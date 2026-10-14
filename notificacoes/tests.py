import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from plataformas.models import Plataforma
from chamados.models import Chamado, Comentario, Anexo
from notificacoes.models import Notificacao
from chamados.services import mudar_status

Usuario = get_user_model()


@pytest.fixture
def plataforma():
    return Plataforma.objects.create(nome='App Mobile', cor='#10B981')


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
class TestComentariosEAnexos:
    def test_adicionar_comentario_gera_notificacao_ao_responsavel(self, client, plataforma, admin_user, dev_1):
        chamado = Chamado.objects.create(
            titulo='Ajustar login',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            responsavel=dev_1
        )
        client.login(username='admin_boss', password='password123')

        # Admin comenta no chamado
        response = client.post(reverse('chamados:comentario_create', kwargs={'pk': chamado.pk}), {
            'texto': 'Favor verificar os logs de autenticação.'
        })
        assert response.status_code == 302
        assert Comentario.objects.filter(chamado=chamado).count() == 1

        # O dev responsável deve ter recebido uma notificação
        notif = Notificacao.objects.filter(destinatario=dev_1).first()
        assert notif is not None
        assert chamado.codigo in notif.mensagem
        assert notif.lida is False

    def test_upload_anexo_valido_e_download_permitido(self, client, plataforma, admin_user, dev_1):
        chamado = Chamado.objects.create(
            titulo='Tela quebrada',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            responsavel=dev_1
        )
        client.login(username='dev_alice', password='password123')

        arquivo_conteudo = b"fake image content"
        arquivo = SimpleUploadedFile("print_erro.png", arquivo_conteudo, content_type="image/png")

        res_upload = client.post(reverse('chamados:anexo_upload', kwargs={'pk': chamado.pk}), {
            'arquivo': arquivo
        })
        assert res_upload.status_code == 302
        anexo = Anexo.objects.get(chamado=chamado)
        assert anexo.nome_original == "print_erro.png"
        assert anexo.enviado_por == dev_1

        # Dev responsável pode baixar
        res_down = client.get(reverse('chamados:anexo_download', kwargs={'pk': chamado.pk, 'anexo_pk': anexo.pk}))
        assert res_down.status_code == 200

    def test_download_anexo_negado_para_dev_nao_autorizado(self, client, plataforma, admin_user, dev_1, dev_2):
        chamado = Chamado.objects.create(
            titulo='Confidencial',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            responsavel=dev_1
        )
        arquivo = SimpleUploadedFile("dados.txt", b"secret", content_type="text/plain")
        anexo = Anexo.objects.create(
            chamado=chamado,
            arquivo=arquivo,
            nome_original="dados.txt",
            enviado_por=admin_user
        )

        # Dev 2 não tem relação com o chamado
        client.login(username='dev_bob', password='password123')
        res = client.get(reverse('chamados:anexo_download', kwargs={'pk': chamado.pk, 'anexo_pk': anexo.pk}))
        assert res.status_code == 403

    def test_upload_anexo_acima_do_limite_falha(self, client, plataforma, admin_user):
        chamado = Chamado.objects.create(
            titulo='Arquivo Gigante',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user
        )
        client.login(username='admin_boss', password='password123')

        # Cria arquivo com 11 MB (> 10 MB) de conteúdo real
        tamanho_excedido = 11 * 1024 * 1024
        arquivo_grande = SimpleUploadedFile("grande.bin", b"0" * tamanho_excedido, content_type="application/octet-stream")

        client.post(reverse('chamados:anexo_upload', kwargs={'pk': chamado.pk}), {
            'arquivo': arquivo_grande
        })
        # Não deve criar o Anexo no banco
        assert Anexo.objects.filter(chamado=chamado).count() == 0


@pytest.mark.django_db
class TestNotificacoes:
    def test_mudanca_status_notifica_responsavel(self, plataforma, admin_user, dev_1):
        chamado = Chamado.objects.create(
            titulo='Notif Status',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=admin_user,
            responsavel=dev_1
        )
        mudar_status(chamado, Chamado.STATUS_EM_ANDAMENTO, admin_user)

        notif = Notificacao.objects.filter(destinatario=dev_1).first()
        assert notif is not None
        assert "alterado para Em andamento" in notif.mensagem

    def test_marcar_notificacao_como_lida(self, client, plataforma, dev_1):
        chamado = Chamado.objects.create(
            titulo='Tarefa',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=dev_1
        )
        notif = Notificacao.objects.create(
            destinatario=dev_1,
            chamado=chamado,
            mensagem="Mensagem de teste",
            lida=False
        )
        client.login(username='dev_alice', password='password123')

        res = client.post(reverse('notificacoes:marcar_lida', kwargs={'pk': notif.pk}))
        assert res.status_code == 302
        notif.refresh_from_db()
        assert notif.lida is True

    def test_marcar_todas_como_lidas(self, client, plataforma, dev_1):
        chamado = Chamado.objects.create(
            titulo='Tarefa',
            descricao='Desc',
            plataforma=plataforma,
            criado_por=dev_1
        )
        Notificacao.objects.create(destinatario=dev_1, chamado=chamado, mensagem="Msg 1", lida=False)
        Notificacao.objects.create(destinatario=dev_1, chamado=chamado, mensagem="Msg 2", lida=False)

        client.login(username='dev_alice', password='password123')
        res = client.post(reverse('notificacoes:marcar_todas'))
        assert res.status_code == 302
        assert Notificacao.objects.filter(destinatario=dev_1, lida=False).count() == 0
