"""Critérios de aceite do padrão de dashboards da Secretaria (front-rules.md, seção 9)."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from chamados.models import Chamado
from plataformas.models import Plataforma

Usuario = get_user_model()


@pytest.fixture
def base():
    hoje = timezone.localdate()
    admin = Usuario.objects.create_superuser(username='chefe', password='senha12345')
    dev = Usuario.objects.create_user(username='dev_ana', password='senha12345', deve_trocar_senha=False)
    outro = Usuario.objects.create_user(username='dev_beto', password='senha12345', deve_trocar_senha=False)
    plat = Plataforma.objects.create(nome='Portal', cor='#2b3a8c')

    def chamado(**extra):
        dados = {'titulo': 'T', 'descricao': 'D', 'plataforma': plat, 'criado_por': admin}
        dados.update(extra)
        return Chamado.objects.create(**dados)

    chamado(responsavel=dev, status=Chamado.STATUS_ABERTO, prazo=hoje - timedelta(days=2))        # aberto + atrasado
    chamado(responsavel=dev, status=Chamado.STATUS_EM_REVISAO, prazo=hoje + timedelta(days=1))    # em andamento (revisão)
    chamado(responsavel=None, status=Chamado.STATUS_ABERTO)                                       # sem responsável
    chamado(responsavel=outro, status=Chamado.STATUS_EM_ANDAMENTO, prazo=hoje - timedelta(days=9))  # atrasado (outro dev)
    c = chamado(responsavel=dev, status=Chamado.STATUS_CONCLUIDO)
    Chamado.objects.filter(pk=c.pk).update(concluido_em=timezone.now())
    return {'admin': admin, 'dev': dev, 'outro': outro, 'plat': plat}


def _entrar(client, usuario):
    client.force_login(usuario)
    return client


@pytest.mark.django_db
class TestIndicadorEDetalhamento:
    """O número do card pode ser reproduzido abrindo a consulta de origem."""

    CARDS = {
        'abertos': 'total_abertos',
        'em_andamento': 'total_em_andamento',
        'atrasados': 'total_atrasados',
        'concluidos_mes': 'total_concluidos_mes',
        'sem_responsavel': 'total_sem_responsavel',
    }

    @pytest.mark.parametrize('recorte', ['equipe', 'dev'])
    def test_cards_batem_com_a_listagem(self, client, base, recorte):
        _entrar(client, base['admin'])
        params = {'dev': base['dev'].pk} if recorte == 'dev' else {}
        cards = client.get(reverse('dashboard:index'), params).context['cards']
        for situacao, chave in self.CARDS.items():
            consulta = {'situacao': situacao}
            if recorte == 'dev':
                consulta['responsavel'] = base['dev'].pk
            total = client.get(reverse('chamados:chamado_list'), consulta).context['total']
            assert total == cards[chave], situacao

    def test_valores_conhecidos(self, client, base):
        _entrar(client, base['admin'])
        cards = client.get(reverse('dashboard:index')).context['cards']
        assert cards == {
            'total_abertos': 2, 'total_em_andamento': 2, 'total_atrasados': 2,
            'total_concluidos_mes': 1, 'total_sem_responsavel': 1,
        }

    def test_card_aponta_para_a_consulta_com_o_recorte(self, client, base):
        _entrar(client, base['admin'])
        html = client.get(reverse('dashboard:index'), {'dev': base['dev'].pk}).content.decode()
        assert f'/chamados/?situacao=atrasados&amp;responsavel={base["dev"].pk}' in html


@pytest.mark.django_db
class TestFiltroInvalido:
    """Entrada inválida: mostra o erro no campo, preserva o valor e suspende os resultados."""

    def test_dashboard_dev_inexistente(self, client, base):
        _entrar(client, base['admin'])
        res = client.get(reverse('dashboard:index'), {'dev': 'abc'})
        assert res.status_code == 200
        assert res.context['filtros_erros']['dev']
        assert 'cards' not in res.context
        assert 'aria-invalid="true"' in res.content.decode()

    def test_endpoint_dos_graficos_responde_400(self, client, base):
        _entrar(client, base['admin'])
        res = client.get(reverse('dashboard:dados_graficos'), {'dev': '999999'})
        assert res.status_code == 400
        assert 'dev' in res.json()['erros']

    def test_listagem_preserva_entradas_e_suspende_resultados(self, client, base):
        _entrar(client, base['admin'])
        res = client.get(reverse('chamados:chamado_list'),
                         {'plataforma': 'xyz', 'data_inicio': '2026-11-20', 'data_fim': '2026-11-01', 'q': 'T'})
        assert res.status_code == 200
        erros = res.context['filtros_erros']
        assert set(erros) == {'plataforma', 'data_fim'}
        assert 'posterior' in erros['data_fim']
        assert list(res.context['chamados']) == []
        html = res.content.decode()
        assert 'value="2026-11-20"' in html and 'value="T"' in html

    def test_relatorio_data_invalida_nao_quebra(self, client, base):
        _entrar(client, base['admin'])
        res = client.get(reverse('relatorios:relatorio'), {'data_inicio': '31/12/2026', 'data_fim': '2026-12-31'})
        assert res.status_code == 200
        assert 'data_inicio' in res.context['filtros_erros']
        assert 'dados' not in res.context

    def test_relatorio_nao_exporta_com_filtro_invalido(self, client, base):
        _entrar(client, base['admin'])
        res = client.get(reverse('relatorios:relatorio'), {'dev': 'abc', 'exportar': 'excel'})
        assert res.status_code == 200
        assert res['Content-Type'].startswith('text/html')


@pytest.mark.django_db
def test_paginacao_preserva_os_filtros(client, base):
    for i in range(20):
        Chamado.objects.create(titulo=f'Lote {i}', descricao='D', plataforma=base['plat'],
                               criado_por=base['admin'], prioridade=Chamado.PRIORIDADE_ALTA)
    _entrar(client, base['admin'])
    res = client.get(reverse('chamados:chamado_list'), {'prioridade': 'alta'})
    assert res.context['total'] == 20
    html = res.content.decode()
    assert '?prioridade=alta&amp;page=2' in html


@pytest.mark.django_db
def test_erro_de_formulario_fica_ligado_ao_campo(client, base):
    _entrar(client, base['admin'])
    res = client.post(reverse('chamados:chamado_create'), {'titulo': '', 'descricao': ''})
    html = res.content.decode()
    assert 'class="form-control is-invalid"' in html
    assert 'aria-describedby="id_titulo-erro"' in html
    assert 'id="id_titulo-erro"' in html


@pytest.mark.django_db
def test_mutacao_sem_csrf_e_recusada(base):
    chamado = Chamado.objects.filter(responsavel=base['dev'], status=Chamado.STATUS_ABERTO).first()
    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(base['dev'])
    res = cliente.post(reverse('chamados:chamado_mudar_status', args=[chamado.pk]), {'novo_status': 'em_andamento'})
    assert res.status_code == 403
    chamado.refresh_from_db()
    assert chamado.status == Chamado.STATUS_ABERTO


@pytest.mark.django_db
class TestNavegacaoPorPerfil:
    def test_admin_ve_configuracoes_e_relatorios(self, client, base):
        html = _entrar(client, base['admin']).get(reverse('dashboard:index')).content.decode()
        assert f'href="{reverse("relatorios:relatorio")}"' in html
        assert f'href="{reverse("accounts:usuario_list")}"' in html
        assert 'Equipe inteira' in html

    def test_dev_nao_ve_areas_administrativas(self, client, base):
        html = _entrar(client, base['dev']).get(reverse('dashboard:index')).content.decode()
        assert f'href="{reverse("relatorios:relatorio")}"' not in html
        assert f'href="{reverse("accounts:usuario_list")}"' not in html
        assert 'Suas demandas' in html

    def test_url_direta_fora_do_escopo_continua_bloqueada(self, client, base):
        _entrar(client, base['dev'])
        assert client.get(reverse('relatorios:relatorio')).status_code == 403
        alheio = Chamado.objects.filter(responsavel=base['outro']).first()
        assert client.get(reverse('chamados:chamado_detail', args=[alheio.pk])).status_code == 403
