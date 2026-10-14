from django.views.generic import ListView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Count

from accounts.mixins import AdminRequiredMixin
from .models import Plataforma
from .forms import PlataformaForm


class PlataformaListView(AdminRequiredMixin, ListView):
    model = Plataforma
    template_name = 'plataformas/plataforma_list.html'
    context_object_name = 'plataformas'
    paginate_by = 15

    def get_queryset(self):
        qs = Plataforma.objects.annotate(total_chamados=Count('chamados')).order_by('nome')
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()

        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))
        if status == 'ativa':
            qs = qs.filter(ativa=True)
        elif status == 'inativa':
            qs = qs.filter(ativa=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['status'] = self.request.GET.get('status', '')
        return context


class PlataformaCreateView(AdminRequiredMixin, CreateView):
    model = Plataforma
    form_class = PlataformaForm
    template_name = 'plataformas/plataforma_form.html'
    success_url = reverse_lazy('plataformas:plataforma_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Plataforma '{self.object.nome}' cadastrada com sucesso.")
        return response


class PlataformaUpdateView(AdminRequiredMixin, UpdateView):
    model = Plataforma
    form_class = PlataformaForm
    template_name = 'plataformas/plataforma_form.html'
    success_url = reverse_lazy('plataformas:plataforma_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Plataforma '{self.object.nome}' atualizada com sucesso.")
        return response


class PlataformaToggleAtivaView(AdminRequiredMixin, View):
    def post(self, request, pk):
        plataforma = get_object_or_404(Plataforma, pk=pk)
        plataforma.ativa = not plataforma.ativa
        plataforma.save(update_fields=['ativa'])
        status_str = "ativada" if plataforma.ativa else "desativada"
        messages.success(request, f"Plataforma '{plataforma.nome}' foi {status_str} com sucesso.")
        return redirect('plataformas:plataforma_list')
