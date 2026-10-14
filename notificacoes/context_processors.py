def notificacoes_context(request):
    if not request.user.is_authenticated:
        return {'notificacoes_nao_lidas_count': 0, 'notificacoes_recentes': []}
    
    # Será conectado ao modelo Notificacao na etapa 3
    try:
        from notificacoes.models import Notificacao
        qs = Notificacao.objects.filter(destinatario=request.user)
        return {
            'notificacoes_nao_lidas_count': qs.filter(lida=False).count(),
            'notificacoes_recentes': qs.order_by('-criada_em')[:5]
        }
    except Exception:
        return {'notificacoes_nao_lidas_count': 0, 'notificacoes_recentes': []}
