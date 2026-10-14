from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, FileResponse

from accounts.mixins import AdminRequiredMixin
from plataformas.models import Plataforma
from .models import Chamado, MudancaStatus, Comentario, Anexo
from .forms import ChamadoForm, MudarStatusForm, ComentarioForm, AnexoForm
from .services import mudar_status
from notificacoes.services import notificar_comentario, notificar_atribuicao


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

        # Comentários e Anexos
        context['comentarios'] = chamado.comentarios.select_related('autor').order_by('criado_em')
        context['anexos'] = chamado.anexos.select_related('enviado_por').order_by('-enviado_em')
        context['comentario_form'] = ComentarioForm()
        context['anexo_form'] = AnexoForm()

        # Montagem da Linha do Tempo Unificada
        eventos = []
        eventos.append({
            'tipo': 'criacao',
            'data': chamado.criado_em,
            'autor': chamado.criado_por,
            'titulo': 'Chamado Aberto',
            'descricao': f"Chamado registrado por {chamado.criado_por.get_full_name() or chamado.criado_por.username}"
        })

        for m in chamado.mudancas_status.select_related('alterado_por'):
            eventos.append({
                'tipo': 'mudanca_status',
                'data': m.alterado_em,
                'autor': m.alterado_por,
                'titulo': f"Status alterado: {m.get_de_status_display()} &rarr; {m.get_para_status_display()}",
                'motivo': m.comentario_motivo,
                'descricao': f"Alterado por {m.alterado_por.get_full_name() or m.alterado_por.username}"
            })

        for c in context['comentarios']:
            eventos.append({
                'tipo': 'comentario',
                'data': c.criado_em,
                'autor': c.autor,
                'titulo': f"Comentário de {c.autor.get_full_name() or c.autor.username}",
                'descricao': c.texto
            })

        for a in context['anexos']:
            eventos.append({
                'tipo': 'anexo',
                'data': a.enviado_em,
                'autor': a.enviado_por,
                'titulo': f"Anexo adicionado: {a.nome_original}",
                'descricao': f"Enviado por {a.enviado_por.get_full_name() or a.enviado_por.username}"
            })

        eventos.sort(key=lambda x: x['data'], reverse=True)
        context['linha_do_tempo'] = eventos

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
        if self.object.responsavel:
            notificar_atribuicao(self.object, self.request.user)
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
        responsavel_antigo = self.get_object().responsavel
        response = super().form_valid(form)
        if self.object.responsavel and self.object.responsavel != responsavel_antigo:
            notificar_atribuicao(self.object, self.request.user)
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

        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

        return redirect('chamados:chamado_detail', pk=chamado.pk)


class ComentarioCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        chamado = get_object_or_404(Chamado, pk=pk)

        # Checa permissão de visualização
        if not getattr(request.user, 'is_admin', False):
            if chamado.responsavel != request.user and chamado.criado_por != request.user:
                raise PermissionDenied("Você não tem permissão para comentar neste chamado.")

        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.chamado = chamado
            comentario.autor = request.user
            comentario.save()

            notificar_comentario(chamado, comentario, request.user)
            messages.success(request, "Comentário adicionado com sucesso.")

            if request.headers.get('HX-Request'):
                comentarios = chamado.comentarios.select_related('autor').order_by('criado_em')
                return render(request, 'chamados/partials/comentarios_list.html', {
                    'comentarios': comentarios,
                    'chamado': chamado,
                    'comentario_form': ComentarioForm(),
                })
        else:
            messages.error(request, "Erro ao enviar comentário. O campo não pode ser vazio.")

        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

        return redirect('chamados:chamado_detail', pk=chamado.pk)


class AnexoUploadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        chamado = get_object_or_404(Chamado, pk=pk)

        # Checa permissão de visualização
        if not getattr(request.user, 'is_admin', False):
            if chamado.responsavel != request.user and chamado.criado_por != request.user:
                raise PermissionDenied("Você não tem permissão para anexar arquivos neste chamado.")

        arquivo = request.FILES.get('arquivo')
        if not arquivo:
            messages.error(request, "Nenhum arquivo foi selecionado.")
            return redirect('chamados:chamado_detail', pk=chamado.pk)

        # Validação do limite de 10 MB
        tamanho = getattr(arquivo, '_size', None) or getattr(arquivo, 'size', 0)
        if tamanho > Anexo.LIMITE_TAMANHO_BYTES:
            messages.error(request, "O arquivo excede o limite máximo permitido de 10 MB.")
            return redirect('chamados:chamado_detail', pk=chamado.pk)

        form = AnexoForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.chamado = chamado
            anexo.enviado_por = request.user
            anexo.nome_original = arquivo.name
            anexo.save()
            messages.success(request, f"Arquivo '{anexo.nome_original}' anexado com sucesso.")
        else:
            for error in form.errors.values():
                messages.error(request, error)

        return redirect('chamados:chamado_detail', pk=chamado.pk)


class AnexoDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk, anexo_pk):
        chamado = get_object_or_404(Chamado, pk=pk)

        # Permissão de download só para quem vê o chamado
        if not getattr(request.user, 'is_admin', False):
            if chamado.responsavel != request.user and chamado.criado_por != request.user:
                raise PermissionDenied("Você não tem permissão para baixar anexos deste chamado.")

        anexo = get_object_or_404(Anexo, pk=anexo_pk, chamado=chamado)
        return FileResponse(anexo.arquivo.open('rb'), as_attachment=True, filename=anexo.nome_original)

