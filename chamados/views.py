from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse

from accounts.mixins import AdminRequiredMixin
from plataformas.models import Plataforma
from .models import Chamado, MudancaStatus
from .forms import ChamadoForm, MudarStatusForm
from .services import mudar_status


class ChamadoListView(LoginRequiredMixin, ListView):
    model = Chamado
    template_name = 'chamados/chamado_list.html'
    context_object_name = 'chamados'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'is_admin', False):
            qs = Chamado.objects.all()
        else:
            qs = Chamado.objects.filter(Q(responsavel=user) | Q(criado_por=user))

        qs = qs.select_related('plataforma', 'responsavel', 'criado_por')

        # Filtros
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        prioridade = self.request.GET.get('prioridade', '').strip()
        tipo = self.request.GET.get('tipo', '').strip()
        plataforma_id = self.request.GET.get('plataforma', '').strip()
        responsavel_id = self.request.GET.get('responsavel', '').strip()
        data_inicio = self.request.GET.get('data_inicio', '').strip()
        data_fim = self.request.GET.get('data_fim', '').strip()

        if q:
            qs = qs.filter(Q(codigo__icontains=q) | Q(titulo__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if prioridade:
            qs = qs.filter(prioridade=prioridade)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if plataforma_id:
            qs = qs.filter(plataforma_id=plataforma_id)
        if responsavel_id:
            qs = qs.filter(responsavel_id=responsavel_id)
        if data_inicio:
            qs = qs.filter(criado_em__date__gte=data_inicio)
        if data_fim:
            qs = qs.filter(criado_em__date__lte=data_fim)

        return qs.order_by('-criado_em')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth import get_user_model
        Usuario = get_user_model()

        context['plataformas'] = Plataforma.objects.filter(ativa=True)
        context['responsaveis'] = Usuario.objects.filter(is_active=True).order_by('first_name', 'username')
        context['status_choices'] = Chamado.STATUS_CHOICES
        context['prioridade_choices'] = Chamado.PRIORIDADE_CHOICES
        context['tipo_choices'] = Chamado.TIPO_CHOICES

        # Preservar filtros atuais
        context['filtros'] = {
            'q': self.request.GET.get('q', ''),
            'status': self.request.GET.get('status', ''),
            'prioridade': self.request.GET.get('prioridade', ''),
            'tipo': self.request.GET.get('tipo', ''),
            'plataforma': self.request.GET.get('plataforma', ''),
            'responsavel': self.request.GET.get('responsavel', ''),
            'data_inicio': self.request.GET.get('data_inicio', ''),
            'data_fim': self.request.GET.get('data_fim', ''),
        }
        return context


class ChamadoDetailView(LoginRequiredMixin, DetailView):
    model = Chamado
    template_name = 'chamados/chamado_detail.html'
    context_object_name = 'chamado'

    def get_object(self, queryset=None):
        chamado = super().get_object(queryset)
        user = self.request.user
        if not getattr(user, 'is_admin', False):
            if chamado.responsavel != user and chamado.criado_por != user:
                raise PermissionDenied("Você não tem permissão para visualizar este chamado.")
        return chamado

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chamado = self.object
        user = self.request.user
        is_admin = getattr(user, 'is_admin', False)
        is_resp = chamado.responsavel == user

        # Identificar transições possíveis para o usuário logado
        acoes_possiveis = []
        if chamado.status == Chamado.STATUS_ABERTO:
            if (is_admin or is_resp) and chamado.responsavel:
                acoes_possiveis.append({'status': Chamado.STATUS_EM_ANDAMENTO, 'label': 'Iniciar Atendimento', 'cor': 'blue', 'requer_comentario': False})
            if is_admin:
                acoes_possiveis.append({'status': Chamado.STATUS_CANCELADO, 'label': 'Cancelar Chamado', 'cor': 'red', 'requer_comentario': True})

        elif chamado.status == Chamado.STATUS_EM_ANDAMENTO:
            if is_admin or is_resp:
                acoes_possiveis.append({'status': Chamado.STATUS_EM_REVISAO, 'label': 'Enviar para Revisão', 'cor': 'amber', 'requer_comentario': False})
            if is_admin:
                acoes_possiveis.append({'status': Chamado.STATUS_CANCELADO, 'label': 'Cancelar Chamado', 'cor': 'red', 'requer_comentario': True})

        elif chamado.status == Chamado.STATUS_EM_REVISAO:
            if is_admin:
                acoes_possiveis.append({'status': Chamado.STATUS_CONCLUIDO, 'label': 'Aprovar e Concluir', 'cor': 'emerald', 'requer_comentario': False})
                acoes_possiveis.append({'status': Chamado.STATUS_EM_ANDAMENTO, 'label': 'Devolver para Andamento', 'cor': 'amber', 'requer_comentario': True})
                acoes_possiveis.append({'status': Chamado.STATUS_CANCELADO, 'label': 'Cancelar Chamado', 'cor': 'red', 'requer_comentario': True})

        elif chamado.status == Chamado.STATUS_CONCLUIDO:
            if is_admin:
                acoes_possiveis.append({'status': Chamado.STATUS_EM_ANDAMENTO, 'label': 'Reabrir Chamado', 'cor': 'purple', 'requer_comentario': True})

        context['acoes_possiveis'] = acoes_possiveis
        context['mudancas_status'] = chamado.mudancas_status.select_related('alterado_por').order_by('-alterado_em')
        context['historico'] = chamado.history.all().order_by('-history_date')
        return context


class ChamadoCreateView(LoginRequiredMixin, CreateView):
    model = Chamado
    form_class = ChamadoForm
    template_name = 'chamados/chamado_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Chamado {self.object.codigo} aberto com sucesso!")
        return response

    def get_success_url(self):
        return reverse('chamados:chamado_detail', kwargs={'pk': self.object.pk})


class ChamadoUpdateView(AdminRequiredMixin, UpdateView):
    model = Chamado
    form_class = ChamadoForm
    template_name = 'chamados/chamado_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        chamado = self.get_object()
        if chamado.status in Chamado.STATUS_FINAIS:
            messages.error(request, "Chamados concluídos ou cancelados não aceitam edição de campos.")
            return redirect('chamados:chamado_detail', pk=chamado.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Chamado {self.object.codigo} atualizado com sucesso!")
        return response

    def get_success_url(self):
        return reverse('chamados:chamado_detail', kwargs={'pk': self.object.pk})


class ChamadoMudarStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        chamado = get_object_or_404(Chamado, pk=pk)
        novo_status = request.POST.get('novo_status')
        comentario = request.POST.get('comentario', '')

        try:
            mudar_status(chamado, novo_status, request.user, comentario=comentario)
            messages.success(request, f"Status do chamado alterado para '{chamado.get_status_display()}'.")
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, 'message') else str(e))

        # Se a requisição veio de HTMX
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

        return redirect('chamados:chamado_detail', pk=chamado.pk)
