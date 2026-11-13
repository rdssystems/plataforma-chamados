def chat_context(request):
    if not request.user.is_authenticated:
        return {'chat_nao_lidas_count': 0}
    from .services import total_nao_lidas

    return {'chat_nao_lidas_count': total_nao_lidas(request.user)}
