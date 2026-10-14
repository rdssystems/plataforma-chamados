from django.views.generic import TemplateView
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from accounts.mixins import AdminRequiredMixin
from plataformas.models import Plataforma
from chamados.models import Chamado
from .services import (
    obter_intervalo_datas,
    calcular_metricas_relatorio,
    gerar_relatorio_excel,
    gerar_relatorio_pdf,
)

Usuario = get_user_model()


class RelatorioView(AdminRequiredMixin, TemplateView):
    template_name = 'relatorios/relatorio.html'

    def get(self, request, *args, **kwargs):
        periodo_atalho = request.GET.get('periodo', 'este_mes')
        data_inicio_str = request.GET.get('data_inicio')
        data_fim_str = request.GET.get('data_fim')
        dev_id = request.GET.get('dev')
        plataforma_id = request.GET.get('plataforma')
        tipo = request.GET.get('tipo')
        prioridade = request.GET.get('prioridade')
        exportar = request.GET.get('exportar')

        data_inicio, data_fim = obter_intervalo_datas(
            periodo_atalho=periodo_atalho,
            data_inicio=data_inicio_str,
            data_fim=data_fim_str
        )

        dados_relatorio = calcular_metricas_relatorio(
            data_inicio=data_inicio,
            data_fim=data_fim,
            dev_id=dev_id,
            plataforma_id=plataforma_id,
            tipo=tipo,
            prioridade=prioridade
        )

        # Exportação Excel
        if exportar == 'excel':
            excel_file = gerar_relatorio_excel(dados_relatorio)
            nome_arquivo = f"relatorio_chamados_{data_inicio.strftime('%Y-%m-%d')}_{data_fim.strftime('%Y-%m-%d')}.xlsx"
            response = HttpResponse(
                excel_file.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
            return response

        # Exportação PDF
        if exportar == 'pdf':
            pdf_bytes = gerar_relatorio_pdf(dados_relatorio, request)
            nome_arquivo = f"relatorio_chamados_{data_inicio.strftime('%Y-%m-%d')}_{data_fim.strftime('%Y-%m-%d')}.pdf"
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
            return response

        # Renderização HTML
        context = self.get_context_data(
            dados=dados_relatorio,
            periodo_atalho=periodo_atalho,
            data_inicio=data_inicio,
            data_fim=data_fim,
            dev_id=dev_id,
            plataforma_id=plataforma_id,
            tipo=tipo,
            prioridade=prioridade,
        )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plataformas'] = Plataforma.objects.filter(ativa=True).order_by('nome')
        context['devs'] = Usuario.objects.filter(is_active=True).order_by('first_name', 'username')
        context['tipos'] = Chamado.TIPO_CHOICES
        context['prioridades'] = Chamado.PRIORIDADE_CHOICES
        return context
