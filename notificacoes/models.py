from django.db import models
from django.conf import settings


class Notificacao(models.Model):
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes'
    )
    chamado = models.ForeignKey(
        'chamados.Chamado',
        on_delete=models.CASCADE,
        related_name='notificacoes'
    )
    mensagem = models.CharField(max_length=255)
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-criada_em']

    def __str__(self):
        return f"Para {self.destinatario}: {self.mensagem}"
