from django.urls import path
from .views import RelatorioView

app_name = 'relatorios'

urlpatterns = [
    path('relatorios/', RelatorioView.as_view(), name='relatorio'),
]
