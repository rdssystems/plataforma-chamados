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

