/*
 * Kanban: arrastar um card entre colunas muda o status (as regras ficam no servidor).
 * Transições que exigem justificativa abrem um modal; cancelar ou erro devolve o card.
 */
(() => {
    'use strict';

    const quadro = document.getElementById('kanban');
    if (!quadro || !window.Sortable) return;

    const urlMover = quadro.dataset.urlMover;
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    const modalEl = document.getElementById('modal-motivo');
    const modal = modalEl && window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const formMotivo = document.getElementById('form-motivo');
    const campoMotivo = document.getElementById('campo-motivo');
    const descricaoMotivo = document.getElementById('modal-motivo-descricao');

    // Mesmas regras do servidor (chamados/services.py): estas mudanças pedem motivo.
    const exigeMotivo = (de, para) =>
        para === 'cancelado' ||
        (de === 'em_revisao' && para === 'em_andamento') ||
        (de === 'concluido' && para === 'em_andamento');

    function aviso(texto, tipo) {
        const area = document.getElementById('avisos');
        if (!area) return;
        const el = document.createElement('div');
        el.className = 'aviso ' + (tipo === 'erro' ? 'aviso-erro' : 'aviso-sucesso');
        el.setAttribute('role', tipo === 'erro' ? 'alert' : 'status');
        const t = document.createElement('span');
        t.className = 'aviso-titulo';
        t.textContent = texto;
        el.appendChild(t);
        area.appendChild(el);
        setTimeout(() => el.remove(), 6000);
    }

    function atualizarContagens() {
        quadro.querySelectorAll('.kanban-coluna').forEach((col) => {
            col.querySelector('[data-contagem]').textContent = col.querySelectorAll('.kanban-card').length;
        });
    }

    function devolver(evt) {
        evt.from.insertBefore(evt.item, evt.from.children[evt.oldIndex] || null);
        atualizarContagens();
    }

    function pedirMotivo(codigo, destino) {
        return new Promise((resolver) => {
            if (!modal) {
                resolver(null);
                return;
            }
            let enviado = false;
            descricaoMotivo.textContent = `Mover ${codigo} para "${destino}" exige uma justificativa.`;
            campoMotivo.value = '';
            campoMotivo.classList.remove('is-invalid');
            const aoEnviar = (e) => {
                e.preventDefault();
                const motivo = campoMotivo.value.trim();
                if (!motivo) {
                    campoMotivo.classList.add('is-invalid');
                    campoMotivo.focus();
                    return;
                }
                enviado = true;
                modal.hide();
                resolver(motivo);
            };
            formMotivo.addEventListener('submit', aoEnviar);
            modalEl.addEventListener('shown.bs.modal', () => campoMotivo.focus(), { once: true });
            modalEl.addEventListener('hidden.bs.modal', () => {
                formMotivo.removeEventListener('submit', aoEnviar);
                if (!enviado) resolver(null);
            }, { once: true });
            modal.show();
        });
    }

    async function aoSoltar(evt) {
        const card = evt.item;
        const de = evt.from.dataset.status;
        const para = evt.to.dataset.status;
        const codigo = card.dataset.codigo;
        atualizarContagens();

        let motivo = '';
        if (de !== para && exigeMotivo(de, para)) {
            motivo = await pedirMotivo(codigo, evt.to.dataset.titulo);
            if (!motivo) {
                devolver(evt);
                aviso('Mudança cancelada: o motivo é obrigatório.', 'erro');
                return;
            }
        }

        const ordem = Array.from(evt.to.querySelectorAll('.kanban-card')).map((c) => c.dataset.id);
        try {
            const resposta = await fetch(urlMover, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                body: JSON.stringify({ chamado_id: card.dataset.id, novo_status: para, comentario: motivo, ordem_ids: ordem }),
            });
            const corpo = await resposta.json().catch(() => ({}));
            if (!resposta.ok || !corpo.sucesso) {
                devolver(evt);
                aviso(corpo.erro || 'Mudança não permitida pelas regras do fluxo.', 'erro');
                return;
            }
            if (de !== para) aviso(`${corpo.codigo} movido para ${corpo.status_display}.`, 'sucesso');
        } catch (_) {
            devolver(evt);
            aviso('Não foi possível salvar a mudança. Verifique a conexão e tente de novo.', 'erro');
        }
    }

    quadro.querySelectorAll('.kanban-lista').forEach((lista) => {
        new Sortable(lista, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'kanban-fantasma',
            dragClass: 'kanban-arrastando',
            filter: 'a, button',
            preventOnFilter: false,
            onEnd: aoSoltar,
        });
    });
})();
