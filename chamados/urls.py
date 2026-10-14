from django.urls import path
from .views import (
    ChamadoListView,
    ChamadoDetailView,
    ChamadoCreateView,
    ChamadoUpdateView,
    ChamadoMudarStatusView,
)

app_name = 'chamados'

urlpatterns = [
    path('chamados/', ChamadoListView.as_view(), name='chamado_list'),
    path('chamados/novo/', ChamadoCreateView.as_view(), name='chamado_create'),
    path('chamados/<int:pk>/', ChamadoDetailView.as_view(), name='chamado_detail'),
    path('chamados/<int:pk>/editar/', ChamadoUpdateView.as_view(), name='chamado_update'),
    path('chamados/<int:pk>/mudar-status/', ChamadoMudarStatusView.as_view(), name='chamado_mudar_status'),
]
