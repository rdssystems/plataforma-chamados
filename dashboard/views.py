from datetime import timedelta
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.http import JsonResponse
from django.contrib.auth import get_user_model

from chamados.models import Chamado, MudancaStatus
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


class DashboardIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        hoje = timezone.localdate()
        inicio_mes = hoje.replace(day=1)

        # Base do queryset
        if getattr(user, 'is_admin', False):
            qs = Chamado.objects.all()
            dev_id = self.request.GET.get('dev', '').strip()
            if dev_id:
                qs = qs.filter(responsavel_id=dev_id)
            context['dev_selecionado'] = dev_id
            context['devs'] = Usuario.objects.filter(is_active=True).order_by('first_name', 'username')
        else:
            qs = Chamado.objects.filter(Q(responsavel=user) | Q(criado_por=user))

        # 1. Agregação dos Cards (tudo em 1 query rápida no banco)
        cards_data = qs.aggregate(
            total_abertos=Count('id', filter=Q(status=Chamado.STATUS_ABERTO)),
            total_em_andamento=Count('id', filter=Q(status__in=[Chamado.STATUS_EM_ANDAMENTO, Chamado.STATUS_EM_REVISAO])),
            total_atrasados=Count('id', filter=Q(prazo__lt=hoje) & ~Q(status__in=Chamado.STATUS_FINAIS)),
            total_concluidos_mes=Count('id', filter=Q(status=Chamado.STATUS_CONCLUIDO, concluido_em__date__gte=inicio_mes, concluido_em__date__lte=hoje)),
            total_sem_responsavel=Count('id', filter=Q(responsavel__isnull=True) & ~Q(status__in=Chamado.STATUS_FINAIS)),
        )

        context['cards'] = cards_data

        # 2. Listas
        # Atrasados, ordenados pelo prazo mais antigo
        context['chamados_atrasados'] = qs.filter(
            prazo__lt=hoje
        ).exclude(
            status__in=Chamado.STATUS_FINAIS
        ).select_related('plataforma', 'responsavel').order_by('prazo')[:5]

        # Vencendo nos próximos 3 dias
        context['chamados_vencendo'] = qs.filter(
            prazo__gte=hoje,
            prazo__lte=hoje + timedelta(days=3)
        ).exclude(
            status__in=Chamado.STATUS_FINAIS
        ).select_related('plataforma', 'responsavel').order_by('prazo')[:5]

        # Últimas 10 atividades
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

        # Base do queryset
        if getattr(user, 'is_admin', False):
            qs = Chamado.objects.all()
            dev_id = request.GET.get('dev', '').strip()
            if dev_id:
                qs = qs.filter(responsavel_id=dev_id)
        else:
            qs = Chamado.objects.filter(Q(responsavel=user) | Q(criado_por=user))

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
