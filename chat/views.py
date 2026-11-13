from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from . import services
from .models import Conversa

Usuario = get_user_model()

MENSAGENS_POR_PAGINA = 50


def _conversa_do_usuario(request, pk):
    return get_object_or_404(Conversa, pk=pk, participacoes__usuario=request.user)


def _pagina_mensagens(conversa, antes_de=None):
    qs = conversa.mensagens.select_related('autor').order_by('-criada_em', '-id')
    if antes_de:
        qs = qs.filter(id__lt=antes_de)
    pagina = list(qs[:MENSAGENS_POR_PAGINA + 1])
    tem_mais = len(pagina) > MENSAGENS_POR_PAGINA
    pagina = list(reversed(pagina[:MENSAGENS_POR_PAGINA]))
    return [services.serializar_mensagem(m) for m in pagina], tem_mais


def _outro_participante(conversa, usuario):
    return Usuario.objects.filter(participacoes_chat__conversa=conversa).exclude(pk=usuario.pk).first()


@login_required
@require_GET
def chat_index(request, pk=None):
    conversa = outro = None
    mensagens_iniciais, tem_mais = [], False
    if pk is not None:
        conversa = _conversa_do_usuario(request, pk)
        outro = _outro_participante(conversa, request.user)
        mensagens_iniciais, tem_mais = _pagina_mensagens(conversa)
        services.marcar_conversa_lida(conversa, request.user)

    return render(request, 'chat/index.html', {
        'conversa': conversa,
        'outro': outro,
        'outro_online': outro is not None and outro.pk in services.ids_online(),
        'conversas': services.conversas_do_usuario(request.user),
        'chat_dados': {
            'conversaId': conversa.pk if conversa else None,
            'usuarioId': request.user.pk,
            'outroId': outro.pk if outro else None,
            'mensagens': mensagens_iniciais,
            'temMais': tem_mais,
            'urlMensagens': reverse('chat:mensagens', args=[conversa.pk]) if conversa else None,
            'urlLida': reverse('chat:marcar_lida', args=[conversa.pk]) if conversa else None,
        },
        'pode_enviar': bool(outro and outro.is_active),
    })


@login_required
@require_POST
def iniciar_conversa(request, usuario_id):
    outro = get_object_or_404(Usuario, pk=usuario_id, is_active=True)
    try:
        conversa = services.obter_ou_criar_conversa(request.user, outro)
    except ValidationError as erro:
        messages.error(request, erro.messages[0])
        return redirect('chat:index')
    return redirect('chat:conversa', pk=conversa.pk)


@login_required
@require_POST
def enviar_mensagem(request, pk):
    conversa = _conversa_do_usuario(request, pk)
    outro = _outro_participante(conversa, request.user)
    if outro is None or not outro.is_active:
        return JsonResponse({'erro': 'Este usuário está desativado e não recebe novas mensagens.'}, status=400)
    try:
        mensagem = services.enviar_mensagem(conversa, request.user, request.POST.get('texto', ''))
    except ValidationError as erro:
        return JsonResponse({'erro': erro.messages[0]}, status=400)
    return JsonResponse({'mensagem': services.serializar_mensagem(mensagem)}, status=201)


@login_required
@require_GET
def listar_mensagens(request, pk):
    """?antes=<id> pagina o histórico para trás; ?depois=<id> recupera o que chegou após uma reconexão."""
    conversa = _conversa_do_usuario(request, pk)
    antes_de, depois_de = request.GET.get('antes'), request.GET.get('depois')
    for valor in (antes_de, depois_de):
        if valor is not None and not valor.isdigit():
            raise Http404
    if depois_de:
        qs = conversa.mensagens.select_related('autor').filter(id__gt=int(depois_de)).order_by('criada_em', 'id')
        pagina = list(qs[:MENSAGENS_POR_PAGINA * 4])
        return JsonResponse({'mensagens': [services.serializar_mensagem(m) for m in pagina], 'tem_mais': False})
    mensagens, tem_mais = _pagina_mensagens(conversa, int(antes_de) if antes_de else None)
    return JsonResponse({'mensagens': mensagens, 'tem_mais': tem_mais})


@login_required
@require_POST
def marcar_lida(request, pk):
    conversa = _conversa_do_usuario(request, pk)
    total = services.marcar_conversa_lida(conversa, request.user)
    return JsonResponse({'nao_lidas_total': total})


@login_required
@require_GET
def lista_conversas(request):
    ativa = request.GET.get('ativa', '')
    return render(request, 'chat/partials/conversas.html', {
        'conversas': services.conversas_do_usuario(request.user),
        'conversa_ativa_id': int(ativa) if ativa.isdigit() else None,
    })


@login_required
@require_GET
def lista_usuarios(request):
    online = services.ids_online()
    usuarios = list(Usuario.objects.filter(is_active=True).exclude(pk=request.user.pk))
    for u in usuarios:
        u.online = u.pk in online
    usuarios.sort(key=lambda u: (not u.online, services.nome_exibicao(u).lower()))
    return render(request, 'chat/partials/usuarios.html', {
        'usuarios': usuarios,
        'total_online': sum(1 for u in usuarios if u.online),
    })
