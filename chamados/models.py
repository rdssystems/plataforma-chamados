from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Chamado(models.Model):
    TIPO_BUG = 'bug'
    TIPO_MELHORIA = 'melhoria'
    TIPO_NOVA_FUNCIONALIDADE = 'nova_funcionalidade'
    TIPO_SUPORTE = 'suporte'
    TIPO_CHOICES = [
        (TIPO_BUG, 'Bug'),
        (TIPO_MELHORIA, 'Melhoria'),
        (TIPO_NOVA_FUNCIONALIDADE, 'Nova Funcionalidade'),
        (TIPO_SUPORTE, 'Suporte'),
    ]

    PRIORIDADE_BAIXA = 'baixa'
    PRIORIDADE_MEDIA = 'media'
    PRIORIDADE_ALTA = 'alta'
    PRIORIDADE_URGENTE = 'urgente'
    PRIORIDADE_CHOICES = [
        (PRIORIDADE_BAIXA, 'Baixa'),
        (PRIORIDADE_MEDIA, 'Média'),
        (PRIORIDADE_ALTA, 'Alta'),
        (PRIORIDADE_URGENTE, 'Urgente'),
    ]

    STATUS_ABERTO = 'aberto'
    STATUS_EM_ANDAMENTO = 'em_andamento'
    STATUS_EM_REVISAO = 'em_revisao'
    STATUS_CONCLUIDO = 'concluido'
    STATUS_CANCELADO = 'cancelado'
    STATUS_CHOICES = [
        (STATUS_ABERTO, 'Aberto'),
        (STATUS_EM_ANDAMENTO, 'Em andamento'),
        (STATUS_EM_REVISAO, 'Em revisão'),
        (STATUS_CONCLUIDO, 'Concluído'),
        (STATUS_CANCELADO, 'Cancelado'),
    ]

    STATUS_FINAIS = [STATUS_CONCLUIDO, STATUS_CANCELADO]

    codigo = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    titulo = models.CharField(max_length=200, verbose_name='Título')
    descricao = models.TextField(verbose_name='Descrição')
    plataforma = models.ForeignKey(
        'plataformas.Plataforma',
        on_delete=models.PROTECT,
        related_name='chamados',
        verbose_name='Plataforma'
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default=TIPO_BUG, verbose_name='Tipo')
    prioridade = models.CharField(
        max_length=20,
        choices=PRIORIDADE_CHOICES,
        default=PRIORIDADE_MEDIA,
        verbose_name='Prioridade'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ABERTO,
        verbose_name='Status'
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='chamados_criados',
        verbose_name='Criado por'
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chamados_atribuidos',
        verbose_name='Responsável'
    )
    prazo = models.DateField(null=True, blank=True, verbose_name='Prazo')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    iniciado_em = models.DateTimeField(null=True, blank=True, verbose_name='Iniciado em')
    concluido_em = models.DateTimeField(null=True, blank=True, verbose_name='Concluído em')
    ordem_kanban = models.PositiveIntegerField(default=0, verbose_name='Ordem Kanban')

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Chamado'
        verbose_name_plural = 'Chamados'
        ordering = ['ordem_kanban', '-criado_em']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['responsavel', 'status']),
            models.Index(fields=['plataforma']),
            models.Index(fields=['criado_em']),
            models.Index(fields=['concluido_em']),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.titulo}"

    @property
    def esta_atrasado(self):
        if not self.prazo:
            return False
        if self.status in self.STATUS_FINAIS:
            return False
        return self.prazo < timezone.localdate()

    @property
    def tempo_resolucao(self):
        if self.concluido_em and self.criado_em:
            return self.concluido_em - self.criado_em
        return None

    def save(self, *args, **kwargs):
        if not self.codigo:
            with transaction.atomic():
                ultimo = Chamado.objects.select_for_update().order_by('-id').first()
                if ultimo and ultimo.codigo and ultimo.codigo.startswith('CH-'):
                    try:
                        numero_atual = int(ultimo.codigo.replace('CH-', ''))
                        proximo_numero = numero_atual + 1
                    except ValueError:
                        proximo_numero = (ultimo.id or 0) + 1
                else:
                    proximo_numero = (ultimo.id + 1) if ultimo else 1
                self.codigo = f"CH-{proximo_numero:04d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class MudancaStatus(models.Model):
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name='mudancas_status')
    de_status = models.CharField(max_length=20, choices=Chamado.STATUS_CHOICES)
    para_status = models.CharField(max_length=20, choices=Chamado.STATUS_CHOICES)
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    alterado_em = models.DateTimeField(auto_now_add=True)
    comentario_motivo = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Mudança de Status'
        verbose_name_plural = 'Mudanças de Status'
        ordering = ['-alterado_em']

    def __str__(self):
        return f"{self.chamado.codigo}: {self.de_status} -> {self.para_status} por {self.alterado_por}"


class Comentario(models.Model):
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='comentarios_feitos')
    texto = models.TextField(verbose_name='Comentário')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
        ordering = ['criado_em']

    def __str__(self):
        return f"Comentário de {self.autor} em {self.chamado.codigo}"


class Anexo(models.Model):
    LIMITE_TAMANHO_BYTES = 10 * 1024 * 1024  # 10 MB

    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to='anexos/%Y/%m/', verbose_name='Arquivo')
    nome_original = models.CharField(max_length=255, verbose_name='Nome Original')
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='anexos_enviados')
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'
        ordering = ['-enviado_em']

    def __str__(self):
        return f"{self.nome_original} ({self.chamado.codigo})"

