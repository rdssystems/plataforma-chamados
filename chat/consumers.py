from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import services
from .tempo_real import GRUPO_PRESENCA, grupo_usuario

# Códigos de fechamento (faixa 4000-4999 é livre para a aplicação).
FECHAR_NAO_AUTENTICADO = 4401


class TempoRealConsumer(AsyncJsonWebsocketConsumer):
    """Uma conexão por aba do navegador: recebe mensagens do chat, notificações e presença."""

    async def connect(self):
        usuario = self.scope.get('user')
        if (
            usuario is None
            or not usuario.is_authenticated
            or not usuario.is_active
            or getattr(usuario, 'deve_trocar_senha', False)
        ):
            # Aceitar antes de fechar: recusar no handshake vira um HTTP 403 sem código,
            # e o navegador não saberia que deve parar de tentar reconectar.
            await self.accept()
            await self.close(code=FECHAR_NAO_AUTENTICADO)
            return

        self.usuario_id = usuario.pk
        await self.channel_layer.group_add(grupo_usuario(self.usuario_id), self.channel_name)
        await self.channel_layer.group_add(GRUPO_PRESENCA, self.channel_name)
        await self.accept()

        ficou_online = await database_sync_to_async(services.registrar_conexao)(self.usuario_id)
        if ficou_online:
            await self._anunciar_presenca(online=True)

    async def disconnect(self, code):
        usuario_id = getattr(self, 'usuario_id', None)
        if usuario_id is None:
            return
        await self.channel_layer.group_discard(grupo_usuario(usuario_id), self.channel_name)
        await self.channel_layer.group_discard(GRUPO_PRESENCA, self.channel_name)
        ficou_offline = await database_sync_to_async(services.registrar_desconexao)(usuario_id)
        if ficou_offline:
            await self._anunciar_presenca(online=False)

    async def receive_json(self, content, **kwargs):
        if content.get('tipo') == 'ping':
            await database_sync_to_async(services.registrar_sinal)(self.usuario_id)
            await self.send_json({'tipo': 'pong'})

    async def evento(self, event):
        await self.send_json(event['dados'])

    async def _anunciar_presenca(self, online):
        await self.channel_layer.group_send(GRUPO_PRESENCA, {
            'type': 'evento',
            'dados': {'tipo': 'presenca', 'usuario_id': self.usuario_id, 'online': online},
        })
