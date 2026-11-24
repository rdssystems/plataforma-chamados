/*
 * Conexão em tempo real (WebSocket) usada em todas as páginas autenticadas.
 * - mantém a presença do usuário (online/offline) com um "ping" periódico;
 * - atualiza os contadores de chat e notificações e mostra avisos (toasts);
 * - mantém atualizadas as listas de usuários online e de conversas;
 * - repassa cada evento recebido como `tempo-real` no `document` (usado pelo chat);
 * - sinaliza mensagem nova de chat: aviso na tela, som, título piscando e, se a
 *   pessoa permitir, notificação do sistema (preferências guardadas no navegador).
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
            atualizarContador('[data-contador-chat]', dados.nao_lidas_total);
            var m = dados.mensagem;
            var conversaVisivel = window.chatConversaAberta === m.conversa_id && !document.hidden;
            if (m.autor_id !== cfg.usuarioId && !conversaVisivel) {
                mostrarAviso(m.autor_nome, m.texto, '/chat/' + m.conversa_id + '/', m.conversa_id);
                sinalizarMensagem(m);
            }
            atualizarConversas();
        } else if (dados.tipo === 'chat.lida') {
            atualizarContador('[data-contador-chat]', dados.nao_lidas_total);
            atualizarConversas();
        } else if (dados.tipo === 'notificacao') {
            atualizarContador('[data-contador-notificacoes]', dados.nao_lidas);
            mostrarAviso('Notificação', dados.mensagem, dados.url);
        } else if (dados.tipo === 'presenca') {
            atualizarUsuarios();
        }
    }

    // Contadores aparecem na barra e no menu lateral: atualiza todos.
    function atualizarContador(seletor, valor) {
        document.querySelectorAll(seletor).forEach(function (el) {
            var alvo = el.querySelector('[data-contador-valor]') || el;
            alvo.textContent = valor;
            el.classList.toggle('d-none', !valor);
        });
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

    // Listas de conversas da página do chat e do chat flutuante.
    var atualizarConversas = adiado(function () {
        document.querySelectorAll('[data-lista-conversas]').forEach(function (lista) {
            var url = cfg.conversasUrl + '?ativa=' + encodeURIComponent(lista.dataset.ativa || '');
            buscarHtml(url).then(function (html) { lista.innerHTML = html; }).catch(function () {});
        });
    }, 300);

    function mostrarAviso(titulo, texto, url, conversaId) {
        var area = document.getElementById('avisos');
        if (!area) return;
        var aviso = document.createElement('a');
        aviso.href = url;
        aviso.className = 'aviso';
        if (conversaId) aviso.dataset.conversaId = conversaId;  // o chat flutuante abre a conversa
        var t = document.createElement('span');
        t.className = 'aviso-titulo';
        t.textContent = titulo;
        var c = document.createElement('span');
        c.className = 'aviso-texto';
        c.textContent = texto.length > 140 ? texto.slice(0, 140) + '…' : texto;
        aviso.appendChild(t);
        aviso.appendChild(c);
        area.appendChild(aviso);
        setTimeout(function () { aviso.remove(); }, 6000);
    }

    // Lista "Online" da barra: atualiza ao abrir o menu suspenso.
    var botaoOnline = document.getElementById('botao-online');
    if (botaoOnline) botaoOnline.addEventListener('show.bs.dropdown', function () { atualizarUsuarios(); });

    // Quem fica offline sem avisar (rede caiu) expira no servidor; a lista é revista periodicamente.
    setInterval(atualizarUsuarios, INTERVALO_LISTA_USUARIOS);

    // --- Sinalização de mensagem nova -------------------------------------------

    var CHAVE_PREFS = 'chat.avisos';
    var prefs = lerPrefs();

    function lerPrefs() {
        var padrao = { som: true, sistema: false };
        try { return Object.assign(padrao, JSON.parse(localStorage.getItem(CHAVE_PREFS) || '{}')); } catch (_) { return padrao; }
    }
    function salvarPrefs() {
        try { localStorage.setItem(CHAVE_PREFS, JSON.stringify(prefs)); } catch (_) {}
    }
    function sincronizarControles(aviso) {
        document.querySelectorAll('[data-pref]').forEach(function (campo) { campo.checked = !!prefs[campo.dataset.pref]; });
        document.querySelectorAll('[data-pref-aviso]').forEach(function (el) {
            el.textContent = aviso || '';
            el.hidden = !aviso;
        });
    }

    // Som gerado no navegador (sem arquivo). Os navegadores só liberam áudio depois de
    // uma interação da pessoa com a página, então o contexto é criado no primeiro clique/tecla.
    var audio = null;
    var ultimoSom = 0;
    function desbloquearAudio() {
        if (!audio) {
            var Contexto = window.AudioContext || window.webkitAudioContext;
            if (!Contexto) return;
            try { audio = new Contexto(); } catch (_) { return; }
        }
        if (audio.state === 'suspended') audio.resume().catch(function () {});
    }
    ['pointerdown', 'keydown', 'touchstart'].forEach(function (evento) {
        document.addEventListener(evento, desbloquearAudio, { passive: true });
    });

    function tocarSom(forcar) {
        if ((!prefs.som && !forcar) || !audio || audio.state !== 'running') return;
        var agora = Date.now();
        if (!forcar && agora - ultimoSom < 1500) return;  // rajada de mensagens = um aviso só
        ultimoSom = agora;
        var t = audio.currentTime;
        // Dois toques curtos e suaves (La5 e Mi6).
        [[880, 0], [1318.5, 0.13]].forEach(function (nota) {
            var osc = audio.createOscillator();
            var vol = audio.createGain();
            osc.type = 'sine';
            osc.frequency.value = nota[0];
            vol.gain.setValueAtTime(0.0001, t + nota[1]);
            vol.gain.exponentialRampToValueAtTime(0.16, t + nota[1] + 0.02);
            vol.gain.exponentialRampToValueAtTime(0.0001, t + nota[1] + 0.35);
            osc.connect(vol);
            vol.connect(audio.destination);
            osc.start(t + nota[1]);
            osc.stop(t + nota[1] + 0.4);
        });
    }

    // Título da aba pisca enquanto a pessoa está em outra aba.
    var tituloOriginal = document.title;
    var piscador = null;
    var naoVistas = 0;
    function piscarTitulo(nome) {
        if (!document.hidden) return;
        naoVistas++;
        var alerta = '(' + naoVistas + ') Nova mensagem de ' + nome;
        var mostrandoAlerta = true;
        clearInterval(piscador);
        document.title = alerta;
        piscador = setInterval(function () {
            mostrandoAlerta = !mostrandoAlerta;
            document.title = mostrandoAlerta ? alerta : tituloOriginal;
        }, 1500);
    }
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) return;
        clearInterval(piscador);
        piscador = null;
        naoVistas = 0;
        document.title = tituloOriginal;
    });

    function notificarSistema(m) {
        if (!prefs.sistema || !document.hidden || !('Notification' in window) || Notification.permission !== 'granted') return;
        try {
            var n = new Notification('Nova mensagem de ' + m.autor_nome, {
                body: m.texto.length > 140 ? m.texto.slice(0, 140) + '…' : m.texto,
                tag: 'chat-' + m.conversa_id,  // várias abas abertas = uma notificação só
            });
            n.onclick = function () {
                window.focus();
                document.dispatchEvent(new CustomEvent('chat-abrir-conversa', { detail: { conversaId: m.conversa_id } }));
                n.close();
            };
        } catch (_) {}
    }

    // Com várias abas abertas, só uma toca o som: a visível tem prioridade.
    function primeiraAbaAvisar(mensagemId) {
        try {
            if (localStorage.getItem('chat.avisada') === String(mensagemId)) return false;
            localStorage.setItem('chat.avisada', String(mensagemId));
        } catch (_) {}
        return true;
    }

    function sinalizarMensagem(m) {
        piscarTitulo(m.autor_nome);
        setTimeout(function () {
            if (!primeiraAbaAvisar(m.id)) return;
            tocarSom(false);
            notificarSistema(m);
        }, document.hidden ? 250 : 0);
    }

    function recusarSistema(motivo) {
        prefs.sistema = false;
        salvarPrefs();
        sincronizarControles(motivo);
    }

    document.addEventListener('change', function (e) {
        var campo = e.target.closest('[data-pref]');
        if (!campo) return;
        var nome = campo.dataset.pref;
        if (nome === 'sistema' && campo.checked) {
            if (!('Notification' in window)) {
                recusarSistema('Este navegador não oferece notificações do sistema.');
                return;
            }
            if (Notification.permission === 'denied') {
                recusarSistema('As notificações estão bloqueadas para este site nas configurações do navegador.');
                return;
            }
            if (Notification.permission !== 'granted') {
                Notification.requestPermission().then(function (resposta) {
                    if (resposta === 'granted') {
                        prefs.sistema = true;
                        salvarPrefs();
                        sincronizarControles();
                    } else {
                        recusarSistema('Permissão não concedida pelo navegador.');
                    }
                });
                return;
            }
        }
        prefs[nome] = campo.checked;
        salvarPrefs();
        sincronizarControles();
        if (nome === 'som' && campo.checked) {
            desbloquearAudio();
            setTimeout(function () { tocarSom(true); }, 60);
        }
    });
    document.addEventListener('click', function (e) {
        if (!e.target.closest('[data-pref-testar]')) return;
        desbloquearAudio();
        // resume() é assíncrono: espera o contexto liberar antes de tocar.
        setTimeout(function () { tocarSom(true); }, 60);
    });
    // Preferências mudadas em outra aba.
    window.addEventListener('storage', function (e) {
        if (e.key !== CHAVE_PREFS) return;
        prefs = lerPrefs();
        sincronizarControles();
    });
    sincronizarControles();

    window.TempoReal = { enviar: enviar, tocarSom: tocarSom };
    conectar();
})();
