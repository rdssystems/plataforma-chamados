from datetime import date, timedelta
import io
from django.utils import timezone
from django.db.models import Count, Q, Avg, F
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from chamados.models import Chamado
from plataformas.models import Plataforma

Usuario = get_user_model()


def obter_intervalo_datas(periodo_atalho=None, data_inicio=None, data_fim=None):
    """
    Retorna (data_inicio, data_fim) a partir do atalho de período ou datas livres.
    Padrão: 'este_mes'.
    """
    hoje = timezone.localdate()

    if data_inicio and data_fim:
        if isinstance(data_inicio, str):
            data_inicio = date.fromisoformat(data_inicio)
        if isinstance(data_fim, str):
            data_fim = date.fromisoformat(data_fim)
        return data_inicio, data_fim

    if periodo_atalho == 'esta_semana':
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
        return inicio, fim

    elif periodo_atalho == 'semana_passada':
        segunda_passada = hoje - timedelta(days=hoje.weekday() + 7)
        domingo_passado = segunda_passada + timedelta(days=6)
        return segunda_passada, domingo_passado

    elif periodo_atalho == 'mes_passado':
        primeiro_deste_mes = hoje.replace(day=1)
        ultimo_mes_passado = primeiro_deste_mes - timedelta(days=1)
        primeiro_mes_passado = ultimo_mes_passado.replace(day=1)
        return primeiro_mes_passado, ultimo_mes_passado

    # Default: este_mes
    primeiro_dia = hoje.replace(day=1)
    if hoje.month == 12:
        ultimo_dia = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        ultimo_dia = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
    return primeiro_dia, ultimo_dia


def calcular_metricas_relatorio(data_inicio, data_fim, dev_id=None, plataforma_id=None, tipo=None, prioridade=None):
    """
    Serviço centralizado que calcula todas as métricas, quebras e lista detalhada do período.
    Usado pela tela e pelas exportações em PDF e Excel.
    """
    qs_base = Chamado.objects.all()

    if dev_id:
        qs_base = qs_base.filter(responsavel_id=dev_id)
    if plataforma_id:
        qs_base = qs_base.filter(plataforma_id=plataforma_id)
    if tipo:
        qs_base = qs_base.filter(tipo=tipo)
    if prioridade:
        qs_base = qs_base.filter(prioridade=prioridade)

    # 1. Chamados abertos no período
    abertos_qs = qs_base.filter(criado_em__date__gte=data_inicio, criado_em__date__lte=data_fim)
    total_abertos = abertos_qs.count()

    # 2. Chamados concluídos no período
    concluidos_qs = qs_base.filter(
        status=Chamado.STATUS_CONCLUIDO,
        concluido_em__date__gte=data_inicio,
        concluido_em__date__lte=data_fim
    ).select_related('plataforma', 'responsavel', 'criado_por')
    total_concluidos = concluidos_qs.count()

    # 3. Tempo médio de resolução dos concluídos
    # Calcula a média em timedelta
    concluidos_com_tempo = [c for c in concluidos_qs if c.concluido_em and c.criado_em]
    if concluidos_com_tempo:
        segundos_totais = sum((c.concluido_em - c.criado_em).total_seconds() for c in concluidos_com_tempo)
        media_segundos = segundos_totais / len(concluidos_com_tempo)
        tempo_medio = timedelta(seconds=int(media_segundos))
    else:
        tempo_medio = None

    # 4. Entregues no prazo (% dos concluídos com concluido_em.date() <= prazo, apenas com prazo)
    concluidos_com_prazo = [c for c in concluidos_qs if c.prazo is not None and c.concluido_em is not None]
    no_prazo_count = sum(1 for c in concluidos_com_prazo if c.concluido_em.date() <= c.prazo)
    if concluidos_com_prazo:
        taxa_no_prazo = round((no_prazo_count / len(concluidos_com_prazo)) * 100, 1)
    else:
        taxa_no_prazo = 0.0  # Sem base de cálculo: a tela mostra "—" usando prazo_denominador.

    # 5. Atrasados no fim do período (prazo < fim do período e não concluídos até ele)
    atrasados_fim_periodo = qs_base.filter(
        prazo__lt=data_fim,
        criado_em__date__lte=data_fim
    ).filter(
        Q(concluido_em__isnull=True) | Q(concluido_em__date__gt=data_fim)
    ).exclude(
        status=Chamado.STATUS_CANCELADO
    ).count()

    # 6. Backlog (não finais na data de fim do período)
    backlog = qs_base.filter(
        criado_em__date__lte=data_fim
    ).filter(
        Q(concluido_em__isnull=True) | Q(concluido_em__date__gt=data_fim)
    ).exclude(
        status=Chamado.STATUS_CANCELADO
    ).count()

    # Quebra por Desenvolvedor (concluídos, tempo médio, % no prazo)
    quebra_devs = []
    devs = Usuario.objects.filter(is_active=True).order_by('first_name', 'username')
    if dev_id:
        devs = devs.filter(id=dev_id)

    for d in devs:
        c_dev = [c for c in concluidos_qs if c.responsavel_id == d.id]
        qtd_concluidos = len(c_dev)

        # Tempo médio
        c_dev_tempo = [c for c in c_dev if c.concluido_em and c.criado_em]
        if c_dev_tempo:
            seg_dev = sum((c.concluido_em - c.criado_em).total_seconds() for c in c_dev_tempo)
            t_medio_dev = timedelta(seconds=int(seg_dev / len(c_dev_tempo)))
        else:
            t_medio_dev = None

        # % no prazo
        c_dev_prazo = [c for c in c_dev if c.prazo and c.concluido_em]
        if c_dev_prazo:
            no_p = sum(1 for c in c_dev_prazo if c.concluido_em.date() <= c.prazo)
            taxa_p = round((no_p / len(c_dev_prazo)) * 100, 1)
        else:
            taxa_p = 0.0

        quebra_devs.append({
            'dev': d,
            'concluidos': qtd_concluidos,
            'tempo_medio': t_medio_dev,
            'taxa_no_prazo': taxa_p
        })

    # Quebra por Plataforma (abertos, concluídos, ativos)
    quebra_plataformas = []
    plataformas = Plataforma.objects.filter(ativa=True).order_by('nome')
    if plataforma_id:
        plataformas = plataformas.filter(id=plataforma_id)

    for p in plataformas:
        abertos_p = abertos_qs.filter(plataforma_id=p.id).count()
        concluidos_p = concluidos_qs.filter(plataforma_id=p.id).count()
        ativos_p = qs_base.filter(plataforma_id=p.id).exclude(status__in=Chamado.STATUS_FINAIS).count()
        quebra_plataformas.append({
            'plataforma': p,
            'abertos': abertos_p,
            'concluidos': concluidos_p,
            'ativos': ativos_p,
        })

    # Distribuição por Tipo e Prioridade
    dist_tipo = qs_base.filter(criado_em__date__gte=data_inicio, criado_em__date__lte=data_fim).values('tipo').annotate(total=Count('id'))
    mapa_tipo = dict(Chamado.TIPO_CHOICES)
    quebra_tipos = [{'label': mapa_tipo.get(item['tipo'], item['tipo']), 'total': item['total']} for item in dist_tipo]

    dist_prioridade = qs_base.filter(criado_em__date__gte=data_inicio, criado_em__date__lte=data_fim).values('prioridade').annotate(total=Count('id'))
    mapa_prioridade = dict(Chamado.PRIORIDADE_CHOICES)
    quebra_prioridades = [{'label': mapa_prioridade.get(item['prioridade'], item['prioridade']), 'total': item['total']} for item in dist_prioridade]

    return {
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_abertos': total_abertos,
        'total_concluidos': total_concluidos,
        'tempo_medio': tempo_medio,
        'taxa_no_prazo': taxa_no_prazo,
        'prazo_numerador': no_prazo_count,
        'prazo_denominador': len(concluidos_com_prazo),
        'atrasados_fim_periodo': atrasados_fim_periodo,
        'backlog': backlog,
        'quebra_devs': quebra_devs,
        'quebra_plataformas': quebra_plataformas,
        'quebra_tipos': quebra_tipos,
        'quebra_prioridades': quebra_prioridades,
        'lista_detalhada': concluidos_qs.order_by('-concluido_em'),
    }


def gerar_relatorio_excel(dados):
    wb = openpyxl.Workbook()

    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')
    border_thin = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # Aba 1: Resumo Executivo
    ws1 = wb.active
    ws1.title = "Resumo"
    ws1.append(["Relatório de Chamados — Resumo do Período"])
    ws1.append([f"Período: {dados['data_inicio'].strftime('%d/%m/%Y')} a {dados['data_fim'].strftime('%d/%m/%Y')}"])
    ws1.append([])

    ws1.append(["Indicador", "Valor"])
    ws1.append(["Chamados Abertos", dados['total_abertos']])
    ws1.append(["Chamados Concluídos", dados['total_concluidos']])
    ws1.append(["Tempo Médio de Resolução", str(dados['tempo_medio']) if dados['tempo_medio'] else "—"])
    ws1.append(["Entregues no Prazo (%)", f"{dados['taxa_no_prazo']}%"])
    ws1.append(["Atrasados no Fim do Período", dados['atrasados_fim_periodo']])
    ws1.append(["Backlog Ativo", dados['backlog']])

    for cell in ws1[4]:
        cell.font = header_font
        cell.fill = header_fill

    # Aba 2: Por Desenvolvedor
    ws2 = wb.create_sheet(title="Por Desenvolvedor")
    ws2.append(["Desenvolvedor", "Chamados Concluídos", "Tempo Médio", "% Entregues no Prazo"])
    for cell in ws2[1]:
        cell.font = header_font
        cell.fill = header_fill

    for d in dados['quebra_devs']:
        ws2.append([
            d['dev'].get_full_name() or d['dev'].username,
            d['concluidos'],
            str(d['tempo_medio']) if d['tempo_medio'] else "—",
            f"{d['taxa_no_prazo']}%"
        ])

    # Aba 3: Por Plataforma
    ws3 = wb.create_sheet(title="Por Plataforma")
    ws3.append(["Plataforma", "Abertos no Período", "Concluídos no Período", "Ativos Atuais"])
    for cell in ws3[1]:
        cell.font = header_font
        cell.fill = header_fill

    for p in dados['quebra_plataformas']:
        ws3.append([
            p['plataforma'].nome,
            p['abertos'],
            p['concluidos'],
            p['ativos']
        ])

    # Aba 4: Lista Detalhada
    ws4 = wb.create_sheet(title="Chamados Concluídos")
    ws4.append(["Código", "Título", "Plataforma", "Responsável", "Criado em", "Concluído em", "Prazo", "Tempo de Resolução"])
    for cell in ws4[1]:
        cell.font = header_font
        cell.fill = header_fill

    for c in dados['lista_detalhada']:
        ws4.append([
            c.codigo,
            c.titulo,
            c.plataforma.nome,
            c.responsavel.username if c.responsavel else "Sem dev",
            c.criado_em.strftime('%d/%m/%Y %H:%M'),
            c.concluido_em.strftime('%d/%m/%Y %H:%M') if c.concluido_em else "—",
            c.prazo.strftime('%d/%m/%Y') if c.prazo else "Sem prazo",
            str(c.tempo_resolucao) if c.tempo_resolucao else "—"
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def gerar_relatorio_pdf(dados, request):
    html_content = render_to_string('relatorios/pdf.html', {'dados': dados}, request=request)

    # 1. Tenta WeasyPrint caso as dependências do sistema estejam instaladas
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except Exception:
        pass

    # 2. Fallback robusto nativo em Python com xhtml2pdf
    from xhtml2pdf import pisa
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    if not pisa_status.err:
        return pdf_buffer.getvalue()

    raise RuntimeError("Falha ao gerar o documento PDF.")
