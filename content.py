import mongoengine
from corpus import Content, File


REGISTRY = [
    {
        "name": "DocumentAnalysis",
        "plural_name": "Document Analyses",
        "fields": [
            {
                "name": "name",
                "label": "Name",
                "unique": True,
                "multiple": False,
                "in_lists": True,
                "type": "text",
                "language": "english",
                "autocomplete": False,
                "synonym_file": None,
                "inherited": True
            },
            {
                "name": "source_text",
                "label": "Source Text",
                "multiple": False,
                "in_lists": True,
                "type": "file",
                "inherited": True
            },
            {
                "name": "procedures_completed",
                "label": "Procedures Completed",
                "type": "embedded",
                "multiple": True,
                "inherited": True,
                "in_lists": False
            }
        ],
        "show_in_nav": True,
        "autocomplete_labels": False,
        "proxy_field": "",
        "templates": {
            "Label": {
                "template": "{{ DocumentAnalysis.name }}",
                "mime_type": "text/html"
            }
        },
        "view_widget_url": "/corpus/{corpus_id}/{content_type}/{content_id}/NLPProcedureManager/",
        "edit_widget_url": "/corpus/{corpus_id}/{content_type}/{content_id}/NLPProcedureManager/",
        "inherited_from_module": "plugins.nlp.content",
        "inherited_from_class": "DocumentAnalysis",
        "base_mongo_indexes": None,
        "has_file_field": True,
        "invalid_field_names": [
            "corpus_id",
            "content_type",
            "last_updated",
            "provenance",
            "field_intensities",
            "path",
            "label",
            "uri"
        ]
    }
]

class DocumentAnalysis(Content):
    name = mongoengine.StringField()
    source_text = mongoengine.EmbeddedDocumentField(File)
    procedures_completed = mongoengine.DictField()

    meta = {
        'abstract': True
    }
