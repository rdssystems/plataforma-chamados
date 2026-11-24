from django.views.generic import TemplateView
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from accounts.mixins import AdminRequiredMixin
from config.filtros import Filtros
from plataformas.models import Plataforma
from chamados.models import Chamado
from .services import (
    obter_intervalo_datas,
    calcular_metricas_relatorio,
    gerar_relatorio_excel,
    gerar_relatorio_pdf,
)

Usuario = get_user_model()


PERIODOS = [
    ('esta_semana', 'Esta semana'),
    ('semana_passada', 'Semana passada'),
    ('este_mes', 'Este mês'),
    ('mes_passado', 'Mês passado'),
]


class RelatorioView(AdminRequiredMixin, TemplateView):
    template_name = 'relatorios/relatorio.html'

    def get(self, request, *args, **kwargs):
        plataformas = list(Plataforma.objects.filter(ativa=True).order_by('nome'))
        devs = list(Usuario.objects.filter(is_active=True).order_by('first_name', 'username'))

        f = Filtros(request.GET)
        periodo_atalho = f.opcao('periodo', PERIODOS, 'Selecione um período da lista.') or 'este_mes'
        data_inicio_livre = f.data('data_inicio')
        data_fim_livre = f.data('data_fim')
        f.periodo(data_inicio_livre, data_fim_livre)
        dev_id = f.id_entre('dev', [d.pk for d in devs], 'Selecione um desenvolvedor da lista.')
        plataforma_id = f.id_entre('plataforma', [p.pk for p in plataformas], 'Selecione uma plataforma da lista.')
        tipo = f.opcao('tipo', Chamado.TIPO_CHOICES, 'Selecione um tipo da lista.')
        prioridade = f.opcao('prioridade', Chamado.PRIORIDADE_CHOICES, 'Selecione uma prioridade da lista.')
        exportar = request.GET.get('exportar')

        contexto_base = {
            'plataformas': plataformas,
            'devs': devs,
            'tipos': Chamado.TIPO_CHOICES,
            'prioridades': Chamado.PRIORIDADE_CHOICES,
            'periodos': PERIODOS,
            'periodo_atalho': periodo_atalho,
            'filtros': f.brutos,
            'filtros_erros': f.erros,
            'filtros_validos': f.validos,
        }
        # Filtro inválido: preserva as entradas e suspende métricas e exportação.
        if not f.validos:
            return self.render_to_response(self.get_context_data(**contexto_base))

        data_inicio, data_fim = obter_intervalo_datas(
            periodo_atalho=periodo_atalho,
            data_inicio=data_inicio_livre if (data_inicio_livre and data_fim_livre) else None,
            data_fim=data_fim_livre if (data_inicio_livre and data_fim_livre) else None,
        )
        dados_relatorio = calcular_metricas_relatorio(
            data_inicio=data_inicio,
            data_fim=data_fim,
            dev_id=dev_id,
            plataforma_id=plataforma_id,
            tipo=tipo,
            prioridade=prioridade
        )

        # O recorte vai no cabeçalho da tela e do PDF: quem lê o arquivo sabe o que foi filtrado.
        nomes = {
            'dev': {d.pk: d.get_full_name() or d.username for d in devs},
            'plataforma': {p.pk: p.nome for p in plataformas},
        }
        recorte = []
        if dev_id:
            recorte.append(f'Desenvolvedor: {nomes["dev"][dev_id]}')
        if plataforma_id:
            recorte.append(f'Plataforma: {nomes["plataforma"][plataforma_id]}')
        if tipo:
            recorte.append(f'Tipo: {dict(Chamado.TIPO_CHOICES)[tipo]}')
        if prioridade:
            recorte.append(f'Prioridade: {dict(Chamado.PRIORIDADE_CHOICES)[prioridade]}')

        if exportar == 'excel':
            excel_file = gerar_relatorio_excel(dados_relatorio)
            nome_arquivo = f"relatorio_chamados_{data_inicio.strftime('%Y-%m-%d')}_{data_fim.strftime('%Y-%m-%d')}.xlsx"
            response = HttpResponse(
                excel_file.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
            return response

        if exportar == 'pdf':
            pdf_bytes = gerar_relatorio_pdf(dados_relatorio, request, recorte=recorte)
            nome_arquivo = f"relatorio_chamados_{data_inicio.strftime('%Y-%m-%d')}_{data_fim.strftime('%Y-%m-%d')}.pdf"
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
            return response

        context = self.get_context_data(
            dados=dados_relatorio,
            data_inicio=data_inicio,
            data_fim=data_fim,
            recorte=recorte,
            **contexto_base,
        )
        return self.render_to_response(context)
