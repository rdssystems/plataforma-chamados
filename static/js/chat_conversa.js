/*
 * Uma conversa aberta: histórico paginado, envio, recebimento em tempo real,
 * leitura e recuperação após queda de conexão.
 * Usado pela página do chat (chat.js) e pela janela flutuante (chat_flutuante.js).
 *
 *   var conversa = ChatConversa({
 *       usuarioId, conversaId, outroId, urlMensagens, urlLida, csrf,
 *       lista, blocoAnteriores, form, erro, status,  // elementos (form/erro/status opcionais)
 *       mensagens, temMais,                         // página inicial (ou carrega sozinho)
 *       estaVisivel: function () { return true; },  // só marca como lida se estiver à vista
 *   });
 *   conversa.destruir();  // remove os ouvintes globais ao trocar de conversa
 */
(function () {
    'use strict';

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

    function buscarJson(url) {
        return fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } }).then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });
    }

    window.ChatConversa = function (o) {
        var mensagens = [];
        var ids = new Set();
        var ouvintes = [];
        var estaVisivel = o.estaVisivel || function () { return !document.hidden; };

        function ouvir(alvo, evento, fn) {
            alvo.addEventListener(evento, fn);
            ouvintes.push([alvo, evento, fn]);
        }

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

        function bolha(m) {
            var minha = m.autor_id === o.usuarioId;
            var data = new Date(m.criada_em);
            var linha = el('div', 'chat-linha' + (minha ? ' minha' : ''));
            linha.dataset.item = '';
            var caixa = el('div', 'chat-bolha');
            caixa.appendChild(el('p', 'mb-0 texto-livre', m.texto));
            caixa.appendChild(el('p', 'chat-bolha-hora mb-0', data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })));
            caixa.title = data.toLocaleString('pt-BR');
            linha.appendChild(caixa);
            return linha;
        }

        function renderizar() {
            o.lista.querySelectorAll('[data-item]').forEach(function (e) { e.remove(); });
            var diaAtual = null;
            var fragmento = document.createDocumentFragment();
            mensagens.forEach(function (m) {
                var data = new Date(m.criada_em);
                if (data.toDateString() !== diaAtual) {
                    diaAtual = data.toDateString();
                    var sep = el('div', 'chat-dia');
                    sep.dataset.item = '';
                    sep.appendChild(el('span', '', rotuloDia(data)));
                    fragmento.appendChild(sep);
                }
                fragmento.appendChild(bolha(m));
            });
            if (!mensagens.length) {
                var vazio = el('p', 'text-center small text-muted py-5 mb-0', 'Nenhuma mensagem ainda. Diga olá!');
                vazio.dataset.item = '';
                fragmento.appendChild(vazio);
            }
            o.lista.appendChild(fragmento);
        }

        function pertoDoFim() {
            return o.lista.scrollHeight - o.lista.scrollTop - o.lista.clientHeight < 120;
        }
        function rolarParaFim() {
            o.lista.scrollTop = o.lista.scrollHeight;
        }
        function mostrarCarregarAnteriores(temMais) {
            if (o.blocoAnteriores) o.blocoAnteriores.classList.toggle('d-none', !temMais);
        }

        var marcandoLida = false;
        function marcarLida() {
            if (marcandoLida || !estaVisivel()) return;
            marcandoLida = true;
            fetch(o.urlLida, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': o.csrf } })
                .finally(function () { marcandoLida = false; });
        }

        // Histórico mais antigo, preservando a posição de leitura.
        if (o.blocoAnteriores) {
            o.blocoAnteriores.querySelector('button').addEventListener('click', function () {
                if (!mensagens.length) return;
                var botao = this;
                botao.disabled = true;
                buscarJson(o.urlMensagens + '?antes=' + mensagens[0].id).then(function (r) {
                    var alturaAntes = o.lista.scrollHeight;
                    adicionar(r.mensagens);
                    renderizar();
                    o.lista.scrollTop += o.lista.scrollHeight - alturaAntes;
                    mostrarCarregarAnteriores(r.tem_mais);
                }).finally(function () { botao.disabled = false; });
            });
        }

        ouvir(document, 'visibilitychange', function () {
            if (!document.hidden) marcarLida();
        });

        ouvir(document, 'tempo-real', function (e) {
            var d = e.detail;
            if (d.tipo === 'chat.mensagem' && d.mensagem.conversa_id === o.conversaId) {
                var estavaNoFim = pertoDoFim();
                if (adicionar([d.mensagem])) {
                    renderizar();
                    if (estavaNoFim || d.mensagem.autor_id === o.usuarioId) rolarParaFim();
                }
                if (d.mensagem.autor_id !== o.usuarioId) marcarLida();
            } else if (d.tipo === 'presenca' && d.usuario_id === o.outroId && o.status) {
                if (o.status.dataset.desativado !== 'true') {
                    o.status.textContent = d.online ? 'Online' : 'Offline';
                    o.status.classList.toggle('text-success', d.online);
                    o.status.classList.toggle('text-muted', !d.online);
                }
            }
        });

        // Após uma queda de conexão, busca o que chegou nesse meio tempo.
        ouvir(document, 'tempo-real-conectado', function () {
            var ultimoId = mensagens.length ? mensagens[mensagens.length - 1].id : 0;
            buscarJson(o.urlMensagens + '?depois=' + ultimoId).then(function (r) {
                var estavaNoFim = pertoDoFim();
                if (adicionar(r.mensagens)) {
                    renderizar();
                    if (estavaNoFim) rolarParaFim();
                    marcarLida();
                }
            }).catch(function () {});
        });

        // Envio
        var campo = null;
        if (o.form) {
            campo = o.form.querySelector('textarea');
            var botaoEnviar = o.form.querySelector('button[type=submit]');

            var ajustarAltura = function () {
                campo.style.height = 'auto';
                campo.style.height = Math.min(campo.scrollHeight, 140) + 'px';
            };
            campo.addEventListener('input', ajustarAltura);
            campo.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
                    e.preventDefault();
                    o.form.requestSubmit();
                }
            });

            o.form.addEventListener('submit', function (e) {
                e.preventDefault();
                if (!campo.value.trim() || botaoEnviar.disabled) return;
                botaoEnviar.disabled = true;
                if (o.erro) o.erro.classList.add('d-none');
                fetch(o.form.action, { method: 'POST', body: new FormData(o.form), credentials: 'same-origin' })
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
                        if (o.erro) {
                            o.erro.textContent = err.message;
                            o.erro.classList.remove('d-none');
                        }
                    })
                    .finally(function () {
                        botaoEnviar.disabled = false;
                        campo.focus();
                    });
            });
        }

        function iniciar(pagina, temMais) {
            adicionar(pagina);
            renderizar();
            rolarParaFim();
            mostrarCarregarAnteriores(temMais);
            marcarLida();
        }

        if (o.mensagens) {
            iniciar(o.mensagens, o.temMais);
        } else {
            buscarJson(o.urlMensagens).then(function (r) { iniciar(r.mensagens, r.tem_mais); }).catch(function () {});
        }

        return {
            conversaId: o.conversaId,
            marcarLida: marcarLida,
            rolarParaFim: rolarParaFim,
            focar: function () { if (campo) campo.focus(); },
            destruir: function () {
                ouvintes.forEach(function (x) { x[0].removeEventListener(x[1], x[2]); });
                ouvintes = [];
            },
        };
    };
})();
