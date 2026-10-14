from django.urls import path
from .views import (
    PlataformaListView,
    PlataformaCreateView,
    PlataformaUpdateView,
    PlataformaToggleAtivaView,
)

app_name = 'plataformas'

urlpatterns = [
    path('plataformas/', PlataformaListView.as_view(), name='plataforma_list'),
    path('plataformas/novo/', PlataformaCreateView.as_view(), name='plataforma_create'),
    path('plataformas/<int:pk>/editar/', PlataformaUpdateView.as_view(), name='plataforma_update'),
    path('plataformas/<int:pk>/toggle/', PlataformaToggleAtivaView.as_view(), name='plataforma_toggle'),
]
