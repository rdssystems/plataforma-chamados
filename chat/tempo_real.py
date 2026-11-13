"""Envio de eventos em tempo real para os navegadores conectados via WebSocket.

Cada usuário conectado entra no grupo ``usuario_<id>``; todos entram em ``presenca``.
Os eventos são enviados só depois do commit da transação, para que o navegador
nunca receba um evento sobre algo que ainda não está no banco.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)

GRUPO_PRESENCA = 'presenca'


def grupo_usuario(usuario_id):
    return f'usuario_{usuario_id}'


def _enviar(grupo, dados):
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(grupo, {'type': 'evento', 'dados': dados})
    except Exception:  # tempo real é "melhor esforço": nunca derruba a requisição
        logger.exception('Falha ao enviar evento em tempo real para %s', grupo)


def publicar_para_usuario(usuario_id, dados):
    transaction.on_commit(lambda: _enviar(grupo_usuario(usuario_id), dados))


def publicar_presenca(dados):
    transaction.on_commit(lambda: _enviar(GRUPO_PRESENCA, dados))
