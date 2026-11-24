from datetime import timedelta
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.http import JsonResponse
from django.contrib.auth import get_user_model

from chamados.models import Chamado, MudancaStatus
from chamados.consultas import q_situacao
from config.filtros import Filtros
from plataformas.models import Plataforma

Usuario = get_user_model()

SEMANAS_NO_GRAFICO = 12


def _totais_por_semana(qs_semanal):
    """{data da segunda-feira: total} a partir de um queryset anotado com TruncWeek."""
    totais = {}
    for item in qs_semanal:
        semana = item['semana']
        if semana is None:
            continue
        if timezone.is_aware(semana):
            semana = timezone.localtime(semana)
        totais[semana.date()] = item['total']
    return totais


MENSAGEM_DEV_INVALIDO = 'Selecione um desenvolvedor da lista.'


def _escopo(request, filtros):
    """Chamados que o usuário pode ver, já com o filtro de dev validado (admin)."""
    user = request.user
    if getattr(user, 'is_admin', False):
        devs = list(Usuario.objects.filter(is_active=True).order_by('first_name', 'username'))
        dev_id = filtros.id_entre('dev', [d.pk for d in devs], MENSAGEM_DEV_INVALIDO)
        qs = Chamado.objects.all()
        if dev_id:
            qs = qs.filter(responsavel_id=dev_id)
        dev = next((d for d in devs if d.pk == dev_id), None)
        return qs, devs, dev
    return Chamado.objects.filter(Q(responsavel=user) | Q(criado_por=user)), [], None


class DashboardIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        filtros = Filtros(self.request.GET)
        qs, devs, dev = _escopo(self.request, filtros)

        context.update({
            'hoje': hoje,
            'devs': devs,
            'dev_selecionado': filtros.brutos.get('dev', ''),
            'dev_filtrado': dev,
            'recorte_dev': f'somente {dev.get_full_name() or dev.username}' if dev else '',
            'filtros_erros': filtros.erros,
            'filtros_validos': filtros.validos,
        })
        # Filtro inválido: mantém a entrada e suspende os resultados até a correção.
        if not filtros.validos:
            return context

        # 1. Indicadores (1 consulta), com as mesmas regras da listagem de chamados.
        context['cards'] = qs.aggregate(
            total_abertos=Count('id', filter=q_situacao('abertos', hoje)),
            total_em_andamento=Count('id', filter=q_situacao('em_andamento', hoje)),
            total_atrasados=Count('id', filter=q_situacao('atrasados', hoje)),
            total_concluidos_mes=Count('id', filter=q_situacao('concluidos_mes', hoje)),
            total_sem_responsavel=Count('id', filter=q_situacao('sem_responsavel', hoje)),
        )

        # 2. Fila de trabalho
        context['chamados_atrasados'] = qs.filter(q_situacao('atrasados', hoje)).select_related(
            'plataforma', 'responsavel').order_by('prazo')[:5]
        context['chamados_vencendo'] = qs.filter(
            prazo__gte=hoje, prazo__lte=hoje + timedelta(days=3)
        ).exclude(status__in=Chamado.STATUS_FINAIS).select_related('plataforma', 'responsavel').order_by('prazo')[:5]

        # 3. Últimas 10 atividades
        context['ultimas_atividades'] = MudancaStatus.objects.filter(
            chamado__in=qs
        ).select_related('chamado', 'alterado_por').order_by('-alterado_em')[:10]
        return context


class DashboardGraficosJsonView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        hoje = timezone.localdate()
        inicio_mes = hoje.replace(day=1)
        # 12 semanas completas (segunda a domingo), incluindo a atual.
        semanas = [hoje - timedelta(days=hoje.weekday(), weeks=n) for n in range(SEMANAS_NO_GRAFICO - 1, -1, -1)]

        filtros = Filtros(request.GET)
        qs, _, _ = _escopo(request, filtros)
        if not filtros.validos:
            return JsonResponse({'erros': filtros.erros}, status=400)

        # 1. Gráfico Linha: abertos vs concluídos por semana (últimas 12 semanas) com TruncWeek
        abertos_semana = qs.filter(
            criado_em__date__gte=semanas[0]
        ).annotate(
            semana=TruncWeek('criado_em')
        ).values('semana').annotate(
            total=Count('id')
        ).order_by('semana')

        concluidos_semana = qs.filter(
            status=Chamado.STATUS_CONCLUIDO,
            concluido_em__date__gte=semanas[0]
        ).annotate(
            semana=TruncWeek('concluido_em')
        ).values('semana').annotate(
            total=Count('id')
        ).order_by('semana')

        mapa_abertos = _totais_por_semana(abertos_semana)
        mapa_concluidos = _totais_por_semana(concluidos_semana)

        # Semanas em ordem cronológica (não alfabética) e com zero quando não houve chamados.
        linha_dados = {
            'labels': [s.strftime('%d/%m') for s in semanas],
            'datas': [s.isoformat() for s in semanas],
            'abertos': [mapa_abertos.get(s, 0) for s in semanas],
            'concluidos': [mapa_concluidos.get(s, 0) for s in semanas],
        }

        # 2. Gráfico Barras: chamados ativos por plataforma
        # Usamos subquery/filter Q em annotate para não fazer loop
        plataformas_qs = Plataforma.objects.filter(ativa=True).annotate(
            total_ativos=Count('chamados', filter=Q(chamados__in=qs.exclude(status__in=Chamado.STATUS_FINAIS)))
        ).values('nome', 'cor', 'total_ativos')

        barras_plataformas = {
            'labels': [p['nome'] for p in plataformas_qs],
            'cores': [p['cor'] for p in plataformas_qs],
            'totais': [p['total_ativos'] for p in plataformas_qs],
        }

        # 3. Gráfico Barras: concluídos por dev no mês (apenas admin)
        barras_devs = {'labels': [], 'totais': []}
        if getattr(user, 'is_admin', False):
            devs_qs = Usuario.objects.filter(
                papel=Usuario.PAPEL_DEV,
                is_active=True
            ).annotate(
                concluidos_mes=Count(
                    'chamados_atribuidos',
                    filter=Q(
                        chamados_atribuidos__status=Chamado.STATUS_CONCLUIDO,
                        chamados_atribuidos__concluido_em__date__gte=inicio_mes
                    )
                )
            ).values('username', 'first_name', 'concluidos_mes')

            barras_devs = {
                'labels': [d['first_name'] or d['username'] for d in devs_qs],
                'totais': [d['concluidos_mes'] for d in devs_qs],
            }

        # 4. Gráfico Rosca: distribuição dos ativos por prioridade
        prioridades_qs = qs.exclude(
            status__in=Chamado.STATUS_FINAIS
        ).values('prioridade').annotate(
            total=Count('id')
        )
        mapa_prioridades = {item['prioridade']: item['total'] for item in prioridades_qs}
        rosca_prioridades = {
            'labels': ['Urgente', 'Alta', 'Média', 'Baixa'],
            'totais': [
                mapa_prioridades.get(Chamado.PRIORIDADE_URGENTE, 0),
                mapa_prioridades.get(Chamado.PRIORIDADE_ALTA, 0),
                mapa_prioridades.get(Chamado.PRIORIDADE_MEDIA, 0),
                mapa_prioridades.get(Chamado.PRIORIDADE_BAIXA, 0),
            ],
        }

        return JsonResponse({
            'linha': linha_dados,
            'plataformas': barras_plataformas,
            'devs': barras_devs,
            'prioridades': rosca_prioridades,
        })
