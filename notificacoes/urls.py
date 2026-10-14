from django.urls import path
from .views import (
    NotificacaoListView,
    NotificacaoMarcarLidaView,
    NotificacaoMarcarTodasLidasView,
)

app_name = 'notificacoes'

urlpatterns = [
    path('notificacoes/', NotificacaoListView.as_view(), name='notificacao_list'),
    path('notificacoes/<int:pk>/marcar-lida/', NotificacaoMarcarLidaView.as_view(), name='marcar_lida'),
    path('notificacoes/marcar-todas/', NotificacaoMarcarTodasLidasView.as_view(), name='marcar_todas'),
]
