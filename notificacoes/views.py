from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.contrib import messages

from .models import Notificacao


class NotificacaoListView(LoginRequiredMixin, ListView):
    model = Notificacao
    template_name = 'notificacoes/notificacao_list.html'
    context_object_name = 'notificacoes'
    paginate_by = 20

    def get_queryset(self):
        qs = Notificacao.objects.filter(destinatario=self.request.user).select_related('chamado')
        filtro = self.request.GET.get('filtro', '')
        if filtro == 'nao_lidas':
            qs = qs.filter(lida=False)
        elif filtro == 'lidas':
            qs = qs.filter(lida=True)
        return qs.order_by('-criada_em')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro'] = self.request.GET.get('filtro', '')
        context['total_nao_lidas'] = Notificacao.objects.filter(destinatario=self.request.user, lida=False).count()
        return context


class NotificacaoMarcarLidaView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notificacao = get_object_or_404(Notificacao, pk=pk, destinatario=request.user)
        notificacao.lida = True
        notificacao.save(update_fields=['lida'])

        if request.headers.get('HX-Request'):
            return render(request, 'notificacoes/partials/notificacao_item.html', {'notif': notificacao})

        messages.success(request, "Notificação marcada como lida.")
        return redirect('notificacoes:notificacao_list')


class NotificacaoMarcarTodasLidasView(LoginRequiredMixin, View):
    def post(self, request):
        Notificacao.objects.filter(destinatario=request.user, lida=False).update(lida=True)
        messages.success(request, "Todas as notificações foram marcadas como lidas.")
        return redirect('notificacoes:notificacao_list')
