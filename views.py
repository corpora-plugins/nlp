from manager.utilities import _get_context, get_scholar_corpus, _contains, _clean
from django.shortcuts import render


def nlp_procedure_manager(request, corpus_id, content_type, content_id):
    context = _get_context(request)
    corpus, role = get_scholar_corpus(corpus_id, context['scholar'])

    return render(
        request,
        'procedure_widget.html',
        {
            'corpus_id': corpus_id,
            'content_type': content_type,
            'content_id': content_id,
            'role': role,
            'popup': True,
            'response': context,
        }
    )
