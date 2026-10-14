from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from functools import wraps


class AdminRequiredMixin(AccessMixin):
    """
    Exige que o usuário esteja autenticado e seja Administrador.
    Caso o usuário esteja autenticado mas não seja admin, retorna HTTP 403.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not getattr(request.user, 'is_admin', False):
            raise PermissionDenied("Acesso restrito a Administradores.")
        return super().dispatch(request, *args, **kwargs)


def admin_required(view_func):
    """
    Decorator para views baseadas em função que exige perfil de administrador.
    Retorna 403 se o usuário não for admin.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not getattr(request.user, 'is_admin', False):
            raise PermissionDenied("Acesso restrito a Administradores.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
