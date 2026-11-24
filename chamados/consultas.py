"""Regras de cálculo das situações usadas nos indicadores e nas consultas.

O dashboard conta e a listagem de chamados filtra com as MESMAS regras, para que o
número de um indicador possa ser reproduzido abrindo a consulta correspondente
(critério de aceite "Indicador e detalhamento" do padrão da Secretaria).
"""
from django.db.models import Q
from django.utils import timezone

from .models import Chamado

SITUACOES = [
    ('abertos', 'Abertos'),
    ('em_andamento', 'Em andamento ou em revisão'),
    ('atrasados', 'Atrasados'),
    ('concluidos_mes', 'Concluídos no mês'),
    ('sem_responsavel', 'Sem responsável'),
]


def q_situacao(situacao, hoje=None):
    hoje = hoje or timezone.localdate()
    ativos = ~Q(status__in=Chamado.STATUS_FINAIS)
    if situacao == 'abertos':
        return Q(status=Chamado.STATUS_ABERTO)
    if situacao == 'em_andamento':
        return Q(status__in=[Chamado.STATUS_EM_ANDAMENTO, Chamado.STATUS_EM_REVISAO])
    if situacao == 'atrasados':
        # Prazo vencido antes de hoje e chamado ainda não concluído nem cancelado.
        return Q(prazo__lt=hoje) & ativos
    if situacao == 'concluidos_mes':
        return Q(status=Chamado.STATUS_CONCLUIDO, concluido_em__date__gte=hoje.replace(day=1), concluido_em__date__lte=hoje)
    if situacao == 'sem_responsavel':
        return Q(responsavel__isnull=True) & ativos
    raise ValueError(f'Situação desconhecida: {situacao}')
