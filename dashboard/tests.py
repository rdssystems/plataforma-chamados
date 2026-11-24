import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from pytest_django.asserts import assertNumQueries

from plataformas.models import Plataforma
from chamados.models import Chamado, MudancaStatus

Usuario = get_user_model()


@pytest.fixture
def setup_dashboard():
    hoje = timezone.localdate()
    p1 = Plataforma.objects.create(nome='ERP Cloud', cor='#3B82F6')
    p2 = Plataforma.objects.create(nome='App Mobile', cor='#10B981')

    admin = Usuario.objects.create_superuser(username='admin_dash', password='password123')
    dev1 = Usuario.objects.create_user(username='dev_clara', password='password123', deve_trocar_senha=False)
    dev2 = Usuario.objects.create_user(username='dev_danilo', password='password123', deve_trocar_senha=False)

    # 1. Aberto com dev1
    c_aberto = Chamado.objects.create(
        titulo='Demanda Aberta',
        descricao='D',
        plataforma=p1,
        criado_por=admin,
        responsavel=dev1,
        status=Chamado.STATUS_ABERTO,
        prazo=hoje + timedelta(days=2)
    )

    # 2. Em andamento com dev1
    c_andamento = Chamado.objects.create(
        titulo='Demanda Andamento',
        descricao='D',
        plataforma=p1,
        criado_por=admin,
        responsavel=dev1,
        status=Chamado.STATUS_EM_ANDAMENTO,
        prazo=hoje + timedelta(days=5)
    )

    # 3. Atrasado com dev2 (prazo ontem)
    c_atrasado = Chamado.objects.create(
        titulo='Demanda Atrasada',
        descricao='D',
        plataforma=p2,
        criado_por=admin,
        responsavel=dev2,
        status=Chamado.STATUS_EM_ANDAMENTO,
        prazo=hoje - timedelta(days=2)
    )

    # 4. Concluído no mês corrente com dev1
    c_concluido = Chamado.objects.create(
        titulo='Demanda Concluida',
        descricao='D',
        plataforma=p1,
        criado_por=admin,
        responsavel=dev1,
        status=Chamado.STATUS_CONCLUIDO,
        concluido_em=timezone.now()
    )

    # 5. Sem responsável (Aberto)
    c_sem_resp = Chamado.objects.create(
        titulo='Demanda Sem Dev',
        descricao='D',
        plataforma=p2,
        criado_por=admin,
        responsavel=None,
        status=Chamado.STATUS_ABERTO
    )

    return {
        'admin': admin,
        'dev1': dev1,
        'dev2': dev2,
        'p1': p1,
        'p2': p2,
    }


@pytest.mark.django_db
class TestDashboard:
    def test_cards_indicadores_admin(self, client, setup_dashboard):
        client.login(username='admin_dash', password='password123')
        res = client.get(reverse('dashboard:index'))
        assert res.status_code == 200

        cards = res.context['cards']
        assert cards['total_abertos'] == 2  # c_aberto + c_sem_resp
        assert cards['total_em_andamento'] == 2  # c_andamento + c_atrasado
        assert cards['total_atrasados'] == 1  # c_atrasado
        assert cards['total_concluidos_mes'] == 1  # c_concluido
        assert cards['total_sem_responsavel'] == 1  # c_sem_resp

    def test_dev_ve_apenas_proprios_numeros(self, client, setup_dashboard):
        # Dev 1 tem: 1 aberto, 1 em andamento, 0 atrasados, 1 concluído
        client.login(username='dev_clara', password='password123')
        res = client.get(reverse('dashboard:index'))
        assert res.status_code == 200

        cards = res.context['cards']
        assert cards['total_abertos'] == 1
        assert cards['total_em_andamento'] == 1
        assert cards['total_atrasados'] == 0
        assert cards['total_concluidos_mes'] == 1

        # Dev não deve ver card de 'sem responsável' no HTML
        assert 'Sem Responsável' not in res.content.decode()

    def test_view_json_dados_graficos(self, client, setup_dashboard):
        client.login(username='admin_dash', password='password123')
        res = client.get(reverse('dashboard:dados_graficos'))
        assert res.status_code == 200

        data = res.json()
        assert 'linha' in data
        assert 'plataformas' in data
        assert 'devs' in data
        assert 'prioridades' in data
        assert len(data['plataformas']['labels']) >= 2

    def test_limite_de_queries_dashboard(self, client, setup_dashboard, django_assert_max_num_queries):
        client.login(username='admin_dash', password='password123')
        # SPEC.md: "página carrega com até 15 queries"
        with django_assert_max_num_queries(15):
            res = client.get(reverse('dashboard:index'))
            assert res.status_code == 200



@pytest.mark.django_db
class TestGraficosECharts:
    def _linha(self, client):
        client.login(username='admin_dash', password='password123')
        return client.get(reverse('dashboard:dados_graficos')).json()['linha']

    def test_serie_semanal_tem_12_semanas_consecutivas_em_ordem_cronologica(self, client, setup_dashboard):
        from datetime import date
        linha = self._linha(client)
        assert len(linha['labels']) == len(linha['datas']) == len(linha['abertos']) == len(linha['concluidos']) == 12
        datas = [date.fromisoformat(d) for d in linha['datas']]
        # Ordem de calendário, não alfabética de "dd/mm" (que quebrava na virada do mês).
        assert all(d.weekday() == 0 for d in datas)
        assert all((b - a).days == 7 for a, b in zip(datas, datas[1:]))
        hoje = timezone.localdate()
        assert datas[-1] == hoje - timedelta(days=hoje.weekday())
        assert linha['labels'] == [d.strftime('%d/%m') for d in datas]

    def test_chamado_antigo_cai_na_semana_certa_e_semanas_vazias_valem_zero(self, client, setup_dashboard):
        admin = Usuario.objects.get(username='admin_dash')
        antigo = Chamado.objects.create(
            titulo='Antigo', descricao='D', plataforma=Plataforma.objects.first(),
            criado_por=admin, status=Chamado.STATUS_ABERTO,
        )
        quando = timezone.now() - timedelta(weeks=5)
        Chamado.objects.filter(pk=antigo.pk).update(criado_em=quando)

        linha = self._linha(client)
        dia = timezone.localtime(quando).date()
        indice = linha['datas'].index((dia - timedelta(days=dia.weekday())).isoformat())
        assert linha['abertos'][indice] == 1
        assert sum(linha['abertos']) == Chamado.objects.count()
        assert linha['abertos'].count(0) >= 9  # semanas sem chamados aparecem como zero

    def test_pagina_carrega_echarts_com_versao_fixa_e_integridade(self, client, setup_dashboard):
        client.login(username='admin_dash', password='password123')
        html = client.get(reverse('dashboard:index')).content.decode()
        assert 'echarts@6.1.0/dist/echarts.min.js' in html
        assert 'integrity="sha384-' in html
        assert 'chart.js' not in html.lower()
        assert 'js/dashboard_graficos.js' in html
        for tipo in ('linha', 'plataformas', 'devs', 'prioridades'):
            assert f'data-grafico="{tipo}"' in html

    def test_dev_nao_ve_grafico_por_desenvolvedor(self, client, setup_dashboard):
        client.login(username='dev_clara', password='password123')
        html = client.get(reverse('dashboard:index')).content.decode()
        assert 'data-grafico="linha"' in html
        assert 'data-grafico="devs"' not in html
