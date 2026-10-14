from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, FormView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import update_session_auth_hash, get_user_model
from django.db.models import Q

from .forms import (
    CustomLoginForm,
    CustomPasswordChangeForm,
    UsuarioCriarForm,
    UsuarioEditarForm,
    UsuarioRedefinirSenhaForm,
)
from .mixins import AdminRequiredMixin

Usuario = get_user_model()


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        if getattr(self.request.user, 'deve_trocar_senha', False):
            return reverse_lazy('accounts:trocar_senha')
        return reverse_lazy('dashboard:index')


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "Você encerrou sua sessão.")
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/trocar_senha.html'
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy('dashboard:index')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Atualiza a sessão para o usuário não ser desconectado ao mudar a senha
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, "Sua senha foi alterada com sucesso!")
        return response


class UsuarioListView(AdminRequiredMixin, ListView):
    model = Usuario
    template_name = 'accounts/usuario_list.html'
    context_object_name = 'usuarios'
    paginate_by = 15

    def get_queryset(self):
        qs = Usuario.objects.all().order_by('first_name', 'username')
        q = self.request.GET.get('q', '').strip()
        papel = self.request.GET.get('papel', '').strip()
        status = self.request.GET.get('status', '').strip()

        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q)
            )
        if papel in [Usuario.PAPEL_ADMIN, Usuario.PAPEL_DEV]:
            qs = qs.filter(papel=papel)
        if status == 'ativo':
            qs = qs.filter(is_active=True)
        elif status == 'inativo':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['papel'] = self.request.GET.get('papel', '')
        context['status'] = self.request.GET.get('status', '')
        return context


class UsuarioCreateView(AdminRequiredMixin, CreateView):
    model = Usuario
    form_class = UsuarioCriarForm
    template_name = 'accounts/usuario_form.html'
    success_url = reverse_lazy('accounts:usuario_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Usuário '{self.object.username}' criado com sucesso com senha provisória."
        )
        return response


class UsuarioUpdateView(AdminRequiredMixin, UpdateView):
    model = Usuario
    form_class = UsuarioEditarForm
    template_name = 'accounts/usuario_form.html'
    success_url = reverse_lazy('accounts:usuario_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Usuário '{self.object.username}' atualizado com sucesso.")
        return response


class UsuarioToggleAtivoView(AdminRequiredMixin, View):
    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        if usuario == request.user:
            messages.error(request, "Você não pode desativar seu próprio usuário.")
            return redirect('accounts:usuario_list')

        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])
        status_str = "ativado" if usuario.is_active else "desativado"
        messages.success(request, f"Usuário '{usuario.username}' foi {status_str} com sucesso.")
        return redirect('accounts:usuario_list')


class UsuarioRedefinirSenhaView(AdminRequiredMixin, FormView):
    template_name = 'accounts/usuario_redefinir_senha.html'
    form_class = UsuarioRedefinirSenhaForm
    success_url = reverse_lazy('accounts:usuario_list')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.usuario_alvo = get_object_or_404(Usuario, pk=kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuario_alvo'] = self.usuario_alvo
        return context

    def form_valid(self, form):
        nova_senha = form.cleaned_data['nova_senha_provisoria']
        self.usuario_alvo.set_password(nova_senha)
        self.usuario_alvo.deve_trocar_senha = True
        self.usuario_alvo.save()
        messages.success(
            self.request,
            f"Senha do usuário '{self.usuario_alvo.username}' redefinida com sucesso para nova senha provisória."
        )
        return redirect(self.success_url)
