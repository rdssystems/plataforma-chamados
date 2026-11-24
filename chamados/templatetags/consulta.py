from django import template

register = template.Library()


@register.filter
def obter(dicionario, chave):
    """{{ filtros|obter:nome }}: valor de um dicionário por chave variável (vazio se ausente)."""
    if not dicionario:
        return ''
    valor = dicionario.get(chave, '')
    return '' if valor is None else valor


@register.filter
def duracao(valor):
    """timedelta em português, sem segundos: '6 d 13 h', '2 h 15 min', 'menos de 1 min'."""
    from datetime import timedelta
    if not isinstance(valor, timedelta):
        return valor if valor not in (None, '') else ''
    total_min = int(valor.total_seconds()) // 60
    dias, resto = divmod(total_min, 60 * 24)
    horas, minutos = divmod(resto, 60)
    partes = []
    if dias:
        partes.append(f'{dias} d')
    if horas:
        partes.append(f'{horas} h')
    if minutos and not dias:
        partes.append(f'{minutos} min')
    return ' '.join(partes) or 'menos de 1 min'
