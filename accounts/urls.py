from django.urls import path
from .views import (
    CustomLoginView,
    CustomLogoutView,
    CustomPasswordChangeView,
    UsuarioListView,
    UsuarioCreateView,
    UsuarioUpdateView,
    UsuarioToggleAtivoView,
    UsuarioRedefinirSenhaView,
    AvatarView,
)

app_name = 'accounts'

urlpatterns = [
    # Autenticação
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('conta/senha/', CustomPasswordChangeView.as_view(), name='trocar_senha'),

    # Gestão de Usuários (Admin)
    path('usuarios/', UsuarioListView.as_view(), name='usuario_list'),
    path('usuarios/novo/', UsuarioCreateView.as_view(), name='usuario_create'),
    path('usuarios/<int:pk>/editar/', UsuarioUpdateView.as_view(), name='usuario_update'),
    path('usuarios/<int:pk>/desativar/', UsuarioToggleAtivoView.as_view(), name='usuario_toggle'),
    path('usuarios/<int:pk>/redefinir-senha/', UsuarioRedefinirSenhaView.as_view(), name='usuario_redefinir_senha'),
    path('usuarios/<int:pk>/foto/', AvatarView.as_view(), name='avatar'),
]
