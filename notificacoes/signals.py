from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from chat.tempo_real import publicar_para_usuario

from .models import Notificacao


@receiver(post_save, sender=Notificacao, dispatch_uid='notificacao_tempo_real')
def enviar_notificacao_em_tempo_real(sender, instance, created, raw=False, **kwargs):
    """Avisa o navegador do destinatário assim que a notificação é criada."""
    if not created or raw:
        return
    publicar_para_usuario(instance.destinatario_id, {
        'tipo': 'notificacao',
        'mensagem': instance.mensagem,
        'url': reverse('chamados:chamado_detail', args=[instance.chamado_id]),
        'nao_lidas': Notificacao.objects.filter(destinatario_id=instance.destinatario_id, lida=False).count(),
    })
