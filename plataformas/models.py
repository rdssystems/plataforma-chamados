from django.db import models


class Plataforma(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name='Nome')
    descricao = models.TextField(blank=True, null=True, verbose_name='Descrição')
    url = models.URLField(blank=True, null=True, verbose_name='URL da Plataforma')
    cor = models.CharField(max_length=7, default='#3B82F6', verbose_name='Cor Hexadecimal')
    ativa = models.BooleanField(default=True, verbose_name='Ativa')

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plataforma'
        verbose_name_plural = 'Plataformas'
        ordering = ['nome']

    def __str__(self):
        return self.nome
