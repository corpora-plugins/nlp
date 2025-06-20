from django.urls import path
from . import views as nlp_views


urlpatterns = [
    path('corpus/<str:corpus_id>/<str:content_type>/<str:content_id>/NLPProcedureManager/', nlp_views.nlp_procedure_manager),
]