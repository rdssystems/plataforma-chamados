from django.urls import path
from .views import (
    ChamadoListView,
    ChamadoDetailView,
    ChamadoCreateView,
    ChamadoUpdateView,
    ChamadoMudarStatusView,
    ComentarioCreateView,
    AnexoUploadView,
    AnexoDownloadView,
)

app_name = 'chamados'

urlpatterns = [
    path('chamados/', ChamadoListView.as_view(), name='chamado_list'),
    path('chamados/novo/', ChamadoCreateView.as_view(), name='chamado_create'),
    path('chamados/<int:pk>/', ChamadoDetailView.as_view(), name='chamado_detail'),
    path('chamados/<int:pk>/editar/', ChamadoUpdateView.as_view(), name='chamado_update'),
    path('chamados/<int:pk>/mudar-status/', ChamadoMudarStatusView.as_view(), name='chamado_mudar_status'),
    path('chamados/<int:pk>/comentarios/', ComentarioCreateView.as_view(), name='comentario_create'),
    path('chamados/<int:pk>/anexos/', AnexoUploadView.as_view(), name='anexo_upload'),
    path('chamados/<int:pk>/anexos/<int:anexo_pk>/download/', AnexoDownloadView.as_view(), name='anexo_download'),
]
