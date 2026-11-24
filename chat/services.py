from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Max, Value
from django.db.models.functions import Greatest
from django.utils import timezone

from .models import TOLERANCIA_PRESENCA, Conversa, Mensagem, Participante, Presenca
from .tempo_real import publicar_para_usuario

Usuario = get_user_model()

TAMANHO_MAXIMO_MENSAGEM = 4000


def nome_exibicao(usuario):
    return usuario.get_full_name() or usuario.username


def obter_ou_criar_conversa(usuario, outro):
    if usuario.pk == outro.pk:
        raise ValidationError('Não é possível iniciar uma conversa consigo mesmo.')
    chave = Conversa.chave_para(usuario, outro)
    conversa = Conversa.objects.filter(chave=chave).first()
    if conversa:
        return conversa
    try:
        with transaction.atomic():
            conversa = Conversa.objects.create(chave=chave)
            Participante.objects.bulk_create([
                Participante(conversa=conversa, usuario=usuario),
                Participante(conversa=conversa, usuario=outro),
            ])
    except IntegrityError:
        # Outra requisição criou a mesma conversa ao mesmo tempo.
        conversa = Conversa.objects.get(chave=chave)
    return conversa


def _nao_lidas(participacao):
    qs = Mensagem.objects.filter(conversa_id=participacao.conversa_id).exclude(autor_id=participacao.usuario_id)
    return qs.filter(id__gt=participacao.ultima_lida_id).count()


def conversas_do_usuario(usuario):
    """Conversas do usuário, com o outro participante, a última mensagem e as não lidas."""
    participacoes = (
        Participante.objects.filter(usuario=usuario)
        .select_related('conversa')
        .order_by('-conversa__atualizada_em')
    )
    conversas = []
    for p in participacoes:
        conversa = p.conversa
        conversa.nao_lidas = _nao_lidas(p)
        conversa.outro = (
            Usuario.objects.filter(participacoes_chat__conversa=conversa).exclude(pk=usuario.pk).first()
        )
        conversa.ultima_mensagem = conversa.mensagens.order_by('-criada_em', '-id').first()
        conversas.append(conversa)
    return conversas


def total_nao_lidas(usuario):
    return sum(_nao_lidas(p) for p in Participante.objects.filter(usuario=usuario))


def serializar_mensagem(mensagem):
    return {
        'id': mensagem.pk,
        'conversa_id': mensagem.conversa_id,
        'autor_id': mensagem.autor_id,
        'autor_nome': nome_exibicao(mensagem.autor),
        'texto': mensagem.texto,
        'criada_em': mensagem.criada_em.isoformat(),
    }


def enviar_mensagem(conversa, autor, texto):
    texto = (texto or '').strip()
    if not texto:
        raise ValidationError('A mensagem não pode ficar vazia.')
    if len(texto) > TAMANHO_MAXIMO_MENSAGEM:
        raise ValidationError(f'A mensagem pode ter no máximo {TAMANHO_MAXIMO_MENSAGEM} caracteres.')

    with transaction.atomic():
        mensagem = Mensagem.objects.create(conversa=conversa, autor=autor, texto=texto)
        Conversa.objects.filter(pk=conversa.pk).update(atualizada_em=mensagem.criada_em)
        Participante.objects.filter(conversa=conversa, usuario=autor).update(
            lida_ate=mensagem.criada_em, ultima_lida_id=Greatest(F('ultima_lida_id'), Value(mensagem.pk))
        )

        dados = serializar_mensagem(mensagem)
        for participante in conversa.participacoes.select_related('usuario'):
            publicar_para_usuario(participante.usuario_id, {
                'tipo': 'chat.mensagem',
                'mensagem': dados,
                'nao_lidas_total': total_nao_lidas(participante.usuario),
            })
    return mensagem


def marcar_conversa_lida(conversa, usuario):
    ultima = conversa.mensagens.aggregate(maior=Max('id'))['maior'] or 0
    # Greatest: duas abas marcando ao mesmo tempo nunca fazem o marcador andar para trás.
    Participante.objects.filter(conversa=conversa, usuario=usuario).update(
        lida_ate=timezone.now(), ultima_lida_id=Greatest(F('ultima_lida_id'), Value(ultima))
    )
    total = total_nao_lidas(usuario)
    publicar_para_usuario(usuario.pk, {'tipo': 'chat.lida', 'conversa_id': conversa.pk, 'nao_lidas_total': total})
    return total


# --- Presença -------------------------------------------------------------

def registrar_conexao(usuario_id):
    """Conta uma nova conexão. Retorna True se o usuário acabou de ficar online."""
    with transaction.atomic():
        presenca, _ = Presenca.objects.select_for_update().get_or_create(usuario_id=usuario_id)
        estava_online = presenca.esta_online
        if not estava_online:
            presenca.conexoes = 0  # descarta contagem antiga de conexões que caíram sem aviso
        presenca.conexoes += 1
        presenca.ultimo_sinal = timezone.now()
        presenca.save()
    return not estava_online


def registrar_desconexao(usuario_id):
    """Desconta uma conexão. Retorna True se o usuário ficou offline."""
    with transaction.atomic():
        presenca = Presenca.objects.select_for_update().filter(usuario_id=usuario_id).first()
        if presenca is None:
            return False
        presenca.conexoes = max(0, presenca.conexoes - 1)
        presenca.save(update_fields=['conexoes'])
        return presenca.conexoes == 0


def registrar_sinal(usuario_id):
    Presenca.objects.filter(usuario_id=usuario_id).update(ultimo_sinal=timezone.now())


def ids_online():
    limite = timezone.now() - TOLERANCIA_PRESENCA
    return set(
        Presenca.objects.filter(conexoes__gt=0, ultimo_sinal__gte=limite).values_list('usuario_id', flat=True)
    )
