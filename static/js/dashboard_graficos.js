/*
 * Gráficos do dashboard com Apache ECharts.
 *
 * Cada gráfico fica num <figure data-grafico="..."> com:
 *   [data-area-grafico]   onde o ECharts desenha
 *   [data-area-tabela]    a mesma informação em tabela (acessibilidade)
 *   [data-alternar-tabela] botão que alterna gráfico/tabela
 *   [data-estado]         mensagem de vazio/erro
 *   [data-subtitulo]      (opcional) texto preenchido a partir dos dados
 *
 * Cores: identidade da Secretaria (anil, folha), validadas com o validador de
 * dataviz (separação para daltonismo, contraste e luminosidade) contra a superfície
 * branca dos cards. Não trocar sem revalidar.
 */
(function () {
    'use strict';

    var raiz = document.getElementById('dashboard-graficos');
    if (!raiz) return;

    var COR = {
        superficie: '#ffffff',
        tinta: '#1e2230',            // grafite (--cor-texto)
        tintaSecundaria: '#565a67',
        tintaFraca: '#6b6f7b',
        grade: '#e6e8ef',
        eixo: '#c8cbd6',
        borda: 'rgba(30,34,48,0.12)',
        barra: '#2b3a8c',            // anil (--cor-primaria): gráficos de uma série
        serie1: '#4a64c8',           // anil médio: Abertos
        serie2: '#2e7a4c',           // folha (--cor-sucesso): Concluídos
        // Rampa ordinal de um só tom: mais escuro = mais urgente (Urgente → Baixa).
        prioridade: ['#1f2a6b', '#2b3a8c', '#4a64c8', '#8d98d4'],
    };
    var FONTE = "'Lexend', system-ui, -apple-system, 'Segoe UI', sans-serif";
    var ALTURA_BARRA = 40;   // altura reservada por categoria nos gráficos de barras

    if (!window.echarts) {
        mostrarErroGeral('A biblioteca de gráficos não carregou. Verifique a conexão e recarregue a página.');
        return;
    }
    var esc = echarts.format.encodeHTML;

    // ------------------------------------------------------------------ util

    function numero(n) {
        return Number(n).toLocaleString('pt-BR');
    }

    function dataBR(iso) {
        var p = iso.split('-');
        return p[2] + '/' + p[1] + '/' + p[0];
    }

    // Nome completo continua no tooltip e na tabela.
    function abreviar(texto, max) {
        return texto.length > max ? texto.slice(0, max - 1).trimEnd() + '…' : texto;
    }

    function corSegura(cor) {
        return /^#[0-9a-f]{3,8}$/i.test(cor || '') ? cor : COR.eixo;
    }

    // Chave de linha no tooltip (um traço curto, não uma caixa).
    function chaveLinha(cor) {
        return '<span style="display:inline-block;width:12px;height:2px;border-radius:1px;background:' +
            cor + ';vertical-align:middle;margin-right:8px"></span>';
    }

    function linhaTooltip(cor, valor, rotulo) {
        // Valor primeiro e em destaque; o nome vem depois, secundário.
        return '<div style="display:flex;align-items:center;gap:6px;line-height:1.6">' + chaveLinha(cor) +
            '<strong style="color:' + COR.tinta + ';font-weight:600">' + esc(valor) + '</strong>' +
            '<span style="color:' + COR.tintaSecundaria + '">' + esc(rotulo) + '</span></div>';
    }

    function cabecalhoTooltip(texto) {
        return '<div style="color:' + COR.tintaFraca + ';font-size:11px;margin-bottom:2px">' + esc(texto) + '</div>';
    }

    var TOOLTIP_BASE = {
        backgroundColor: COR.superficie,
        borderColor: COR.borda,
        borderWidth: 1,
        padding: [8, 10],
        textStyle: { color: COR.tinta, fontSize: 12, fontFamily: FONTE },
        extraCssText: 'box-shadow:0 4px 12px rgba(0,0,0,.08);border-radius:8px;',
        confine: true,
    };

    var OPCAO_BASE = {
        textStyle: { fontFamily: FONTE },
        animationDuration: 400,
        aria: { enabled: true },
    };

    // --------------------------------------------------------- linha semanal

    function graficoLinha(d) {
        var series = [
            { nome: 'Abertos', valores: d.abertos, cor: COR.serie1 },
            { nome: 'Concluídos', valores: d.concluidos, cor: COR.serie2 },
        ];
        var vazio = d.abertos.concat(d.concluidos).every(function (v) { return v === 0; });
        var ultimo = d.labels.length - 1;
        var maximo = Math.max.apply(null, d.abertos.concat(d.concluidos).concat([1]));
        // Rótulos no fim das linhas só quando não colidem; senão, legenda + tooltip bastam.
        var rotulosFinais = Math.abs(d.abertos[ultimo] - d.concluidos[ultimo]) > maximo * 0.12;

        return {
            vazio: vazio,
            descricao: 'Gráfico de linhas com os chamados abertos e concluídos por semana nas últimas 12 semanas. ' +
                'Na semana atual: ' + numero(d.abertos[ultimo]) + ' abertos e ' + numero(d.concluidos[ultimo]) +
                ' concluídos. Os valores de cada semana estão na tabela do botão Ver tabela.',
            mensagemVazio: 'Nenhum chamado aberto ou concluído nas últimas 12 semanas.',
            altura: 256,
            pontos: d.labels.length,
            inicioTeclado: ultimo,
            opcao: Object.assign({}, OPCAO_BASE, {
                legend: {
                    top: 0, left: 0, icon: 'roundRect', itemWidth: 14, itemHeight: 3, itemGap: 16,
                    textStyle: { color: COR.tintaSecundaria, fontSize: 12 },
                },
                grid: {
                    top: 36, left: 4, right: rotulosFinais ? 96 : 12, bottom: 4,
                    outerBoundsMode: 'same', outerBoundsContain: 'axisLabel',
                },
                tooltip: Object.assign({}, TOOLTIP_BASE, {
                    trigger: 'axis',
                    axisPointer: { type: 'line', lineStyle: { color: COR.eixo, width: 1, type: 'solid' } },
                    formatter: function (params) {
                        var i = params[0].dataIndex;
                        return cabecalhoTooltip('Semana de ' + dataBR(d.datas[i])) + params.map(function (p) {
                            return linhaTooltip(p.color, numero(p.value), p.seriesName);
                        }).join('');
                    },
                }),
                xAxis: {
                    type: 'category', boundaryGap: false, data: d.labels,
                    axisLine: { lineStyle: { color: COR.eixo } },
                    axisTick: { show: false },
                    axisLabel: { color: COR.tintaFraca, fontSize: 11 },
                },
                yAxis: {
                    type: 'value', minInterval: 1,
                    axisLabel: { color: COR.tintaFraca, fontSize: 11 },
                    splitLine: { lineStyle: { color: COR.grade, width: 1, type: 'solid' } },
                },
                series: series.map(function (s) {
                    return {
                        name: s.nome, type: 'line', data: s.valores, color: s.cor,
                        lineStyle: { width: 2, cap: 'round', join: 'round' },
                        symbol: 'circle', symbolSize: 8, showSymbol: false,
                        itemStyle: { color: s.cor, borderColor: COR.superficie, borderWidth: 2 },
                        emphasis: { disabled: true },
                        endLabel: {
                            show: rotulosFinais, distance: 10, color: COR.tintaSecundaria, fontSize: 11,
                            formatter: function (p) { return p.seriesName + ': ' + numero(p.value); },
                        },
                        // Ponto no fim da linha, com anel da cor da superfície.
                        markPoint: {
                            silent: true, animation: false, symbol: 'circle', symbolSize: 8,
                            itemStyle: { color: s.cor, borderColor: COR.superficie, borderWidth: 2 },
                            label: { show: false },
                            data: [{ coord: [ultimo, s.valores[ultimo]] }],
                        },
                    };
                }),
            }),
            tabela: {
                cabecalho: ['Semana (início)', 'Abertos', 'Concluídos'],
                linhas: d.datas.map(function (iso, i) { return [dataBR(iso), d.abertos[i], d.concluidos[i]]; }),
            },
        };
    }

    // ---------------------------------------------------- barras horizontais

    function barrasHorizontais(cfg) {
        // cfg: nomes, valores, cores (uma por barra), rotulo(valor, i), tooltip(valor, i), marcadores (opcional)
        var rich = { n: { color: COR.tintaSecundaria, fontSize: 12 } };
        if (cfg.marcadores) {
            cfg.marcadores.forEach(function (cor, i) {
                rich['m' + i] = { width: 8, height: 8, borderRadius: 4, backgroundColor: corSegura(cor) };
            });
        }
        return Object.assign({}, OPCAO_BASE, {
            grid: { top: 4, left: 4, right: 64, bottom: 4, outerBoundsMode: 'same', outerBoundsContain: 'axisLabel' },
            tooltip: Object.assign({}, TOOLTIP_BASE, {
                trigger: 'axis',
                // A faixa inteira da categoria é a área de toque, maior que a barra.
                axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(11,11,11,0.04)' } },
                formatter: function (params) {
                    var p = params[0];
                    return cabecalhoTooltip(cfg.nomes[p.dataIndex]) +
                        linhaTooltip(cfg.cores[p.dataIndex], cfg.tooltip(p.value, p.dataIndex), cfg.unidade);
                },
            }),
            // Todas as barras têm o valor na ponta, então o eixo de valores é dispensável.
            xAxis: { type: 'value', show: false, minInterval: 1, max: function (v) { return Math.max(v.max, 1); } },
            yAxis: {
                type: 'category', inverse: true, data: cfg.nomes,
                axisTick: { show: false },
                axisLine: { lineStyle: { color: COR.eixo } },
                axisLabel: {
                    margin: 10,
                    rich: rich,
                    formatter: function (nome, i) {
                        // Chaves e barras verticais têm significado no texto rico do ECharts.
                        var limpo = abreviar(String(nome).replace(/[{}|]/g, ''), 22);
                        // Marcador da cor da entidade logo antes do eixo, ao lado do nome.
                        return '{n|' + limpo + '}' + (cfg.marcadores ? ' {m' + i + '| }' : '');
                    },
                },
            },
            series: [{
                type: 'bar',
                data: cfg.valores.map(function (v, i) { return { value: v, itemStyle: { color: cfg.cores[i] } }; }),
                barMaxWidth: 24,
                // Ponta arredondada (4px) do lado do valor; quadrada na linha de base.
                itemStyle: { borderRadius: [0, 4, 4, 0] },
                label: {
                    show: true, position: 'right', distance: 8, color: COR.tintaSecundaria, fontSize: 11,
                    formatter: function (p) { return cfg.rotulo(p.value, p.dataIndex); },
                },
                emphasis: { itemStyle: { opacity: 0.85 } },
            }],
        });
    }

    function ordenarDecrescente(nomes, valores, extra) {
        var idx = nomes.map(function (_, i) { return i; });
        idx.sort(function (a, b) { return valores[b] - valores[a] || String(nomes[a]).localeCompare(nomes[b], 'pt-BR'); });
        return {
            nomes: idx.map(function (i) { return nomes[i]; }),
            valores: idx.map(function (i) { return valores[i]; }),
            extra: extra ? idx.map(function (i) { return extra[i]; }) : null,
        };
    }

    function listar(nomes, valores) {
        return nomes.map(function (n, i) { return n + ' ' + numero(valores[i]); }).join(', ');
    }

    function alturaBarras(n) {
        return Math.max(160, n * ALTURA_BARRA + 16);
    }

    function graficoPlataformas(d) {
        var o = ordenarDecrescente(d.labels, d.totais, d.cores);
        var total = o.valores.reduce(function (a, b) { return a + b; }, 0);
        return {
            vazio: !o.nomes.length || total === 0,
            mensagemVazio: o.nomes.length ? 'Nenhum chamado ativo nas plataformas.' : 'Nenhuma plataforma ativa.',
            descricao: 'Gráfico de barras com os chamados ativos por plataforma: ' + listar(o.nomes, o.valores) + '.',
            altura: alturaBarras(o.nomes.length),
            pontos: o.nomes.length,
            opcao: barrasHorizontais({
                nomes: o.nomes, valores: o.valores, marcadores: o.extra,
                cores: o.nomes.map(function () { return COR.barra; }),
                unidade: 'chamados ativos',
                rotulo: numero, tooltip: numero,
            }),
            tabela: {
                cabecalho: ['Plataforma', 'Chamados ativos'],
                linhas: o.nomes.map(function (n, i) { return [n, o.valores[i]]; }),
            },
        };
    }

    function graficoDevs(d) {
        var o = ordenarDecrescente(d.labels, d.totais);
        var total = o.valores.reduce(function (a, b) { return a + b; }, 0);
        return {
            vazio: !o.nomes.length || total === 0,
            mensagemVazio: o.nomes.length ? 'Nenhum chamado concluído neste mês.' : 'Nenhum desenvolvedor ativo.',
            descricao: 'Gráfico de barras com os chamados concluídos por desenvolvedor no mês: ' + listar(o.nomes, o.valores) + '.',
            altura: alturaBarras(o.nomes.length),
            pontos: o.nomes.length,
            opcao: barrasHorizontais({
                nomes: o.nomes, valores: o.valores,
                cores: o.nomes.map(function () { return COR.barra; }),
                unidade: 'concluídos no mês',
                rotulo: numero, tooltip: numero,
            }),
            tabela: {
                cabecalho: ['Desenvolvedor', 'Concluídos no mês'],
                linhas: o.nomes.map(function (n, i) { return [n, o.valores[i]]; }),
            },
        };
    }

    function graficoPrioridades(d) {
        // Ordem natural (Urgente → Baixa), não por tamanho.
        var total = d.totais.reduce(function (a, b) { return a + b; }, 0);
        function percentual(v) { return total ? Math.round((v / total) * 100) + '%' : '0%'; }
        return {
            vazio: total === 0,
            mensagemVazio: 'Nenhum chamado ativo.',
            descricao: 'Gráfico de barras com os ' + numero(total) + ' chamados ativos por prioridade: ' +
                d.labels.map(function (n, i) { return n + ' ' + numero(d.totais[i]) + ' (' + percentual(d.totais[i]) + ')'; }).join(', ') + '.',
            subtitulo: numero(total) + (total === 1 ? ' chamado ativo' : ' chamados ativos'),
            altura: alturaBarras(d.labels.length),
            pontos: d.labels.length,
            opcao: barrasHorizontais({
                nomes: d.labels, valores: d.totais, cores: COR.prioridade,
                unidade: 'chamados ativos',
                rotulo: function (v) { return numero(v) + ' · ' + percentual(v); },
                tooltip: function (v) { return numero(v) + ' (' + percentual(v) + ')'; },
            }),
            tabela: {
                cabecalho: ['Prioridade', 'Chamados ativos', '% dos ativos'],
                linhas: d.labels.map(function (n, i) { return [n, d.totais[i], percentual(d.totais[i])]; }),
            },
        };
    }

    // ------------------------------------------------------------ montagem

    var CONSTRUTORES = {
        linha: function (dados) { return graficoLinha(dados.linha); },
        plataformas: function (dados) { return graficoPlataformas(dados.plataformas); },
        devs: function (dados) { return graficoDevs(dados.devs); },
        prioridades: function (dados) { return graficoPrioridades(dados.prioridades); },
    };

    var graficos = [];

    function montarTabela(destino, tabela) {
        var t = document.createElement('table');
        t.className = 'table table-sm align-middle mb-0 small';
        var thead = t.createTHead().insertRow();
        tabela.cabecalho.forEach(function (c, i) {
            var th = document.createElement('th');
            th.scope = 'col';
            th.className = i ? 'text-end' : '';
            th.textContent = c;
            thead.appendChild(th);
        });
        var tbody = t.createTBody();
        tabela.linhas.forEach(function (linha) {
            var tr = tbody.insertRow();
            linha.forEach(function (valor, i) {
                var td = tr.insertCell();
                td.className = i ? 'text-end' : '';
                td.textContent = typeof valor === 'number' ? numero(valor) : valor;
            });
        });
        destino.replaceChildren(t);
    }

    function mostrarEstado(fig, texto) {
        var estado = fig.querySelector('[data-estado]');
        estado.textContent = texto;
        estado.classList.remove('d-none');
        fig.querySelector('[data-area-grafico]').classList.add('d-none');
        var botao = fig.querySelector('[data-alternar-tabela]');
        if (botao) botao.classList.add('d-none');
    }

    function mostrarErroGeral(texto, permitirNovaTentativa) {
        raiz.querySelectorAll('[data-grafico]').forEach(function (fig) {
            mostrarEstado(fig, texto);
            if (!permitirNovaTentativa) return;
            var botao = document.createElement('button');
            botao.type = 'button';
            botao.className = 'btn btn-sm btn-outline-primary d-block mx-auto mt-3';
            botao.textContent = 'Tentar de novo';
            botao.addEventListener('click', function () {
                raiz.querySelectorAll('[data-grafico]').forEach(limparEstado);
                carregar();
            });
            fig.querySelector('[data-estado]').appendChild(botao);
        });
    }

    function limparEstado(fig) {
        var estado = fig.querySelector('[data-estado]');
        estado.replaceChildren();
        estado.classList.add('d-none');
        fig.querySelector('[data-area-grafico]').classList.remove('d-none');
        var botao = fig.querySelector('[data-alternar-tabela]');
        if (botao) botao.classList.remove('d-none');
    }

    // Tooltip também pelo teclado: Tab foca o gráfico; setas, Home e End percorrem; Esc fecha.
    function ativarTeclado(area, grafico, total, inicio) {
        if (!total) return;
        area.tabIndex = 0;
        var atual = -1;
        function mostrar(i) {
            atual = Math.min(Math.max(i, 0), total - 1);
            grafico.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: atual });
        }
        area.addEventListener('focus', function () { mostrar(atual < 0 ? (inicio || 0) : atual); });
        area.addEventListener('blur', function () { grafico.dispatchAction({ type: 'hideTip' }); });
        area.addEventListener('keydown', function (e) {
            var passo = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
            if (passo) { e.preventDefault(); mostrar(atual + passo); }
            else if (e.key === 'Home') { e.preventDefault(); mostrar(0); }
            else if (e.key === 'End') { e.preventDefault(); mostrar(total - 1); }
            else if (e.key === 'Escape') { grafico.dispatchAction({ type: 'hideTip' }); }
        });
    }

    function configurarAlternancia(fig) {
        var botao = fig.querySelector('[data-alternar-tabela]');
        if (!botao) return;
        botao.addEventListener('click', function () {
            var verTabela = botao.getAttribute('aria-pressed') !== 'true';
            botao.setAttribute('aria-pressed', String(verTabela));
            botao.textContent = verTabela ? 'Ver gráfico' : 'Ver tabela';
            fig.querySelector('[data-area-tabela]').classList.toggle('d-none', !verTabela);
            fig.querySelector('[data-area-grafico]').classList.toggle('d-none', verTabela);
            if (!verTabela) graficos.forEach(function (g) { g.resize(); });
        });
    }

    function renderizar(dados) {
        raiz.querySelectorAll('[data-grafico]').forEach(function (fig) {
            var construir = CONSTRUTORES[fig.dataset.grafico];
            if (!construir) return;
            var g = construir(dados);
            var subtitulo = fig.querySelector('[data-subtitulo]');
            if (subtitulo && g.subtitulo) subtitulo.textContent = g.subtitulo;
            if (g.vazio) {
                mostrarEstado(fig, g.mensagemVazio);
                return;
            }
            var area = fig.querySelector('[data-area-grafico]');
            area.style.height = g.altura + 'px';
            var grafico = echarts.init(area, null, { renderer: 'svg', locale: 'PT-br' });
            g.opcao.aria = {
                enabled: true,
                label: { description: g.descricao + ' Com o gráfico em foco, use as setas para percorrer os valores.' },
            };
            grafico.setOption(g.opcao);
            graficos.push(grafico);
            ativarTeclado(area, grafico, g.pontos, g.inicioTeclado);
            montarTabela(fig.querySelector('[data-area-tabela]'), g.tabela);
            configurarAlternancia(fig);
        });

        if ('ResizeObserver' in window) {
            var observador = new ResizeObserver(function () { graficos.forEach(function (g) { g.resize(); }); });
            raiz.querySelectorAll('[data-area-grafico]').forEach(function (a) { observador.observe(a); });
        } else {
            window.addEventListener('resize', function () { graficos.forEach(function (g) { g.resize(); }); });
        }
    }

    // O ECharts mede os rótulos ao desenhar: esperar a Lexend carregar evita medir com a
    // fonte reserva (mais estreita) e cortar nomes longos depois.
    var fontesProntas = (document.fonts && document.fonts.ready)
        ? document.fonts.ready.catch(function () {})
        : Promise.resolve();

    function carregar() {
        fetch(raiz.dataset.url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function (dados) { return fontesProntas.then(function () { renderizar(dados); }); })
            .catch(function (erro) {
                console.error('Erro ao carregar os gráficos:', erro);
                mostrarErroGeral('Não foi possível carregar os dados deste gráfico.', true);
            });
    }

    carregar();
})();
