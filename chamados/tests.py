import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from plataformas.models import Plataforma
from chamados.models import Chamado, MudancaStatus
from chamados.services import mudar_status

Usuario = get_user_model()


@pytest.fixture
def plataforma():
    return Plataforma.objects.create(nome='Portal ERP', cor='#3B82F6')


@pytest.fixture
def admin_user():
    return Usuario.objects.create_superuser(username='admin_boss', password='password123')


@pytest.fixture
def dev_1():
    return Usuario.objects.create_user(username='dev_alice', password='password123', deve_trocar_senha=False)


@pytest.fixture
def dev_2():
    return Usuario.objects.create_user(username='dev_bob', password='password123', deve_trocar_senha=False)


@pytest.mark.django_db
class TestChamadoModel:
    def test_geracao_codigo_sequencial(self, plataforma, admin_user):
        c1 = Chamado.objects.create(
            titulo='Chamado Um',
            descricao='Desc 1',
            plataforma=plataforma,
            criado_por=admin_user
        )
        c2 = Chamado.objects.create(
            titulo='Chamado Dois',
            descricao='Desc 2',
            plataforma=plataforma,
            criado_por=admin_user
        )
        assert c1.codigo == 'CH-0001'
        assert c2.codigo == 'CH-0002'

    def test_propriedade_esta_atrasado(self, plataforma, admin_user):
        ontem = timezone.localdate() - timedelta(days=1)
        amanha = timezone.localdate() + timedelta(days=1)

        c_atrasado = Chamado.objects.create(
            titulo='Bug Antigo',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            prazo=ontem,
            status=Chamado.STATUS_EM_ANDAMENTO
        )
        assert c_atrasado.esta_atrasado is True

        c_no_prazo = Chamado.objects.create(
            titulo='Bug Novo',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            prazo=amanha,
            status=Chamado.STATUS_EM_ANDAMENTO
        )
        assert c_no_prazo.esta_atrasado is False

        # Chamado concluído com prazo vencido NÃO conta como atrasado
        c_atrasado.status = Chamado.STATUS_CONCLUIDO
        assert c_atrasado.esta_atrasado is False


@pytest.mark.django_db
class TestTransicoesStatusServices:
    def test_aberto_para_em_andamento_sem_responsavel_falha(self, plataforma, admin_user):
        chamado = Chamado.objects.create(
            titulo='Tarefa X',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            responsavel=None
        )
        with pytest.raises(ValidationError) as exc:
            mudar_status(chamado, Chamado.STATUS_EM_ANDAMENTO, admin_user)
        assert "responsável atribuído" in str(exc.value)

    def test_aberto_para_em_andamento_por_outro_dev_falha(self, plataforma, admin_user, dev_1, dev_2):
        chamado = Chamado.objects.create(
            titulo='Tarefa Y',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            responsavel=dev_1
        )
        with pytest.raises(ValidationError) as exc:
            mudar_status(chamado, Chamado.STATUS_EM_ANDAMENTO, dev_2)
        assert "Apenas o responsável ou um administrador" in str(exc.value)

    def test_fluxo_completo_valido(self, plataforma, admin_user, dev_1):
        chamado = Chamado.objects.create(
            titulo='Fluxo Feliz',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            responsavel=dev_1
        )
        assert chamado.iniciado_em is None
        assert chamado.concluido_em is None

        # 1. Aberto -> Em andamento (pelo dev responsável)
        mudar_status(chamado, Chamado.STATUS_EM_ANDAMENTO, dev_1)
        chamado.refresh_from_db()
        assert chamado.status == Chamado.STATUS_EM_ANDAMENTO
        assert chamado.iniciado_em is not None

        # 2. Em andamento -> Em revisão (pelo dev responsável)
        mudar_status(chamado, Chamado.STATUS_EM_REVISAO, dev_1)
        chamado.refresh_from_db()
        assert chamado.status == Chamado.STATUS_EM_REVISAO

        # 3. Em revisão -> Concluído (pelo admin)
        mudar_status(chamado, Chamado.STATUS_CONCLUIDO, admin_user)
        chamado.refresh_from_db()
        assert chamado.status == Chamado.STATUS_CONCLUIDO
        assert chamado.concluido_em is not None

        # Verificar se registrou 3 MudancaStatus
        assert MudancaStatus.objects.filter(chamado=chamado).count() == 3

    def test_devolucao_e_reabertura_exigem_comentario_e_limpam_concluido(self, plataforma, admin_user, dev_1):
        chamado = Chamado.objects.create(
            titulo='Reabertura Test',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            responsavel=dev_1,
            status=Chamado.STATUS_EM_REVISAO
        )

        # Devolver sem comentário -> falha
        with pytest.raises(ValidationError):
            mudar_status(chamado, Chamado.STATUS_EM_ANDAMENTO, admin_user, comentario="")

        # Devolver com comentário -> sucesso
        mudar_status(chamado, Chamado.STATUS_EM_ANDAMENTO, admin_user, comentario="Ajustar testes unitários")
        chamado.refresh_from_db()
        assert chamado.status == Chamado.STATUS_EM_ANDAMENTO

        # Concluir
        chamado.status = Chamado.STATUS_EM_REVISAO
        chamado.save()
        mudar_status(chamado, Chamado.STATUS_CONCLUIDO, admin_user)
        chamado.refresh_from_db()
        assert chamado.concluido_em is not None

        # Reabrir sem comentário -> falha
        with pytest.raises(ValidationError):
            mudar_status(chamado, Chamado.STATUS_EM_ANDAMENTO, admin_user, comentario="")

        # Reabrir com comentário -> sucesso e limpa concluido_em
        mudar_status(chamado, Chamado.STATUS_EM_ANDAMENTO, admin_user, comentario="Bug reaberto pelo cliente")
        chamado.refresh_from_db()
        assert chamado.status == Chamado.STATUS_EM_ANDAMENTO
        assert chamado.concluido_em is None

    def test_cancelamento_requer_admin_e_motivo(self, plataforma, admin_user, dev_1):
        chamado = Chamado.objects.create(
            titulo='Cancelar Test',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            responsavel=dev_1
        )
        # Dev tentando cancelar -> falha
        with pytest.raises(ValidationError):
            mudar_status(chamado, Chamado.STATUS_CANCELADO, dev_1, comentario="Motivo dev")

        # Admin sem motivo -> falha
        with pytest.raises(ValidationError):
            mudar_status(chamado, Chamado.STATUS_CANCELADO, admin_user, comentario="")

        # Admin com motivo -> sucesso
        mudar_status(chamado, Chamado.STATUS_CANCELADO, admin_user, comentario="Projeto descontinuado")
        chamado.refresh_from_db()
        assert chamado.status == Chamado.STATUS_CANCELADO


@pytest.mark.django_db
class TestViewsChamadosPermissoes:
    def test_visibilidade_da_lista_dev_vs_admin(self, client, plataforma, admin_user, dev_1, dev_2):
        c1 = Chamado.objects.create(titulo='C1 Dev 1', descricao='D', plataforma=plataforma, criado_por=admin_user, responsavel=dev_1)
        c2 = Chamado.objects.create(titulo='C2 Dev 2', descricao='D', plataforma=plataforma, criado_por=admin_user, responsavel=dev_2)
        c3 = Chamado.objects.create(titulo='C3 Criado Dev 1', descricao='D', plataforma=plataforma, criado_por=dev_1, responsavel=None)

        # Admin vê todos
        client.login(username='admin_boss', password='password123')
        res_admin = client.get(reverse('chamados:chamado_list'))
        assert res_admin.status_code == 200
        assert c1.codigo in res_admin.content.decode()
        assert c2.codigo in res_admin.content.decode()
        assert c3.codigo in res_admin.content.decode()
        client.logout()

        # Dev 1 vê c1 (atribuído) e c3 (criado), mas NÃO vê c2
        client.login(username='dev_alice', password='password123')
        res_dev1 = client.get(reverse('chamados:chamado_list'))
        assert res_dev1.status_code == 200
        content_dev1 = res_dev1.content.decode()
        assert c1.codigo in content_dev1
        assert c3.codigo in content_dev1
        assert c2.codigo not in content_dev1

    def test_detalhe_acesso_negado_dev(self, client, plataforma, admin_user, dev_1, dev_2):
        c_bob = Chamado.objects.create(titulo='Segredo Bob', descricao='D', plataforma=plataforma, criado_por=admin_user, responsavel=dev_2)
        client.login(username='dev_alice', password='password123')

        res = client.get(reverse('chamados:chamado_detail', kwargs={'pk': c_bob.pk}))
        assert res.status_code == 403

    def test_dev_cria_chamado_sem_responsavel(self, client, plataforma, dev_1):
        client.login(username='dev_alice', password='password123')
        res = client.post(reverse('chamados:chamado_create'), {
            'titulo': 'Novo Bug pelo Dev',
            'descricao': 'Descricao completa',
            'plataforma': plataforma.pk,
            'tipo': Chamado.TIPO_BUG,
        })
        assert res.status_code == 302
        novo_c = Chamado.objects.get(titulo='Novo Bug pelo Dev')
        assert novo_c.criado_por == dev_1
        assert novo_c.responsavel is None
        assert novo_c.prioridade == Chamado.PRIORIDADE_MEDIA

    def test_dev_nao_pode_editar_chamado(self, client, plataforma, dev_1):
        c = Chamado.objects.create(titulo='Original', descricao='D', plataforma=plataforma, criado_por=dev_1)
        client.login(username='dev_alice', password='password123')

        res = client.get(reverse('chamados:chamado_update', kwargs={'pk': c.pk}))
        assert res.status_code == 403


@pytest.mark.django_db
class TestKanban:
    def test_kanban_view_visibilidade_admin_e_dev(self, client, plataforma, admin_user, dev_1, dev_2):
        c1 = Chamado.objects.create(titulo='C1 Dev 1', descricao='D', plataforma=plataforma, criado_por=admin_user, responsavel=dev_1)
        c2 = Chamado.objects.create(titulo='C2 Dev 2', descricao='D', plataforma=plataforma, criado_por=admin_user, responsavel=dev_2)

        # Admin vê ambos
        client.login(username='admin_boss', password='password123')
        res_admin = client.get(reverse('chamados:kanban'))
        assert res_admin.status_code == 200
        assert c1.codigo in res_admin.content.decode()
        assert c2.codigo in res_admin.content.decode()
        client.logout()

        # Dev 1 só vê c1
        client.login(username='dev_alice', password='password123')
        res_dev1 = client.get(reverse('chamados:kanban'))
        assert res_dev1.status_code == 200
        content = res_dev1.content.decode()
        assert c1.codigo in content
        assert c2.codigo not in content

    def test_kanban_mover_transicao_valida_e_ordem(self, client, plataforma, admin_user, dev_1):
        c1 = Chamado.objects.create(titulo='C1', descricao='D', plataforma=plataforma, criado_por=admin_user, responsavel=dev_1, status=Chamado.STATUS_ABERTO)
        c2 = Chamado.objects.create(titulo='C2', descricao='D', plataforma=plataforma, criado_por=admin_user, responsavel=dev_1, status=Chamado.STATUS_ABERTO)

        client.login(username='dev_alice', password='password123')
        res = client.post(
            reverse('chamados:kanban_mover'),
            data={'chamado_id': c1.pk, 'novo_status': Chamado.STATUS_EM_ANDAMENTO, 'ordem_ids': [c1.pk, c2.pk]},
            content_type='application/json'
        )
        assert res.status_code == 200
        dados = res.json()
        assert dados['sucesso'] is True

        c1.refresh_from_db()
        assert c1.status == Chamado.STATUS_EM_ANDAMENTO
        assert c1.iniciado_em is not None

    def test_kanban_mover_transicao_invalida_recusada(self, client, plataforma, admin_user, dev_1):
        # Chamado Aberto sem responsável
        c = Chamado.objects.create(titulo='Sem dev', descricao='D', plataforma=plataforma, criado_por=admin_user, responsavel=None, status=Chamado.STATUS_ABERTO)

        client.login(username='admin_boss', password='password123')
        res = client.post(
            reverse('chamados:kanban_mover'),
            data={'chamado_id': c.pk, 'novo_status': Chamado.STATUS_EM_ANDAMENTO},
            content_type='application/json'
        )
        assert res.status_code == 400
        dados = res.json()
        assert dados['sucesso'] is False
        assert "responsável atribuído" in dados['erro']

        # Status permanece inalterado
        c.refresh_from_db()
        assert c.status == Chamado.STATUS_ABERTO

