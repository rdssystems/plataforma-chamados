from django.shortcuts import redirect
from django.urls import reverse, resolve


class TrocaSenhaObrigatoriaMiddleware:
    """
    Redireciona usuários autenticados que possuem 'deve_trocar_senha=True'
    para a rota de troca de senha até que a senha seja alterada.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, 'deve_trocar_senha', False):
            path = request.path
            
            # Rotas isentas do redirecionamento
            rotas_isentas = [
                reverse('accounts:trocar_senha'),
                reverse('accounts:logout'),
            ]

            is_isento = any(path.startswith(r) for r in rotas_isentas) or \
                        path.startswith('/static/') or \
                        path.startswith('/media/') or \
                        path.startswith('/favicon.ico')

            if not is_isento:
                return redirect('accounts:trocar_senha')

        return self.get_response(request)
