from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from .models import Chamado, MudancaStatus


def mudar_status(chamado: Chamado, novo_status: str, usuario, comentario: str = None) -> Chamado:
    """
    Executa a transição de status de um Chamado aplicando todas as regras de negócio
    especificadas na matriz de permissões e transições.
    """
    de_status = chamado.status
    comentario = (comentario or '').strip()

    if de_status == novo_status:
        return chamado

    is_admin = getattr(usuario, 'is_admin', False)
    is_responsavel = (chamado.responsavel_id is not None) and (chamado.responsavel_id == usuario.id)

    # 1. De Aberto -> Em andamento
    if de_status == Chamado.STATUS_ABERTO and novo_status == Chamado.STATUS_EM_ANDAMENTO:
        if not (is_admin or is_responsavel):
            raise ValidationError("Apenas o responsável ou um administrador podem colocar o chamado em andamento.")
        if not chamado.responsavel:
            raise ValidationError("O chamado precisa ter um responsável atribuído para entrar em andamento.")

    # 2. De Em andamento -> Em revisão
    elif de_status == Chamado.STATUS_EM_ANDAMENTO and novo_status == Chamado.STATUS_EM_REVISAO:
        if not (is_admin or is_responsavel):
            raise ValidationError("Apenas o responsável ou um administrador podem enviar o chamado para revisão.")

    # 3. De Em revisão -> Concluído
    elif de_status == Chamado.STATUS_EM_REVISAO and novo_status == Chamado.STATUS_CONCLUIDO:
        if not is_admin:
            raise ValidationError("Apenas administradores podem aprovar e concluir um chamado.")

    # 4. De Em revisão -> Em andamento (devolução)
    elif de_status == Chamado.STATUS_EM_REVISAO and novo_status == Chamado.STATUS_EM_ANDAMENTO:
        if not is_admin:
            raise ValidationError("Apenas administradores podem devolver um chamado em revisão para andamento.")
        if not comentario:
            raise ValidationError("É obrigatório informar um comentário com o motivo ao devolver o chamado para andamento.")

    # 5. De Concluído -> Em andamento (reabertura)
    elif de_status == Chamado.STATUS_CONCLUIDO and novo_status == Chamado.STATUS_EM_ANDAMENTO:
        if not is_admin:
            raise ValidationError("Apenas administradores podem reabrir um chamado concluído.")
        if not comentario:
            raise ValidationError("É obrigatório informar um comentário com o motivo ao reabrir o chamado.")

    # 6. De Aberto, Em andamento ou Em revisão -> Cancelado
    elif de_status in [Chamado.STATUS_ABERTO, Chamado.STATUS_EM_ANDAMENTO, Chamado.STATUS_EM_REVISAO] and novo_status == Chamado.STATUS_CANCELADO:
        if not is_admin:
            raise ValidationError("Apenas administradores podem cancelar um chamado.")
        if not comentario:
            raise ValidationError("É obrigatório informar um comentário com o motivo ao cancelar o chamado.")

    else:
        status_dict = dict(Chamado.STATUS_CHOICES)
        de_str = status_dict.get(de_status, de_status)
        para_str = status_dict.get(novo_status, novo_status)
        raise ValidationError(f"Transição de '{de_str}' para '{para_str}' não é permitida pelas regras de negócio.")

    # Executa a transição atomicamente
    with transaction.atomic():
        # Regras de preenchimento de datas
        if novo_status == Chamado.STATUS_EM_ANDAMENTO:
            if not chamado.iniciado_em:
                chamado.iniciado_em = timezone.now()
            if de_status == Chamado.STATUS_CONCLUIDO:
                chamado.concluido_em = None
        elif novo_status == Chamado.STATUS_CONCLUIDO:
            chamado.concluido_em = timezone.now()

        chamado.status = novo_status
        chamado.save(update_fields=['status', 'iniciado_em', 'concluido_em', 'atualizado_em'])

        # Registro na tabela MudancaStatus
        MudancaStatus.objects.create(
            chamado=chamado,
            de_status=de_status,
            para_status=novo_status,
            alterado_por=usuario,
            comentario_motivo=comentario or None
        )

        # Se houver comentário no motivo e houver modelo Comentario, pode opcionalmente gravar também
        if comentario:
            try:
                from chamados.models import Comentario
                Comentario.objects.create(
                    chamado=chamado,
                    autor=usuario,
                    texto=f"[Mudança de Status para {chamado.get_status_display()}]: {comentario}"
                )
            except Exception:
                pass

        # Dispara notificação interna se houver app de notificações
        try:
            from notificacoes.services import criar_notificacao_mudanca_status
            criar_notificacao_mudanca_status(chamado, de_status, novo_status, usuario)
        except Exception:
            pass

    return chamado
