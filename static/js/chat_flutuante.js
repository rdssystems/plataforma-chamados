/*
 * Chat flutuante no canto inferior direito: abre, minimiza e permite responder
 * sem sair da página. O estado (aberto/minimizado, aba e conversa) é lembrado
 * entre páginas no navegador da pessoa.
 *
 * Integra com:
 *  - tempo_real.js: atualiza a lista de conversas, os usuários online e os contadores;
 *    avisa quando chega mensagem (som, título piscando, notificação do sistema).
 *  - chat_conversa.js: a conversa aberta.
 */
(function () {
    'use strict';

    var raiz = document.getElementById('chat-flutuante');
    if (!raiz || !window.ChatConversa) return;

    var usuarioId = Number(raiz.dataset.usuarioId);
    var urlConversas = raiz.dataset.urlConversas;
    var urlPagina = raiz.dataset.urlPagina;
    var csrf = raiz.querySelector('[data-chat-csrf]').value;
    var janela = document.getElementById('chat-janela');
    var lancador = document.getElementById('chat-lancador');
    var telaLista = raiz.querySelector('[data-chat-tela="lista"]');
    var telaConversa = raiz.querySelector('[data-chat-tela="conversa"]');
    var titulo = document.getElementById('chat-janela-titulo');
    var statusEl = raiz.querySelector('[data-chat-status]');
    var voltar = raiz.querySelector('[data-chat-voltar]');
    var telaCheia = raiz.querySelector('[data-chat-tela-cheia]');
    var listaConversas = raiz.querySelector('[data-lista-conversas]');
    var modelo = document.getElementById('chat-flutuante-conversa');

    var CHAVE = 'chat.flutuante';
    var estado = ler();
    var conversa = null;       // instância de ChatConversa
    var abrindo = 0;           // descarta respostas de aberturas antigas

    function ler() {
        try {
            var e = JSON.parse(localStorage.getItem(CHAVE) || '{}');
            return { aberto: !!e.aberto, conversa: e.conversa || null, aba: e.aba === 'online' ? 'online' : 'conversas' };
        } catch (_) {
            return { aberto: false, conversa: null, aba: 'conversas' };
        }
    }
    function salvar() {
        try { localStorage.setItem(CHAVE, JSON.stringify(estado)); } catch (_) {}
    }

    function aberto() { return !janela.hidden; }

    function marcarVisivel() {
        // tempo_real.js não mostra aviso de uma conversa que já está à vista.
        if (conversa && aberto()) window.chatConversaAberta = conversa.conversaId;
        else if (window.chatConversaAberta === (conversa && conversa.conversaId)) window.chatConversaAberta = null;
    }

    // --- Abrir e minimizar ------------------------------------------------------

    function abrir(focar) {
        janela.hidden = false;
        raiz.classList.add('aberto');
        lancador.setAttribute('aria-expanded', 'true');
        lancador.classList.remove('alerta');
        estado.aberto = true;
        salvar();
        if (estado.conversa && (!conversa || conversa.conversaId !== estado.conversa)) {
            abrirConversa(estado.conversa, focar);
        } else if (conversa) {
            marcarVisivel();
            conversa.marcarLida();
            conversa.rolarParaFim();
            if (focar) conversa.focar();
        } else {
            carregarConversas();
            if (focar) raiz.querySelector('[data-chat-aba][aria-selected="true"]').focus();
        }
    }

    function minimizar(devolverFoco) {
        janela.hidden = true;
        raiz.classList.remove('aberto');
        lancador.setAttribute('aria-expanded', 'false');
        estado.aberto = false;
        salvar();
        marcarVisivel();
        if (devolverFoco) lancador.focus();
    }

    // --- Lista ------------------------------------------------------------------

    function mostrarAba(nome) {
        estado.aba = nome;
        salvar();
        raiz.querySelectorAll('[data-chat-aba]').forEach(function (b) {
            b.setAttribute('aria-selected', String(b.dataset.chatAba === nome));
        });
        raiz.querySelectorAll('[data-chat-painel]').forEach(function (p) {
            p.classList.toggle('d-none', p.dataset.chatPainel !== nome);
        });
    }

    function carregarConversas() {
        fetch(urlConversas + '?ativa=', { credentials: 'same-origin' })
            .then(function (r) {
                if (!r.ok || r.redirected) throw new Error();
                return r.text();
            })
            .then(function (html) { listaConversas.innerHTML = html; })
            .catch(function () {});
    }

    function mostrarLista() {
        if (conversa) conversa.destruir();
        if (window.chatConversaAberta === (conversa && conversa.conversaId)) window.chatConversaAberta = null;
        conversa = null;
        estado.conversa = null;
        salvar();
        telaConversa.replaceChildren();
        telaConversa.classList.add('d-none');
        telaLista.classList.remove('d-none');
        voltar.hidden = true;
        statusEl.hidden = true;
        titulo.textContent = 'Chat';
        telaCheia.href = urlPagina;
        carregarConversas();
    }

    // --- Conversa ---------------------------------------------------------------

    function abrirConversa(id, focar) {
        var pedido = ++abrindo;
        fetch('/chat/' + encodeURIComponent(id) + '/resumo/', { credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (r) {
                if (!r.ok || r.redirected) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function (d) {
                if (pedido !== abrindo) return;
                if (conversa) conversa.destruir();

                telaConversa.replaceChildren(modelo.content.cloneNode(true));
                var form = telaConversa.querySelector('[data-form]');
                var campo = form.querySelector('textarea');
                var idCampo = 'chat-flutuante-campo-' + d.id;
                campo.id = idCampo;
                var rotulo = form.querySelector('[data-rotulo-campo]');
                rotulo.htmlFor = idCampo;
                rotulo.textContent = 'Mensagem para ' + d.outro.nome;
                form.action = d.urls.enviar;
                var token = document.createElement('input');
                token.type = 'hidden';
                token.name = 'csrfmiddlewaretoken';
                token.value = csrf;
                form.appendChild(token);
                if (!d.pode_enviar) {
                    form.classList.add('d-none');
                    telaConversa.querySelector('[data-desativado]').classList.remove('d-none');
                }

                titulo.textContent = d.outro.nome;
                statusEl.hidden = false;
                statusEl.dataset.desativado = String(!d.outro.ativo);
                statusEl.textContent = !d.outro.ativo ? 'Usuário desativado' : (d.outro.online ? 'Online' : 'Offline');
                statusEl.classList.toggle('text-success', d.outro.ativo && d.outro.online);
                voltar.hidden = false;
                telaCheia.href = d.urls.pagina;
                telaLista.classList.add('d-none');
                telaConversa.classList.remove('d-none');
                estado.conversa = d.id;
                salvar();

                conversa = window.ChatConversa({
                    usuarioId: usuarioId,
                    conversaId: d.id,
                    outroId: d.outro.id,
                    urlMensagens: d.urls.mensagens,
                    urlLida: d.urls.lida,
                    csrf: csrf,
                    lista: telaConversa.querySelector('[data-mensagens]'),
                    blocoAnteriores: telaConversa.querySelector('[data-anteriores]'),
                    form: d.pode_enviar ? form : null,
                    erro: form.querySelector('[data-erro]'),
                    status: statusEl,
                    mensagens: d.mensagens,
                    temMais: d.tem_mais,
                    estaVisivel: function () { return aberto() && !document.hidden; },
                });
                marcarVisivel();
                if (focar && aberto()) conversa.focar();
            })
            .catch(function () {
                // Conversa inexistente ou sem acesso: volta para a lista.
                if (pedido === abrindo) mostrarLista();
            });
    }

    // --- Eventos ----------------------------------------------------------------

    lancador.addEventListener('click', function () {
        if (aberto()) minimizar(true);
        else abrir(true);
    });
    raiz.querySelector('[data-chat-minimizar]').addEventListener('click', function () { minimizar(true); });
    voltar.addEventListener('click', function () {
        mostrarLista();
        raiz.querySelector('[data-chat-aba][aria-selected="true"]').focus();
    });
    raiz.querySelectorAll('[data-chat-aba]').forEach(function (b) {
        b.addEventListener('click', function () { mostrarAba(b.dataset.chatAba); });
    });
    janela.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !e.target.closest('.dropdown-menu')) minimizar(true);
    });

    // Conversa da lista abre aqui mesmo (Ctrl/Cmd+clique continua abrindo a página do chat).
    listaConversas.addEventListener('click', function (e) {
        var link = e.target.closest('a[data-conversa-id]');
        if (!link || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button !== 0) return;
        e.preventDefault();
        abrirConversa(Number(link.dataset.conversaId), true);
    });

    // "Conversar" (na aba Online daqui ou no menu Online da barra) abre a conversa aqui.
    document.addEventListener('submit', function (e) {
        var form = e.target.closest('form[data-iniciar-conversa]');
        if (!form) return;
        e.preventDefault();
        var menu = form.closest('.dropdown-menu');
        if (menu && window.bootstrap) {
            var gatilho = menu.parentElement.querySelector('[data-bs-toggle="dropdown"]');
            if (gatilho) bootstrap.Dropdown.getOrCreateInstance(gatilho).hide();
        }
        fetch(form.action, { method: 'POST', body: new FormData(form), credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (r) { return r.json().then(function (c) { if (!r.ok) throw new Error(c.erro); return c; }); })
            .then(function (c) {
                estado.conversa = c.conversa_id;
                if (aberto()) abrirConversa(c.conversa_id, true);
                else abrir(true);
            })
            .catch(function () { form.submit(); });
    });

    // Aviso de nova mensagem (toast) e notificação do sistema abrem a conversa aqui.
    document.addEventListener('click', function (e) {
        var aviso = e.target.closest('.aviso[data-conversa-id]');
        if (!aviso || e.ctrlKey || e.metaKey) return;
        e.preventDefault();
        aviso.remove();
        estado.conversa = Number(aviso.dataset.conversaId);
        if (aberto()) abrirConversa(estado.conversa, true);
        else abrir(true);
    });
    document.addEventListener('chat-abrir-conversa', function (e) {
        estado.conversa = e.detail.conversaId;
        if (aberto()) abrirConversa(estado.conversa, true);
        else abrir(true);
    });

    // Mensagem nova fora da conversa à vista: o botão pulsa até a pessoa abrir o chat.
    document.addEventListener('tempo-real', function (e) {
        var d = e.detail;
        if (d.tipo !== 'chat.mensagem' || d.mensagem.autor_id === usuarioId) return;
        var visivel = aberto() && conversa && conversa.conversaId === d.mensagem.conversa_id;
        if (!visivel && !aberto()) {
            lancador.classList.remove('alerta');
            void lancador.offsetWidth;  // reinicia a animação
            lancador.classList.add('alerta');
        }
    });

    // --- Estado inicial (vindo da página anterior) --------------------------------
    mostrarAba(estado.aba);
    if (estado.aberto) abrir(false);
})();
