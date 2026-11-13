from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

# Tempo sem sinal (ping) após o qual o usuário é considerado offline,
# mesmo que o contador de conexões não tenha zerado (ex.: queda do servidor).
TOLERANCIA_PRESENCA = timedelta(seconds=70)


class Conversa(models.Model):
    """Conversa direta entre dois usuários. As mensagens nunca são apagadas."""

    chave = models.CharField(
        max_length=50,
        unique=True,
        help_text='Identifica o par de usuários ("menor_id:maior_id"), garantindo uma conversa por par.',
    )
    participantes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='Participante',
        related_name='conversas',
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = 'Conversa'
        verbose_name_plural = 'Conversas'
        ordering = ['-atualizada_em']

    def __str__(self):
        return f'Conversa {self.chave}'

    @staticmethod
    def chave_para(usuario_a, usuario_b):
        ids = sorted([usuario_a.pk, usuario_b.pk])
        return f'{ids[0]}:{ids[1]}'


class Participante(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.PROTECT, related_name='participacoes')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='participacoes_chat'
    )
    lida_ate = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Participante'
        verbose_name_plural = 'Participantes'
        constraints = [
            models.UniqueConstraint(fields=['conversa', 'usuario'], name='participante_unico_por_conversa'),
        ]

    def __str__(self):
        return f'{self.usuario} em {self.conversa}'


class Mensagem(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.PROTECT, related_name='mensagens')
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='mensagens_chat'
    )
    texto = models.TextField(max_length=4000)
    criada_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
        ordering = ['criada_em', 'id']

    def __str__(self):
        return f'{self.autor}: {self.texto[:40]}'


class Presenca(models.Model):
    """Quantas conexões WebSocket o usuário tem abertas e quando deu o último sinal."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, related_name='presenca'
    )
    conexoes = models.PositiveIntegerField(default=0)
    ultimo_sinal = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Presença'
        verbose_name_plural = 'Presenças'

    @property
    def esta_online(self):
        return (
            self.conexoes > 0
            and self.ultimo_sinal is not None
            and self.ultimo_sinal >= timezone.now() - TOLERANCIA_PRESENCA
        )
