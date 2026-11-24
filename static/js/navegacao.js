/*
 * Menu lateral (abaixo de 992px), no mesmo comportamento do Naicas:
 * fundo inerte enquanto aberto, foco devolvido ao botão ao fechar e
 * fechamento automático ao alargar a tela para o menu horizontal.
 */
(() => {
    'use strict';

    const menu = document.getElementById('menu-principal');
    const pagina = document.getElementById('pagina-app');
    const abrir = document.getElementById('abrir-menu');
    if (!menu || !pagina || !abrir) return;

    // Mesma condição do menu horizontal em secretaria.css.
    const desktop = window.matchMedia('(min-width: 992px)');
    const liberarPagina = () => {
        pagina.inert = false;
        abrir.setAttribute('aria-expanded', 'false');
    };
    const fecharMenu = () => window.bootstrap?.Offcanvas.getInstance(menu)?.hide();

    menu.addEventListener('show.bs.offcanvas', (event) => {
        if (desktop.matches) {
            event.preventDefault();
            return;
        }
        pagina.inert = true;
        abrir.setAttribute('aria-expanded', 'true');
    });
    menu.addEventListener('hidden.bs.offcanvas', () => {
        liberarPagina();
        const destino = desktop.matches ? document.querySelector('.navbar-brand') : abrir;
        destino?.focus({ preventScroll: true });
    });
    menu.addEventListener('click', (event) => {
        const link = event.target.closest('a[href]');
        if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
            fecharMenu();
        }
    });
    desktop.addEventListener('change', () => {
        if (!desktop.matches) return;
        fecharMenu();
        liberarPagina();
    });
    window.addEventListener('pageshow', (event) => {
        if (!event.persisted) return;
        const aberto = menu.classList.contains('show') || menu.classList.contains('showing');
        if (aberto) {
            fecharMenu();
        } else {
            liberarPagina();
        }
    });
})();
