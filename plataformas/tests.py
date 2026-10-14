import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from plataformas.models import Plataforma

Usuario = get_user_model()


@pytest.mark.django_db
class TestPlataformas:
    def test_admin_crud_plataforma(self, client):
        admin = Usuario.objects.create_superuser(username='admin_plat', password='password123')
        client.login(username='admin_plat', password='password123')

        # Criar
        res_create = client.post(reverse('plataformas:plataforma_create'), {
            'nome': 'Portal do Cliente',
            'descricao': 'Portal web para clientes',
            'url': 'https://cliente.empresa.com',
            'cor': '#3B82F6',
            'ativa': True,
        })
        assert res_create.status_code == 302
        plat = Plataforma.objects.get(nome='Portal do Cliente')
        assert plat.cor == '#3B82F6'
        assert plat.ativa is True

        # Listar
        res_list = client.get(reverse('plataformas:plataforma_list'))
        assert res_list.status_code == 200
        assert 'Portal do Cliente' in res_list.content.decode()

        # Editar
        res_edit = client.post(reverse('plataformas:plataforma_update', kwargs={'pk': plat.pk}), {
            'nome': 'Portal do Cliente VIP',
            'descricao': 'Atualizado',
            'url': 'https://cliente.empresa.com',
            'cor': '#10B981',
            'ativa': True,
        })
        assert res_edit.status_code == 302
        plat.refresh_from_db()
        assert plat.nome == 'Portal do Cliente VIP'
        assert plat.cor == '#10B981'

        # Toggle Ativa
        res_toggle = client.post(reverse('plataformas:plataforma_toggle', kwargs={'pk': plat.pk}))
        assert res_toggle.status_code == 302
        plat.refresh_from_db()
        assert plat.ativa is False

    def test_dev_nao_tem_acesso_a_plataformas(self, client):
        dev = Usuario.objects.create_user(username='dev_plat', password='password123', deve_trocar_senha=False)
        plat = Plataforma.objects.create(nome='Sistema Interno', cor='#EF4444')
        client.login(username='dev_plat', password='password123')

        rotas = [
            reverse('plataformas:plataforma_list'),
            reverse('plataformas:plataforma_create'),
            reverse('plataformas:plataforma_update', kwargs={'pk': plat.pk}),
            reverse('plataformas:plataforma_toggle', kwargs={'pk': plat.pk}),
        ]
        for rota in rotas:
            res = client.get(rota)
            assert res.status_code == 403
