/*
 * Conexão em tempo real (WebSocket) usada em todas as páginas autenticadas.
 * - mantém a presença do usuário (online/offline) com um "ping" periódico;
 * - atualiza os contadores de chat e notificações e mostra avisos (toasts);
 * - mantém atualizadas as listas de usuários online e de conversas;
 * - repassa cada evento recebido como `tempo-real` no `document` (usado por chat.js).
 */
(function () {
    'use strict';

    var script = document.currentScript;
    var cfg = {
        usuarioId: Number(script.dataset.usuarioId),
        usuariosUrl: script.dataset.usuariosUrl,
        conversasUrl: script.dataset.conversasUrl,
    };
    var FECHAR_NAO_AUTENTICADO = 4401;
    var INTERVALO_PING = 25000;
    var INTERVALO_LISTA_USUARIOS = 60000;

    var ws = null;
    var tentativas = 0;
    var pingTimer = null;

    function conectar() {
        var protocolo = location.protocol === 'https:' ? 'wss://' : 'ws://';
        ws = new WebSocket(protocolo + location.host + '/ws/app/');

        ws.onopen = function () {
            tentativas = 0;
            clearInterval(pingTimer);
            pingTimer = setInterval(function () { enviar({ tipo: 'ping' }); }, INTERVALO_PING);
            atualizarUsuarios();
            document.dispatchEvent(new CustomEvent('tempo-real-conectado'));
        };

        ws.onmessage = function (e) {
            var dados;
            try { dados = JSON.parse(e.data); } catch (_) { return; }
            tratar(dados);
            document.dispatchEvent(new CustomEvent('tempo-real', { detail: dados }));
        };

        ws.onclose = function (e) {
            clearInterval(pingTimer);
            if (e.code === FECHAR_NAO_AUTENTICADO) return;
            var espera = Math.min(30000, 1000 * Math.pow(2, tentativas++));
            setTimeout(conectar, espera);
        };
    }

    function enviar(obj) {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
    }

    function tratar(dados) {
        if (dados.tipo === 'chat.mensagem') {
            atualizarContador(document.getElementById('chat-badge'), dados.nao_lidas_total);
            var m = dados.mensagem;
            var conversaVisivel = window.chatConversaAberta === m.conversa_id && !document.hidden;
            if (m.autor_id !== cfg.usuarioId && !conversaVisivel) {
                mostrarAviso(m.autor_nome, m.texto, '/chat/' + m.conversa_id + '/');
            }
            atualizarConversas();
        } else if (dados.tipo === 'chat.lida') {
            atualizarContador(document.getElementById('chat-badge'), dados.nao_lidas_total);
            atualizarConversas();
        } else if (dados.tipo === 'notificacao') {
            atualizarContador(document.getElementById('notif-badge'), dados.nao_lidas);
            var ponto = document.getElementById('notif-dot');
            if (ponto) ponto.classList.toggle('hidden', !dados.nao_lidas);
            mostrarAviso('Notificação', dados.mensagem, dados.url);
        } else if (dados.tipo === 'presenca') {
            atualizarUsuarios();
        }
    }

    function atualizarContador(el, valor) {
        if (!el) return;
        el.textContent = valor;
        el.classList.toggle('hidden', !valor);
    }

    // Agrupa várias chamadas seguidas numa só requisição.
    function adiado(fn, ms) {
        var timer = null;
        return function () {
            clearTimeout(timer);
            timer = setTimeout(fn, ms);
        };
    }

    function buscarHtml(url) {
        return fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
            .then(function (r) {
                if (!r.ok || r.redirected) throw new Error('Falha ao carregar ' + url);
                return r.text();
            });
    }

    var atualizarUsuarios = adiado(function () {
        var alvos = document.querySelectorAll('[data-usuarios-online]');
        buscarHtml(cfg.usuariosUrl).then(function (html) {
            alvos.forEach(function (el) { el.innerHTML = html; });
            var raiz = alvos.length ? alvos[0].querySelector('[data-online-count]') : null;
            var total = raiz ? raiz.dataset.onlineCount : '0';
            var contador = document.getElementById('online-count');
            if (contador) contador.textContent = total;
            document.querySelectorAll('[data-online-count-label]').forEach(function (el) { el.textContent = total; });
        }).catch(function () {});
    }, 300);

    var atualizarConversas = adiado(function () {
        var lista = document.getElementById('lista-conversas');
        if (!lista) return;
        var url = cfg.conversasUrl + '?ativa=' + encodeURIComponent(lista.dataset.ativa || '');
        buscarHtml(url).then(function (html) { lista.innerHTML = html; }).catch(function () {});
    }, 300);

    function mostrarAviso(titulo, texto, url) {
        var area = document.getElementById('toasts');
        if (!area) return;
        var aviso = document.createElement('a');
        aviso.href = url;
        aviso.className = 'block bg-white border border-slate-200 shadow-lg rounded-xl p-3 hover:bg-slate-50 transition';
        var t = document.createElement('p');
        t.className = 'text-sm font-semibold text-slate-800 truncate';
        t.textContent = titulo;
        var c = document.createElement('p');
        c.className = 'text-sm text-slate-600 line-clamp-2 break-words';
        c.textContent = texto.length > 140 ? texto.slice(0, 140) + '…' : texto;
        aviso.appendChild(t);
        aviso.appendChild(c);
        area.appendChild(aviso);
        setTimeout(function () { aviso.remove(); }, 6000);
    }

    // Painel "Online" do topo
    var botaoOnline = document.getElementById('online-toggle');
    var painelOnline = document.getElementById('online-painel');
    function abrirPainel(abrir) {
        if (!painelOnline) return;
        painelOnline.classList.toggle('hidden', !abrir);
        botaoOnline.setAttribute('aria-expanded', String(abrir));
    }
    if (botaoOnline && painelOnline) {
        botaoOnline.addEventListener('click', function (e) {
            e.stopPropagation();
            var abrir = painelOnline.classList.contains('hidden');
            abrirPainel(abrir);
            if (abrir) atualizarUsuarios();
        });
        document.addEventListener('click', function (e) {
            if (!painelOnline.contains(e.target)) abrirPainel(false);
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') abrirPainel(false);
        });
    }

    // Quem fica offline sem avisar (rede caiu) expira no servidor; a lista é revista periodicamente.
    setInterval(atualizarUsuarios, INTERVALO_LISTA_USUARIOS);

    window.TempoReal = { enviar: enviar };
    conectar();
})();
