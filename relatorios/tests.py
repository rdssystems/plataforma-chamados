import pytest
from datetime import date, datetime, timedelta
import io
import openpyxl
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from plataformas.models import Plataforma
from chamados.models import Chamado
from relatorios.services import calcular_metricas_relatorio, gerar_relatorio_excel, gerar_relatorio_pdf

Usuario = get_user_model()


@pytest.fixture
def setup_dados_conhecidos():
    admin = Usuario.objects.create_superuser(username='admin_relat', password='password123')
    dev_a = Usuario.objects.create_user(username='dev_arthur', password='password123', deve_trocar_senha=False)
    dev_b = Usuario.objects.create_user(username='dev_bia', password='password123', deve_trocar_senha=False)
    plat = Plataforma.objects.create(nome='SaaS Principal', cor='#3B82F6')

    # Período de análise: 01/10/2026 a 31/10/2026
    dt_inicio = date(2026, 10, 1)
    dt_fim = date(2026, 10, 31)

    tz = timezone.get_current_timezone()

    # Chamado 1: Criado 05/10/2026, concluído 07/10/2026 (2 dias), prazo 10/10/2026 (no prazo: SIM)
    c1 = Chamado.objects.create(
        titulo='C1',
        descricao='D',
        plataforma=plat,
        criado_por=admin,
        responsavel=dev_a,
        status=Chamado.STATUS_CONCLUIDO,
        prazo=date(2026, 10, 10)
    )
    Chamado.objects.filter(pk=c1.pk).update(
        criado_em=datetime(2026, 10, 5, 10, 0, tzinfo=tz),
        concluido_em=datetime(2026, 10, 7, 10, 0, tzinfo=tz)
    )

    # Chamado 2: Criado 10/10/2026, concluído 16/10/2026 (6 dias), prazo 12/10/2026 (no prazo: NÃO)
    c2 = Chamado.objects.create(
        titulo='C2',
        descricao='D',
        plataforma=plat,
        criado_por=admin,
        responsavel=dev_b,
        status=Chamado.STATUS_CONCLUIDO,
        prazo=date(2026, 10, 12)
    )
    Chamado.objects.filter(pk=c2.pk).update(
        criado_em=datetime(2026, 10, 10, 10, 0, tzinfo=tz),
        concluido_em=datetime(2026, 10, 16, 10, 0, tzinfo=tz)
    )

    # Chamado 3: Criado 12/10/2026, aberto, prazo 20/10/2026 (atrasado no fim do período: SIM, backlog: SIM)
    c3 = Chamado.objects.create(
        titulo='C3',
        descricao='D',
        plataforma=plat,
        criado_por=admin,
        responsavel=dev_a,
        status=Chamado.STATUS_EM_ANDAMENTO,
        prazo=date(2026, 10, 20)
    )
    Chamado.objects.filter(pk=c3.pk).update(
        criado_em=datetime(2026, 10, 12, 10, 0, tzinfo=tz)
    )

    # Chamado 4: Criado 25/10/2026, aberto, prazo 05/11/2026 (atrasado no fim do período: NÃO, backlog: SIM)
    c4 = Chamado.objects.create(
        titulo='C4',
        descricao='D',
        plataforma=plat,
        criado_por=admin,
        responsavel=dev_b,
        status=Chamado.STATUS_ABERTO,
        prazo=date(2026, 11, 5)
    )
    Chamado.objects.filter(pk=c4.pk).update(
        criado_em=datetime(2026, 10, 25, 10, 0, tzinfo=tz)
    )

    # Chamado 5: Criado 15/09/2026 (fora do período), concluído 02/10/2026 (concluído dentro do período, sem prazo)
    c5 = Chamado.objects.create(
        titulo='C5',
        descricao='D',
        plataforma=plat,
        criado_por=admin,
        responsavel=dev_a,
        status=Chamado.STATUS_CONCLUIDO,
        prazo=None
    )
    Chamado.objects.filter(pk=c5.pk).update(
        criado_em=datetime(2026, 9, 15, 10, 0, tzinfo=tz),
        concluido_em=datetime(2026, 10, 2, 10, 0, tzinfo=tz)
    )

    return {
        'admin': admin,
        'dev_a': dev_a,
        'dev_b': dev_b,
        'dt_inicio': dt_inicio,
        'dt_fim': dt_fim,
    }


@pytest.mark.django_db
class TestRelatoriosServico:
    def test_calculo_metricas_com_dados_conhecidos(self, setup_dados_conhecidos):
        d = setup_dados_conhecidos
        metricas = calcular_metricas_relatorio(data_inicio=d['dt_inicio'], data_fim=d['dt_fim'])

        # 1. Chamados abertos no período (C1, C2, C3, C4) = 4
        assert metricas['total_abertos'] == 4

        # 2. Chamados concluídos no período (C1, C2, C5) = 3
        assert metricas['total_concluidos'] == 3

        # 3. Entregues no prazo:
        # C1 (no prazo: SIM), C2 (no prazo: NÃO), C5 (sem prazo) -> 1 de 2 = 50.0%
        assert metricas['taxa_no_prazo'] == 50.0

        # 4. Atrasados no fim do período: C3 (prazo 20/10 < 31/10 e não concluído) = 1
        assert metricas['atrasados_fim_periodo'] == 1

        # 5. Backlog no fim do período: C3 e C4 = 2
        assert metricas['backlog'] == 2

        # 6. Lista detalhada possui exatamente os 3 concluídos
        assert metricas['lista_detalhada'].count() == 3


@pytest.mark.django_db
class TestRelatoriosExportacaoEViews:
    def test_dev_recebe_403_ao_acessar_relatorios(self, client, setup_dados_conhecidos):
        client.login(username='dev_arthur', password='password123')
        res = client.get(reverse('relatorios:relatorio'))
        assert res.status_code == 403

    def test_admin_acessa_tela_relatorio(self, client, setup_dados_conhecidos):
        client.login(username='admin_relat', password='password123')
        res = client.get(reverse('relatorios:relatorio'))
        assert res.status_code == 200
        assert 'Relatório de Entregas e Desempenho' in res.content.decode()

    def test_exportacao_excel(self, client, setup_dados_conhecidos):
        client.login(username='admin_relat', password='password123')
        res = client.get(f"{reverse('relatorios:relatorio')}?exportar=excel&periodo=este_mes")
        assert res.status_code == 200
        assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in res['Content-Type']
        assert 'relatorio_chamados_' in res['Content-Disposition']

        # Carrega o workbook retornado e valida abas
        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        assert "Resumo" in wb.sheetnames
        assert "Por Desenvolvedor" in wb.sheetnames
        assert "Por Plataforma" in wb.sheetnames
        assert "Chamados Concluídos" in wb.sheetnames

    def test_exportacao_pdf(self, client, setup_dados_conhecidos):
        client.login(username='admin_relat', password='password123')
        res = client.get(f"{reverse('relatorios:relatorio')}?exportar=pdf&periodo=este_mes")
        assert res.status_code == 200
        assert res['Content-Type'] == 'application/pdf'
        assert 'relatorio_chamados_' in res['Content-Disposition']
        # Valida cabeçalho padrão de arquivo PDF
        assert res.content.startswith(b'%PDF')
