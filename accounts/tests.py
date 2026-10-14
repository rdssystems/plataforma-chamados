import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.management import call_command

Usuario = get_user_model()


@pytest.mark.django_db
class TestUsuarioModel:
    def test_criar_usuario_dev_default(self):
        user = Usuario.objects.create_user(
            username='dev_test',
            password='password123'
        )
        assert user.papel == Usuario.PAPEL_DEV
        assert user.deve_trocar_senha is True
        assert user.is_dev is True
        assert user.is_admin is False

    def test_criar_superuser_admin(self):
        admin = Usuario.objects.create_superuser(
            username='admin_test',
            password='password123',
            email='admin@teste.com'
        )
        assert admin.papel == Usuario.PAPEL_ADMIN
        assert admin.deve_trocar_senha is False
        assert admin.is_admin is True
        assert admin.is_dev is False

    def test_comando_criar_admin(self):
        call_command('criar_admin', username='supergestor', password='senhaforte123')
        gestor = Usuario.objects.get(username='supergestor')
        assert gestor.papel == Usuario.PAPEL_ADMIN
        assert gestor.deve_trocar_senha is False
        assert gestor.check_password('senhaforte123') is True


@pytest.mark.django_db
class TestAutenticacaoETrocaSenha:
    def test_redirecionamento_deve_trocar_senha(self, client):
        user = Usuario.objects.create_user(
            username='dev_novo',
            password='provisoria123'
        )
        client.login(username='dev_novo', password='provisoria123')

        # Usuário tenta acessar dashboard
        response = client.get(reverse('dashboard:index'))
        # Deve ser redirecionado para a tela de troca de senha
        assert response.status_code == 302
        assert response.url == reverse('accounts:trocar_senha')

    def test_troca_de_senha_com_sucesso(self, client):
        user = Usuario.objects.create_user(
            username='dev_novo',
            password='provisoria123'
        )
        client.login(username='dev_novo', password='provisoria123')

        # Realiza a troca de senha
        response = client.post(reverse('accounts:trocar_senha'), {
            'old_password': 'provisoria123',
            'new_password1': 'nova_senha_segura123',
            'new_password2': 'nova_senha_segura123',
        })
        assert response.status_code == 302

        user.refresh_from_db()
        assert user.deve_trocar_senha is False
        assert user.check_password('nova_senha_segura123') is True

        # Agora consegue acessar o dashboard normalmente
        res_dash = client.get(reverse('dashboard:index'))
        assert res_dash.status_code == 200

    def test_logout(self, client):
        user = Usuario.objects.create_superuser(
            username='admin_logout',
            password='password123'
        )
        client.login(username='admin_logout', password='password123')
        response = client.post(reverse('accounts:logout'))
        assert response.status_code == 302
        assert response.url == reverse('accounts:login')


@pytest.mark.django_db
class TestPermissoesEAdminRequired:
    def test_dev_recebe_403_ao_acessar_rotas_de_admin(self, client):
        dev = Usuario.objects.create_user(
            username='dev_comum',
            password='password123',
            deve_trocar_senha=False
        )
        client.login(username='dev_comum', password='password123')

        rotas_admin = [
            reverse('accounts:usuario_list'),
            reverse('accounts:usuario_create'),
            reverse('accounts:usuario_update', kwargs={'pk': dev.pk}),
            reverse('accounts:usuario_redefinir_senha', kwargs={'pk': dev.pk}),
        ]

        for rota in rotas_admin:
            response = client.get(rota)
            assert response.status_code == 403

    def test_admin_acessa_rotas_com_sucesso(self, client):
        admin = Usuario.objects.create_superuser(
            username='admin_gestor',
            password='password123'
        )
        client.login(username='admin_gestor', password='password123')

        response = client.get(reverse('accounts:usuario_list'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestGestaoUsuariosAdmin:
    def test_admin_cria_usuario_com_senha_provisoria(self, client):
        admin = Usuario.objects.create_superuser(
            username='admin_master',
            password='password123'
        )
        client.login(username='admin_master', password='password123')

        response = client.post(reverse('accounts:usuario_create'), {
            'username': 'dev_criado',
            'first_name': 'Dev',
            'last_name': 'Silva',
            'email': 'dev@empresa.com',
            'papel': Usuario.PAPEL_DEV,
            'senha_provisoria': 'senhaTemp123',
        })
        assert response.status_code == 302

        novo_usuario = Usuario.objects.get(username='dev_criado')
        assert novo_usuario.papel == Usuario.PAPEL_DEV
        assert novo_usuario.deve_trocar_senha is True
        assert novo_usuario.check_password('senhaTemp123') is True
        assert novo_usuario.is_active is True

    def test_admin_desativa_e_reativa_usuario(self, client):
        admin = Usuario.objects.create_superuser(
            username='admin_master',
            password='password123'
        )
        dev = Usuario.objects.create_user(
            username='dev_alvo',
            password='password123'
        )
        client.login(username='admin_master', password='password123')

        # Desativa
        response = client.post(reverse('accounts:usuario_toggle', kwargs={'pk': dev.pk}))
        assert response.status_code == 302
        dev.refresh_from_db()
        assert dev.is_active is False

        # Reativa
        response = client.post(reverse('accounts:usuario_toggle', kwargs={'pk': dev.pk}))
        assert response.status_code == 302
        dev.refresh_from_db()
        assert dev.is_active is True

    def test_admin_nao_pode_desativar_a_si_proprio(self, client):
        admin = Usuario.objects.create_superuser(
            username='admin_master',
            password='password123'
        )
        client.login(username='admin_master', password='password123')

        response = client.post(reverse('accounts:usuario_toggle', kwargs={'pk': admin.pk}))
        assert response.status_code == 302
        admin.refresh_from_db()
        assert admin.is_active is True

    def test_admin_redefine_senha_provisoria(self, client):
        admin = Usuario.objects.create_superuser(
            username='admin_master',
            password='password123'
        )
        dev = Usuario.objects.create_user(
            username='dev_esquecido',
            password='antiga123',
            deve_trocar_senha=False
        )
        client.login(username='admin_master', password='password123')

        response = client.post(reverse('accounts:usuario_redefinir_senha', kwargs={'pk': dev.pk}), {
            'nova_senha_provisoria': 'reset123456'
        })
        assert response.status_code == 302

        dev.refresh_from_db()
        assert dev.check_password('reset123456') is True
        assert dev.deve_trocar_senha is True
