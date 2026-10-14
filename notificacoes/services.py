from .models import Notificacao


def notificar_atribuicao(chamado, alterado_por):
    if chamado.responsavel and chamado.responsavel != alterado_por:
        Notificacao.objects.create(
            destinatario=chamado.responsavel,
            chamado=chamado,
            mensagem=f"Você foi atribuído como responsável pelo chamado {chamado.codigo}."
        )


def notificar_comentario(chamado, comentario, autor):
    destinatarios = set()
    if chamado.responsavel and chamado.responsavel != autor:
        destinatarios.add(chamado.responsavel)
    if chamado.criado_por and chamado.criado_por != autor:
        destinatarios.add(chamado.criado_por)

    autor_nome = autor.get_full_name() or autor.username
    for dest in destinatarios:
        Notificacao.objects.create(
            destinatario=dest,
            chamado=chamado,
            mensagem=f"Novo comentário em {chamado.codigo} por {autor_nome}."
        )


def criar_notificacao_mudanca_status(chamado, de_status, novo_status, alterado_por):
    destinatarios = set()
    if chamado.responsavel and chamado.responsavel != alterado_por:
        destinatarios.add(chamado.responsavel)
    if chamado.criado_por and chamado.criado_por != alterado_por:
        destinatarios.add(chamado.criado_por)

    status_str = chamado.get_status_display()
    for dest in destinatarios:
        Notificacao.objects.create(
            destinatario=dest,
            chamado=chamado,
            mensagem=f"O chamado {chamado.codigo} teve seu status alterado para {status_str}."
        )
