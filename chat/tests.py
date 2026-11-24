from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone

from chamados.models import Chamado
from notificacoes.models import Notificacao
from plataformas.models import Plataforma

from . import services
from .consumers import FECHAR_NAO_AUTENTICADO, TempoRealConsumer
from .models import Conversa, Mensagem, Participante, Presenca
from .tempo_real import grupo_usuario

Usuario = get_user_model()


@pytest.fixture
def alice():
    return Usuario.objects.create_user(username='alice', password='senha12345', deve_trocar_senha=False)


@pytest.fixture
def bob():
    return Usuario.objects.create_user(username='bob', password='senha12345', deve_trocar_senha=False)


@pytest.fixture
def carol():
    return Usuario.objects.create_user(username='carol', password='senha12345', deve_trocar_senha=False)


@pytest.fixture
def conversa(alice, bob):
    return services.obter_ou_criar_conversa(alice, bob)


@pytest.mark.django_db
class TestServicos:
    def test_conversa_unica_por_par_independente_da_ordem(self, alice, bob):
        c1 = services.obter_ou_criar_conversa(alice, bob)
        c2 = services.obter_ou_criar_conversa(bob, alice)
        assert c1.pk == c2.pk
        assert Conversa.objects.count() == 1
        assert set(c1.participantes.values_list('username', flat=True)) == {'alice', 'bob'}

    def test_nao_conversa_consigo_mesmo(self, alice):
        with pytest.raises(ValidationError):
            services.obter_ou_criar_conversa(alice, alice)

    def test_mensagem_vazia_ou_longa_e_rejeitada(self, conversa, alice):
        with pytest.raises(ValidationError):
            services.enviar_mensagem(conversa, alice, '   ')
        with pytest.raises(ValidationError):
            services.enviar_mensagem(conversa, alice, 'x' * 4001)

    def test_contagem_de_nao_lidas(self, conversa, alice, bob):
        services.enviar_mensagem(conversa, alice, 'Oi Bob')
        services.enviar_mensagem(conversa, alice, 'Tudo bem?')
        assert services.total_nao_lidas(bob) == 2
        assert services.total_nao_lidas(alice) == 0  # as próprias mensagens não contam

        services.marcar_conversa_lida(conversa, bob)
        assert services.total_nao_lidas(bob) == 0

        services.enviar_mensagem(conversa, alice, 'Mais uma')
        assert services.total_nao_lidas(bob) == 1

    def test_mensagem_no_mesmo_instante_da_leitura_conta_como_nao_lida(self, conversa, alice, bob):
        # Relógio com pouca precisão (Windows) gera horários iguais; a leitura é marcada pelo id.
        services.enviar_mensagem(conversa, alice, 'Primeira')
        services.marcar_conversa_lida(conversa, bob)
        leitura = Participante.objects.get(conversa=conversa, usuario=bob).lida_ate
        nova = services.enviar_mensagem(conversa, alice, 'Mesmo instante')
        Mensagem.objects.filter(pk=nova.pk).update(criada_em=leitura)
        assert services.total_nao_lidas(bob) == 1

    def test_migracao_converte_leitura_por_horario_em_id(self, conversa, alice, bob):
        from importlib import import_module
        from django.apps import apps
        migracao = import_module('chat.migrations.0002_ultima_lida_por_id')
        antiga = services.enviar_mensagem(conversa, alice, 'Antiga')
        recente = services.enviar_mensagem(conversa, alice, 'Recente')
        agora = timezone.now()
        Mensagem.objects.filter(pk=antiga.pk).update(criada_em=agora - timedelta(hours=2))
        Mensagem.objects.filter(pk=recente.pk).update(criada_em=agora)
        Participante.objects.filter(conversa=conversa, usuario=bob).update(
            lida_ate=agora - timedelta(hours=1), ultima_lida_id=0
        )
        migracao.preencher_ultima_lida(apps, None)
        assert Participante.objects.get(conversa=conversa, usuario=bob).ultima_lida_id == antiga.pk
        assert services.total_nao_lidas(bob) == 1

    def test_lista_de_conversas_traz_outro_participante_e_ultima_mensagem(self, conversa, alice, bob):
        services.enviar_mensagem(conversa, bob, 'Primeira')
        services.enviar_mensagem(conversa, bob, 'Segunda')
        [c] = services.conversas_do_usuario(alice)
        assert c.outro == bob
        assert c.ultima_mensagem.texto == 'Segunda'
        assert c.nao_lidas == 2

    def test_historico_e_permanente(self, conversa, alice):
        services.enviar_mensagem(conversa, alice, 'Registro')
        with pytest.raises(ProtectedError):
            alice.delete()
        with pytest.raises(ProtectedError):
            conversa.delete()
        assert Mensagem.objects.count() == 1


@pytest.mark.django_db
class TestPresenca:
    def test_online_enquanto_houver_conexao(self, alice):
        assert services.registrar_conexao(alice.pk) is True   # ficou online
        assert services.registrar_conexao(alice.pk) is False  # segunda aba
        assert alice.pk in services.ids_online()
        assert services.registrar_desconexao(alice.pk) is False
        assert alice.pk in services.ids_online()
        assert services.registrar_desconexao(alice.pk) is True
        assert alice.pk not in services.ids_online()

    def test_conexao_sem_sinal_expira(self, alice):
        services.registrar_conexao(alice.pk)
        Presenca.objects.filter(usuario=alice).update(ultimo_sinal=timezone.now() - timedelta(minutes=5))
        assert alice.pk not in services.ids_online()
        # Nova conexão descarta a contagem antiga, que ficou "presa".
        assert services.registrar_conexao(alice.pk) is True
        assert Presenca.objects.get(usuario=alice).conexoes == 1


@pytest.mark.django_db
class TestViews:
    def test_exige_login(self, client):
        response = client.get(reverse('chat:index'))
        assert response.status_code == 302
        assert reverse('accounts:login') in response.url

    def test_iniciar_conversa_redireciona_para_ela(self, client, alice, bob):
        client.force_login(alice)
        response = client.post(reverse('chat:iniciar', args=[bob.pk]))
        conversa = Conversa.objects.get()
        assert response.status_code == 302
        assert response.url == reverse('chat:conversa', args=[conversa.pk])

    def test_nao_inicia_conversa_com_usuario_desativado(self, client, alice, bob):
        bob.is_active = False
        bob.save()
        client.force_login(alice)
        assert client.post(reverse('chat:iniciar', args=[bob.pk])).status_code == 404

    def test_enviar_e_listar_mensagens(self, client, conversa, alice):
        client.force_login(alice)
        response = client.post(reverse('chat:enviar', args=[conversa.pk]), {'texto': 'Olá!'})
        assert response.status_code == 201
        assert response.json()['mensagem']['texto'] == 'Olá!'

        response = client.get(reverse('chat:mensagens', args=[conversa.pk]))
        assert [m['texto'] for m in response.json()['mensagens']] == ['Olá!']

    def test_mensagem_vazia_retorna_erro(self, client, conversa, alice):
        client.force_login(alice)
        response = client.post(reverse('chat:enviar', args=[conversa.pk]), {'texto': ''})
        assert response.status_code == 400
        assert 'vazia' in response.json()['erro']

    def test_nao_participante_nao_acessa_conversa(self, client, conversa, carol):
        client.force_login(carol)
        assert client.get(reverse('chat:conversa', args=[conversa.pk])).status_code == 404
        assert client.get(reverse('chat:mensagens', args=[conversa.pk])).status_code == 404
        assert client.post(reverse('chat:enviar', args=[conversa.pk]), {'texto': 'intrusa'}).status_code == 404
        assert Mensagem.objects.count() == 0

    def test_abrir_conversa_marca_como_lida(self, client, conversa, alice, bob):
        services.enviar_mensagem(conversa, alice, 'Oi')
        client.force_login(bob)
        response = client.get(reverse('chat:conversa', args=[conversa.pk]))
        assert response.status_code == 200
        assert services.total_nao_lidas(bob) == 0

    def test_paginacao_do_historico(self, client, conversa, alice):
        for i in range(55):
            services.enviar_mensagem(conversa, alice, f'msg {i}')
        client.force_login(alice)
        url = reverse('chat:mensagens', args=[conversa.pk])

        recentes = client.get(url).json()
        assert len(recentes['mensagens']) == 50
        assert recentes['tem_mais'] is True
        assert recentes['mensagens'][-1]['texto'] == 'msg 54'

        antigas = client.get(url, {'antes': recentes['mensagens'][0]['id']}).json()
        assert [m['texto'] for m in antigas['mensagens']] == [f'msg {i}' for i in range(5)]
        assert antigas['tem_mais'] is False

        novas = client.get(url, {'depois': recentes['mensagens'][-2]['id']}).json()
        assert [m['texto'] for m in novas['mensagens']] == ['msg 54']

    def test_conversa_com_usuario_desativado_mantem_historico_e_bloqueia_envio(self, client, conversa, alice, bob):
        services.enviar_mensagem(conversa, bob, 'Antes de sair')
        bob.is_active = False
        bob.save()
        client.force_login(alice)
        response = client.get(reverse('chat:conversa', args=[conversa.pk]))
        assert response.status_code == 200
        assert response.context['pode_enviar'] is False
        assert client.post(reverse('chat:enviar', args=[conversa.pk]), {'texto': 'Oi?'}).status_code == 400

    def test_lista_de_usuarios_mostra_online_primeiro(self, client, alice, bob, carol):
        services.registrar_conexao(carol.pk)
        client.force_login(alice)
        response = client.get(reverse('chat:usuarios'))
        usuarios = response.context['usuarios']
        assert [u.username for u in usuarios] == ['carol', 'bob']
        assert response.context['total_online'] == 1

    def test_menu_mostra_contador_de_nao_lidas(self, client, conversa, alice, bob):
        services.enviar_mensagem(conversa, alice, 'Oi')
        client.force_login(bob)
        response = client.get(reverse('dashboard:index'))
        assert response.context['chat_nao_lidas_count'] == 1


def _conectar(usuario):
    communicator = WebsocketCommunicator(TempoRealConsumer.as_asgi(), '/ws/app/')
    communicator.scope['user'] = usuario
    return communicator


@pytest.mark.django_db(transaction=True)
class TestWebSocket:
    def test_recusa_anonimo(self):
        from django.contrib.auth.models import AnonymousUser

        async def cenario():
            communicator = _conectar(AnonymousUser())
            await communicator.connect()
            saida = await communicator.receive_output()
            assert saida == {'type': 'websocket.close', 'code': FECHAR_NAO_AUTENTICADO}

        async_to_sync(cenario)()

    def test_recebe_mensagem_e_presenca_em_tempo_real(self, alice, bob):
        conversa = services.obter_ou_criar_conversa(alice, bob)

        async def cenario():
            ws_bob = _conectar(bob)
            assert (await ws_bob.connect())[0]
            evento = await ws_bob.receive_json_from()
            assert evento == {'tipo': 'presenca', 'usuario_id': bob.pk, 'online': True}

            ws_alice = _conectar(alice)
            assert (await ws_alice.connect())[0]
            evento = await ws_bob.receive_json_from()
            assert evento == {'tipo': 'presenca', 'usuario_id': alice.pk, 'online': True}
            await ws_alice.receive_json_from()  # o próprio aviso de presença

            await ws_alice.send_json_to({'tipo': 'ping'})
            assert await ws_alice.receive_json_from() == {'tipo': 'pong'}

            from channels.db import database_sync_to_async
            await database_sync_to_async(services.enviar_mensagem)(conversa, alice, 'Tempo real!')

            evento = await ws_bob.receive_json_from()
            assert evento['tipo'] == 'chat.mensagem'
            assert evento['mensagem']['texto'] == 'Tempo real!'
            assert evento['nao_lidas_total'] == 1

            await ws_alice.disconnect()
            evento = await ws_bob.receive_json_from()
            assert evento == {'tipo': 'presenca', 'usuario_id': alice.pk, 'online': False}
            await ws_bob.disconnect()

        async_to_sync(cenario)()

    def test_notificacao_chega_em_tempo_real(self, alice, bob):
        plataforma = Plataforma.objects.create(nome='Web', cor='#000000')
        chamado = Chamado.objects.create(titulo='Bug', descricao='Desc', plataforma=plataforma, criado_por=alice)

        async def cenario():
            ws_bob = _conectar(bob)
            assert (await ws_bob.connect())[0]
            await ws_bob.receive_json_from()  # presença

            from channels.db import database_sync_to_async
            await database_sync_to_async(Notificacao.objects.create)(
                destinatario=bob, chamado=chamado, mensagem='Você foi atribuído.'
            )
            evento = await ws_bob.receive_json_from()
            assert evento['tipo'] == 'notificacao'
            assert evento['mensagem'] == 'Você foi atribuído.'
            assert evento['nao_lidas'] == 1
            await ws_bob.disconnect()

        async_to_sync(cenario)()


def test_evento_enviado_ao_grupo_do_usuario():
    """Sanidade da camada de canais configurada (em memória nos testes)."""
    layer = get_channel_layer()

    async def cenario():
        canal = await layer.new_channel()
        await layer.group_add(grupo_usuario(1), canal)
        await layer.group_send(grupo_usuario(1), {'type': 'evento', 'dados': {'ok': True}})
        assert (await layer.receive(canal))['dados'] == {'ok': True}

    async_to_sync(cenario)()


@pytest.mark.django_db
class TestChatFlutuante:
    def test_iniciar_responde_json_para_a_janela_flutuante(self, client, alice, bob):
        client.force_login(alice)
        res = client.post(reverse('chat:iniciar', args=[bob.pk]), HTTP_ACCEPT='application/json')
        assert res.status_code == 200
        assert res.json()['conversa_id'] == Conversa.objects.get().pk

    def test_iniciar_consigo_mesmo_em_json_da_erro_400(self, client, alice):
        client.force_login(alice)
        res = client.post(reverse('chat:iniciar', args=[alice.pk]), HTTP_ACCEPT='application/json')
        assert res.status_code == 400
        assert 'consigo mesmo' in res.json()['erro']

    def test_resumo_traz_o_necessario_para_abrir_a_conversa(self, client, conversa, alice, bob):
        services.enviar_mensagem(conversa, bob, 'Oi Alice')
        client.force_login(alice)
        dados = client.get(reverse('chat:resumo', args=[conversa.pk])).json()
        assert dados['id'] == conversa.pk
        assert dados['outro']['nome'] == 'bob' and dados['outro']['ativo'] is True
        assert dados['pode_enviar'] is True
        assert [m['texto'] for m in dados['mensagens']] == ['Oi Alice']
        assert dados['urls']['enviar'] == reverse('chat:enviar', args=[conversa.pk])
        # Abrir o resumo não marca como lida: quem marca é a janela, só se estiver à vista.
        assert services.total_nao_lidas(alice) == 1

    def test_resumo_de_conversa_alheia_e_404(self, client, conversa, carol):
        client.force_login(carol)
        assert client.get(reverse('chat:resumo', args=[conversa.pk])).status_code == 404

    def test_janela_aparece_nas_paginas_mas_nao_no_chat(self, client, alice):
        client.force_login(alice)
        painel = client.get(reverse('dashboard:index')).content.decode()
        assert 'id="chat-flutuante"' in painel and 'js/chat_flutuante.js' in painel
        pagina_chat = client.get(reverse('chat:index')).content.decode()
        assert 'id="chat-flutuante"' not in pagina_chat
        assert 'data-pref="som"' in pagina_chat  # as preferências de aviso também ficam na página do chat

    def test_janela_nao_aparece_sem_login_nem_na_troca_obrigatoria_de_senha(self, client, alice):
        assert 'id="chat-flutuante"' not in client.get(reverse('accounts:login')).content.decode()
        alice.deve_trocar_senha = True
        alice.save()
        client.force_login(alice)
        assert 'id="chat-flutuante"' not in client.get(reverse('accounts:trocar_senha')).content.decode()

    def test_lista_de_usuarios_permite_iniciar_pela_janela(self, client, alice, bob):
        client.force_login(alice)
        html = client.get(reverse('chat:usuarios')).content.decode()
        assert 'data-iniciar-conversa' in html
