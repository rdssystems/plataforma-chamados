/*
 * Página do chat: abas Conversas/Online e a conversa aberta
 * (histórico paginado, envio, recebimento em tempo real e leitura).
 */
(function () {
    'use strict';

    var dadosEl = document.getElementById('chat-dados');
    if (!dadosEl) return;
    var dados = JSON.parse(dadosEl.textContent);

    // --- Abas -----------------------------------------------------------------
    var abas = document.querySelectorAll('[data-aba]');
    function mostrarAba(nome) {
        abas.forEach(function (b) {
            var ativa = b.dataset.aba === nome;
            b.classList.toggle('text-blue-600', ativa);
            b.classList.toggle('border-blue-600', ativa);
            b.classList.toggle('text-slate-500', !ativa);
            b.classList.toggle('border-transparent', !ativa);
            b.setAttribute('aria-selected', String(ativa));
        });
        document.querySelectorAll('[data-painel]').forEach(function (p) {
            p.classList.toggle('hidden', p.dataset.painel !== nome);
        });
    }
    abas.forEach(function (b) {
        b.addEventListener('click', function () { mostrarAba(b.dataset.aba); });
    });
    var temConversas = document.querySelector('#lista-conversas [data-conversa-id]');
    mostrarAba(temConversas || dados.conversaId ? 'conversas' : 'online');

    if (!dados.conversaId) return;

    // --- Conversa aberta ------------------------------------------------------
    window.chatConversaAberta = dados.conversaId;
    var lista = document.getElementById('mensagens');
    var blocoAnteriores = document.getElementById('carregar-anteriores');
    var form = document.getElementById('form-mensagem');
    var csrf = document.getElementById('chat-csrf').value;
    var mensagens = [];
    var ids = new Set();

    function adicionar(novas) {
        var adicionadas = 0;
        novas.forEach(function (m) {
            if (ids.has(m.id)) return;
            ids.add(m.id);
            mensagens.push(m);
            adicionadas++;
        });
        mensagens.sort(function (a, b) { return a.id - b.id; });
        return adicionadas;
    }

    function el(tag, classes, texto) {
        var e = document.createElement(tag);
        if (classes) e.className = classes;
        if (texto !== undefined) e.textContent = texto;
        return e;
    }

    function rotuloDia(data) {
        var hoje = new Date();
        var ontem = new Date();
        ontem.setDate(hoje.getDate() - 1);
        if (data.toDateString() === hoje.toDateString()) return 'Hoje';
        if (data.toDateString() === ontem.toDateString()) return 'Ontem';
        return data.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
    }

    function bolha(m) {
        var minha = m.autor_id === dados.usuarioId;
        var data = new Date(m.criada_em);
        var linha = el('div', 'flex ' + (minha ? 'justify-end' : 'justify-start'));
        linha.dataset.item = '';
        var caixa = el('div', 'max-w-[75%] rounded-2xl px-3.5 py-2 text-sm shadow-sm ' +
            (minha ? 'bg-blue-600 text-white rounded-br-md' : 'bg-white text-slate-800 border border-slate-200 rounded-bl-md'));
        caixa.appendChild(el('p', 'whitespace-pre-wrap break-words', m.texto));
        var hora = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        caixa.appendChild(el('p', 'mt-1 text-[11px] text-right ' + (minha ? 'text-blue-100' : 'text-slate-400'), hora));
        caixa.title = data.toLocaleString('pt-BR');
        linha.appendChild(caixa);
        return linha;
    }

    function renderizar() {
        lista.querySelectorAll('[data-item]').forEach(function (e) { e.remove(); });
        var diaAtual = null;
        var fragmento = document.createDocumentFragment();
        mensagens.forEach(function (m) {
            var data = new Date(m.criada_em);
            if (data.toDateString() !== diaAtual) {
                diaAtual = data.toDateString();
                var sep = el('div', 'flex justify-center py-2');
                sep.dataset.item = '';
                sep.appendChild(el('span', 'text-[11px] font-medium text-slate-500 bg-slate-200/70 px-2.5 py-0.5 rounded-full', rotuloDia(data)));
                fragmento.appendChild(sep);
            }
            fragmento.appendChild(bolha(m));
        });
        if (!mensagens.length) {
            var vazio = el('p', 'text-center text-sm text-slate-400 py-8', 'Nenhuma mensagem ainda. Diga olá!');
            vazio.dataset.item = '';
            fragmento.appendChild(vazio);
        }
        lista.appendChild(fragmento);
    }

    function pertoDoFim() {
        return lista.scrollHeight - lista.scrollTop - lista.clientHeight < 120;
    }
    function rolarParaFim() {
        lista.scrollTop = lista.scrollHeight;
    }
    function mostrarCarregarAnteriores(temMais) {
        blocoAnteriores.classList.toggle('hidden', !temMais);
    }

    function buscarJson(url) {
        return fetch(url, { credentials: 'same-origin' }).then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });
    }

    // Histórico mais antigo, preservando a posição de leitura.
    blocoAnteriores.querySelector('button').addEventListener('click', function () {
        if (!mensagens.length) return;
        var botao = this;
        botao.disabled = true;
        buscarJson(dados.urlMensagens + '?antes=' + mensagens[0].id).then(function (r) {
            var alturaAntes = lista.scrollHeight;
            adicionar(r.mensagens);
            renderizar();
            lista.scrollTop += lista.scrollHeight - alturaAntes;
            mostrarCarregarAnteriores(r.tem_mais);
        }).finally(function () { botao.disabled = false; });
    });

    // Leitura
    var marcandoLida = false;
    function marcarLida() {
        if (marcandoLida || document.hidden) return;
        marcandoLida = true;
        fetch(dados.urlLida, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrf } })
            .finally(function () { marcandoLida = false; });
    }
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) marcarLida();
    });

    // Tempo real
    document.addEventListener('tempo-real', function (e) {
        var d = e.detail;
        if (d.tipo === 'chat.mensagem' && d.mensagem.conversa_id === dados.conversaId) {
            var estavaNoFim = pertoDoFim();
            if (adicionar([d.mensagem])) {
                renderizar();
                if (estavaNoFim || d.mensagem.autor_id === dados.usuarioId) rolarParaFim();
            }
            if (d.mensagem.autor_id !== dados.usuarioId) marcarLida();
        } else if (d.tipo === 'presenca' && d.usuario_id === dados.outroId) {
            var status = document.getElementById('status-outro');
            if (status && status.textContent.trim() !== 'Usuário desativado') {
                status.textContent = d.online ? 'Online' : 'Offline';
                status.className = 'text-xs ' + (d.online ? 'text-emerald-600' : 'text-slate-400');
            }
        }
    });

    // Após uma queda de conexão, busca o que chegou nesse meio tempo.
    var primeiraConexao = true;
    document.addEventListener('tempo-real-conectado', function () {
        if (primeiraConexao) { primeiraConexao = false; return; }
        var ultimoId = mensagens.length ? mensagens[mensagens.length - 1].id : 0;
        buscarJson(dados.urlMensagens + '?depois=' + ultimoId).then(function (r) {
            var estavaNoFim = pertoDoFim();
            if (adicionar(r.mensagens)) {
                renderizar();
                if (estavaNoFim) rolarParaFim();
                marcarLida();
            }
        }).catch(function () {});
    });

    // Envio
    if (form) {
        var campo = form.querySelector('textarea');
        var botaoEnviar = form.querySelector('button[type=submit]');
        var erro = document.getElementById('erro-envio');

        function ajustarAltura() {
            campo.style.height = 'auto';
            campo.style.height = Math.min(campo.scrollHeight, 160) + 'px';
        }
        campo.addEventListener('input', ajustarAltura);
        campo.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
                e.preventDefault();
                form.requestSubmit();
            }
        });

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (!campo.value.trim() || botaoEnviar.disabled) return;
            botaoEnviar.disabled = true;
            erro.classList.add('hidden');
            fetch(form.action, { method: 'POST', body: new FormData(form), credentials: 'same-origin' })
                .then(function (r) {
                    return r.json().catch(function () { return {}; }).then(function (corpo) {
                        if (!r.ok) throw new Error(corpo.erro || 'Não foi possível enviar a mensagem.');
                        return corpo;
                    });
                })
                .then(function (corpo) {
                    if (adicionar([corpo.mensagem])) renderizar();
                    rolarParaFim();
                    campo.value = '';
                    ajustarAltura();
                })
                .catch(function (err) {
                    erro.textContent = err.message;
                    erro.classList.remove('hidden');
                })
                .finally(function () {
                    botaoEnviar.disabled = false;
                    campo.focus();
                });
        });
        campo.focus();
    }

    adicionar(dados.mensagens);
    renderizar();
    rolarParaFim();
    mostrarCarregarAnteriores(dados.temMais);
})();
