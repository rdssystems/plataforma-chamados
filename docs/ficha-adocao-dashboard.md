# Ficha de adoção do padrão de dashboards — Gestão de Chamados

Preenchida a partir do **Padrão de dashboards dos sistemas da Secretaria** (`front-rules.md`, seção 8), com a interface do Naicas como referência visual. Itens marcados com **(a confirmar)** são escolhas feitas na implantação que ainda dependem de validação com a equipe responsável pelo serviço.

## Ficha (seção 8)

| Decisão | Gestão de Chamados |
| --- | --- |
| Público e escopo | **Administrador**: todos os chamados da equipe, com recorte opcional por desenvolvedor. **Desenvolvedor**: chamados atribuídos a ele ou abertos por ele. O escopo é aplicado no servidor (consulta), não só escondido na tela. |
| Pergunta do painel | O que exige atenção agora na fila de chamados: o que está atrasado, o que vence em breve e o que está sem responsável? **(a confirmar)** |
| Indicadores e fonte | Cadastro de chamados, dentro do escopo do perfil. Unidade: chamados. Regras em `chamados/consultas.py` (as mesmas da listagem): ver tabela abaixo. |
| Tempo e ausência | Situação atual, exceto "Concluídos no mês" (dia 1 do mês até hoje). Consulta válida sem resultados mostra **0**. Falha ao carregar um gráfico mostra a mensagem no bloco afetado e o botão "Tentar de novo". No relatório, "No prazo" sem concluídos com prazo mostra **—** com explicação. |
| Filtros e detalhe | Recorte por desenvolvedor (administrador). Cada indicador abre a listagem de chamados com a mesma situação e o mesmo recorte (`?situacao=...&responsavel=...`). |
| Rotina e ação | Fila de trabalho: atrasados (do prazo mais antigo) e que vencem em até 3 dias, cada item com "Abrir". No chamado, as próximas ações permitidas ao perfil (iniciar, enviar para revisão, aprovar e concluir, devolver, cancelar, reabrir). Ações rápidas no cabeçalho: Abrir chamado, Ver Kanban, Ver relatórios (administrador). |
| Análise opcional | Abertos × concluídos por semana (12 semanas); ativos por plataforma; concluídos por desenvolvedor no mês (administrador); ativos por prioridade. Todos com tabela equivalente ("Ver tabela"), período no subtítulo e o recorte aplicado. |

### Regras de cálculo dos indicadores

| Indicador | Regra | Consulta correspondente |
| --- | --- | --- |
| Abertos | status = Aberto | `/chamados/?situacao=abertos` |
| Em andamento | status = Em andamento **ou** Em revisão | `/chamados/?situacao=em_andamento` |
| Atrasados | prazo anterior a hoje e status diferente de Concluído/Cancelado | `/chamados/?situacao=atrasados` |
| Concluídos no mês | status = Concluído e concluído entre o dia 1 do mês e hoje | `/chamados/?situacao=concluidos_mes` |
| Sem responsável (administrador) | sem responsável e status diferente de Concluído/Cancelado | `/chamados/?situacao=sem_responsavel` |

Percentual do relatório — **No prazo**: numerador = concluídos no período com conclusão até o prazo; denominador = concluídos no período que tinham prazo; denominador zero → "—".

## Aplicação nas demais telas (seção 6)

| Tela | Como ficou |
| --- | --- |
| Listagem (chamados, plataformas, usuários, notificações) | Cabeçalho com a ação principal, painel de filtros, filtros ativos com remoção individual (chamados), total, tabela com rolagem horizontal própria, paginação que preserva o recorte. |
| Detalhe do chamado | Trilha, identificação e selos de situação no cabeçalho, dados agrupados, linha do tempo, anexos, comentários e "Próximas ações" com a principal destacada. |
| Cadastro e edição | Campos agrupados na ordem de preenchimento, erros junto ao campo (`aria-describedby`), resumo no topo, valores preservados, "Cancelar" + ação principal. |
| Relatório | Período e recorte no cabeçalho, atalhos de período antes dos filtros, exportação Excel/PDF com o mesmo recorte e as mesmas permissões. |

## Critérios de aceite (seção 9)

| Verificação | Situação |
| --- | --- |
| Identidade entre sistemas | Mesma base do Naicas: Bootstrap 5.3, Bootstrap Icons, Lexend, tokens anil/urucum/ipê/folha (`static/css/secretaria.css`), barra anil, `cabecalho-pagina`, cards de indicador. A "fita" é assinatura só do Naicas e não foi usada. Comparação lado a lado com o Naicas em produção **(a confirmar)**. |
| Indicador e detalhamento | Testado: cada card bate com a listagem correspondente, com e sem recorte (`config/test_padrao_secretaria.py`). |
| Filtros e paginação | Testado: filtro inválido mostra erro no campo, preserva o valor e suspende os resultados; paginação preserva os filtros. |
| Permissão e contexto | Testado com administrador e desenvolvedor; URL direta fora do escopo continua bloqueada (403). |
| Ações e navegação | Links por `{% url %}`; mutações com POST e CSRF (teste com `enforce_csrf_checks=True`). |
| Estados e gráficos | Zero, consulta vazia, filtro inválido e falha de carga são distinguíveis; gráfico e tabela usam os mesmos dados. |
| Revisão no navegador | Telas conferidas em 375, 768 e 1440 px (Edge headless). Percurso completo só por teclado e teste em aparelho físico **(a fazer)**. |
| Telas internas | Listagem, detalhe e formulário abertos a partir do painel mantêm barra, contexto do perfil e cabeçalho. |
