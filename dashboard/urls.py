from django.urls import path
from .views import DashboardIndexView, DashboardGraficosJsonView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardIndexView.as_view(), name='index'),
    path('dashboard/dados-graficos/', DashboardGraficosJsonView.as_view(), name='dados_graficos'),
]
