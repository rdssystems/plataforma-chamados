/*
 * Página do chat: abas Conversas/Online e a conversa aberta.
 * A conversa em si (histórico, envio, tempo real, leitura) fica em chat_conversa.js.
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
            b.setAttribute('aria-selected', String(b.dataset.aba === nome));  // o estilo vem do aria-selected
        });
        document.querySelectorAll('[data-painel]').forEach(function (p) {
            p.classList.toggle('d-none', p.dataset.painel !== nome);
        });
    }
    abas.forEach(function (b) {
        b.addEventListener('click', function () { mostrarAba(b.dataset.aba); });
    });
    var temConversas = document.querySelector('#lista-conversas [data-conversa-id]');
    mostrarAba(temConversas || dados.conversaId ? 'conversas' : 'online');

    if (!dados.conversaId || !window.ChatConversa) return;

    // --- Conversa aberta ------------------------------------------------------
    window.chatConversaAberta = dados.conversaId;
    var form = document.getElementById('form-mensagem');
    var conversa = window.ChatConversa({
        usuarioId: dados.usuarioId,
        conversaId: dados.conversaId,
        outroId: dados.outroId,
        urlMensagens: dados.urlMensagens,
        urlLida: dados.urlLida,
        csrf: document.getElementById('chat-csrf').value,
        lista: document.getElementById('mensagens'),
        blocoAnteriores: document.getElementById('carregar-anteriores'),
        form: form,
        erro: document.getElementById('erro-envio'),
        status: document.getElementById('status-outro'),
        mensagens: dados.mensagens,
        temMais: dados.temMais,
    });
    conversa.focar();
})();
