from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path('chat/', views.chat_index, name='index'),
    path('chat/conversas/', views.lista_conversas, name='conversas'),
    path('chat/usuarios/', views.lista_usuarios, name='usuarios'),
    path('chat/iniciar/<int:usuario_id>/', views.iniciar_conversa, name='iniciar'),
    path('chat/<int:pk>/', views.chat_index, name='conversa'),
    path('chat/<int:pk>/enviar/', views.enviar_mensagem, name='enviar'),
    path('chat/<int:pk>/mensagens/', views.listar_mensagens, name='mensagens'),
    path('chat/<int:pk>/lida/', views.marcar_lida, name='marcar_lida'),
]
