import os
import shutil
import langcodes
import traceback
import spacy
from time import sleep
from spacy.tokens import Doc
from spacy.cli.download import get_compatibility, download
from huey.contrib.djhuey import db_task
from corpus import Job


def get_spacy_languages():
    spacy_languages = {}
    compatibility_dict = get_compatibility()

    model_names = [model_name for model_name in compatibility_dict.keys() if
            compatibility_dict[model_name][0].startswith("3.8") and model_name.endswith("core_web_md") or model_name.endswith("core_news_md")]

    for model_name in model_names:
        language_code = model_name.split("_")[0]
        language = langcodes.Language.get(language_code)
        language_name = language.language_name()
        version = compatibility_dict[model_name][0]
        if language_name:
            spacy_languages[language_name] = {
                'language_code': language_code,
                'model': model_name,
                'version': version
            }

    return spacy_languages


REGISTRY = {
    "Read Text with spaCy": {
        "version": "0.2",
        "jobsite_type": "HUEY",
        "content_type": "DocumentAnalysis",
        "track_provenance": True,
        "create_report": True,
        "configuration": {
            "parameters": {
                "language": {
                    "value": "English",
                    "type": "choice",
                    "choices": sorted(list(get_spacy_languages().keys())),
                    "label": "Language",
                    "note": "This determines which spaCy model to use when parsing the document. It will be parsed using the medium sized core news model for the chosen language."
                }
            },
        },
        "module": 'plugins.nlp.tasks',
        "functions": ['read_text_with_spacy'],
     },
    "Perform NER with spaCy": {
        "version": "0.1",
        "jobsite_type": "HUEY",
        "content_type": "DocumentAnalysis",
        "track_provenance": True,
        "create_report": True,
        "configuration": {
            "parameters": {
            },
        },
        "module": 'plugins.nlp.tasks',
        "functions": ['perform_ner_with_spacy']
    }
}


@db_task(priority=2)
def read_text_with_spacy(job_id):
    job = Job(job_id)
    text_segments = []
    errors = []
    nlp_dir = f"{job.content.path}/spacy"
    nlp_path_prefix = f"{nlp_dir}/{job.content.id}_"
    nlp_files = []
    max_doc_length = 900000

    job.set_status('running')

    language_name = job.get_param_value('language')
    spacy_languages = get_spacy_languages()
    spacy_model = spacy_languages[language_name].get('model')

    if spacy_model:
        job.report("Setting up file structure...")
        if os.path.exists(nlp_dir):
            shutil.rmtree(nlp_dir)
            sleep(2)
        os.makedirs(nlp_dir, exist_ok=True)

        job.report(f"Attempting to load text from {job.content.name}...")

        try:
            text = None
            with open(job.content.source_text.path, 'r', encoding='utf-8') as text_in:
                text = text_in.read()

            while len(text) > max_doc_length:
                segment_end_index = get_segment_end_index(text, max_doc_length)
                text_segments.append(text[:segment_end_index])
                text = text[segment_end_index:]

            text_segments.append(text)
        except:
            text_segments = None
            errors.append(f"Error while loading text from file:\n\n{traceback.format_exc()}")

        if text_segments:
            job.report(f"Reading text using this spaCy model: {spacy_model}")
            nlp = None

            try:
                nlp = spacy.load(spacy_model)
            except:
                nlp = None

            if nlp is None:
                download(spacy_model)
                nlp = spacy.load(spacy_model)

            job.set_status('running', percent_complete=10)

            try:
                for seg_index in range(0, len(text_segments)):
                    doc = nlp(text_segments[seg_index])
                    nlp_filename = f"{nlp_path_prefix}{seg_index}.spacydoc"
                    doc.to_disk(nlp_filename)
                    nlp_files.append(nlp_filename)
                    del doc

                    job.set_status('running', percent_complete=int((seg_index / len(text_segments)) * 100))

                job.report(f"Completed reading {job.content.name} with spaCy and saved results to disk :)")
            except:
                errors.append(f"spaCy encountered an error while parsing or serializing the text:\n\n{traceback.format_exc()}")
        else:
            errors.append("Unable to load text due to missing file or empty content!")
    else:
        errors.append("Invalid spacy model specified!")

    if errors:
        job.complete(status='error', error_msg="\n\n".join(errors))
    else:
        job.content.procedures_completed['read_text_with_spacy'] = {
            "language_info": spacy_languages[language_name],
            "nlp_files": nlp_files,
        }
        job.content.save()
        job.complete(status='complete')


def get_segment_end_index(text, max_doc_length):
    if not text:
        return 0

    endline_indexes = []
    for char_index in range(0, len(text)):
        if char_index % max_doc_length == 0 and endline_indexes:
            return endline_indexes[-1]

        if text[char_index] == '\n':
            endline_indexes.append(char_index)

    return char_index


@db_task(priority=2)
def perform_ner_with_spacy(job_id):
    job = Job(job_id)
    errors = []
    nlp_dir = f"{job.content.path}/spacy"
    tagged_text_file = f"{nlp_dir}/{job.content.id}_tagged_text.xml"

    job.set_status('running')
    job.report(f"Attempting to load parsed NLP data from {job.content.name}...")

    if 'read_text_with_spacy' in job.content.procedures_completed and os.path.exists(nlp_dir):
        with open(tagged_text_file, 'w', encoding='utf-8') as text_out:
            try:
                nlp_info = job.content.procedures_completed['read_text_with_spacy']
                nlp = spacy.load(nlp_info['language_info']['model'])

                text_out.write('''<TEI xmlns="http://www.tei-c.org/ns/1.0">''')

                for nlp_file in nlp_info['nlp_files']:
                    doc = Doc(nlp.vocab).from_disk(nlp_file)
                    entities = [ent for ent in doc.ents]
                    entity_map = {}
                    for entity_index in range(0, len(entities)):
                        ent = entities[entity_index]
                        if ent.start not in entity_map:
                            entity_map[ent.start] = {'start': [], 'end': []}
                        if ent.end not in entity_map:
                            entity_map[ent.end] = {'start': [], 'end': []}

                        entity_map[ent.start]['start'].append(entity_index)
                        entity_map[ent.end]['end'].append(entity_index)

                    tokens = [t for t in doc]
                    last_whitespace = ''
                    for token_index in range(0, len(tokens)):
                        token = tokens[token_index]

                        if token_index in entity_map and entity_map[token_index]['end']:
                            for ent_index in entity_map[token_index]['end']:
                                text_out.write('</name>')

                        if len(last_whitespace) > 0:
                            text_out.write(last_whitespace)

                        if token_index in entity_map and entity_map[token_index]['start']:
                            for ent_index in entity_map[token_index]['start']:
                                text_out.write(f'<name type="{entities[ent_index].label_}">')

                        text_out.write(token.text)
                        last_whitespace = token.whitespace_

                    if len(last_whitespace) > 0:
                        text_out.write(last_whitespace)

                    del doc
                    del entities
                    del tokens

                text_out.write('</TEI>')
            except:
                errors.append(f"Error writing out tagged text:\n\n{traceback.format_exc()}")

    if errors:
        job.complete(status='error', error_msg="\n\n".join(errors))
    else:
        job.content.procedures_completed['perform_ner_with_spacy'] = {
            'tagged_text_file': tagged_text_file,
        }
        job.complete(status='complete')