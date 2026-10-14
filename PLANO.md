# Plano de Desenvolvimento — Sistema de Gestão de Chamados

Este documento detalha o progresso e o planejamento de cada etapa do projeto conforme especificado em `SPEC.md`.

---

## Status Geral das Etapas

- [x] **Etapa 1 — Base, contas e permissões** (Concluída)
- [x] **Etapa 2 — Plataformas e chamados** (Concluída)
- [x] **Etapa 3 — Comentários, anexos, histórico e notificações** (Concluída)
- [x] **Etapa 4 — Kanban** (Concluída)
- [x] **Etapa 5 — Dashboard** (Concluída)
- [ ] **Etapa 6 — Relatórios** (Em andamento)
- [ ] **Extra — Dados de demonstração**

---

## Conclusão da Etapa 1 — Base, contas e permissões

### Critérios de Aceite da Etapa 1:
- [x] Projeto Django criado com a estrutura de apps, .env, requirements.txt e .gitignore.
- [x] Usuário customizado com papel e deve_trocar_senha; comando criar_admin para o primeiro admin.
- [x] Login, logout e troca de senha; quem tem deve_trocar_senha é redirecionado até trocar.
- [x] Tela de usuários (só admin): criar com senha provisória, editar, desativar, redefinir senha.
- [x] Layout base com barra lateral, topo e menu conforme o papel.
- [x] Dev que acessa uma rota de admin recebe 403.
- [x] Todos os 12 testes passando no pytest.

---

## Conclusão da Etapa 2 — Plataformas e chamados

### Critérios de Aceite da Etapa 2:
- [x] CRUD de plataformas (só admin).
- [x] Criar, editar e ver chamado; código CH-0001 gerado sem repetir.
- [x] Atribuição de responsável e regras de permissão da tabela de papéis.
- [x] Transições de status validadas num único serviço (chamados/services.py); transição inválida é recusada.
- [x] iniciado_em, concluido_em e MudancaStatus gravados nas transições.
- [x] Lista com busca, filtros e paginação; dev vê só o que pode ver.
- [x] Todos os 25 testes passando no pytest.

---

## Conclusão da Etapa 3 — Comentários, anexos, histórico e notificações

### Critérios de Aceite da Etapa 3:
- [x] Comentários via HTMX no detalhe do chamado.
- [x] Upload de anexos com limite de 10 MB e download só para quem vê o chamado.
- [x] Linha do tempo no detalhe juntando histórico, mudanças de status e comentários.
- [x] Notificação ao responsável quando o chamado é atribuído, comentado ou muda de status; sino com contador de não lidas.
- [x] Todos os 32 testes passando no pytest.

---

## Conclusão da Etapa 4 — Kanban

### Critérios de Aceite da Etapa 4:
- [x] Uma coluna por status; arrastar entre colunas chama o mesmo serviço de transição.
- [x] Arraste recusado volta o card para a coluna original e mostra a mensagem.
- [x] Ordem dentro da coluna salva em ordem_kanban.
- [x] Filtros de plataforma e responsável.
- [x] Todos os 35 testes passando no pytest.

---

## Conclusão da Etapa 5 — Dashboard

### Critérios de Aceite da Etapa 5:
- [x] Cards, gráficos e listas da seção Dashboard.
- [x] Dev vê só os próprios números.
- [x] Consultas agregadas no banco; página carrega com até 15 queries (executou em 8 queries).
- [x] Todos os 39 testes passando no pytest.

---

## Detalhamento da Etapa 6 — Relatórios

### Objetivos e Escopo:
1. **Serviço Centralizado de Métricas (`relatorios/services.py`)**:
   - Módulo único que calcula todas as métricas do período para a tela e para as exportações:
     - **Chamados abertos**: `criado_em` dentro do período.
     - **Chamados concluídos**: `concluido_em` dentro do período.
     - **Tempo médio de resolução**: média de `concluido_em − criado_em` dos concluídos.
     - **Entregues no prazo**: % dos concluídos com `concluido_em <= prazo` (considerando apenas os que têm prazo).
     - **Atrasados no fim do período**: `prazo < fim do período` e não concluídos até ele.
     - **Backlog**: não finais na data de fim do período.
     - **Quebras**:
       - Tabela por dev: concluídos, tempo médio, % no prazo.
       - Tabela por plataforma: abertos, concluídos, ativos.
       - Distribuição por tipo e prioridade.
     - **Lista detalhada**: todos os chamados concluídos no período, com código, título, plataforma, responsável, datas e tempo de resolução.
2. **Tela de Relatórios (`/relatorios/`)**:
   - Apenas Admin acessa (`AdminRequiredMixin`).
   - Filtros:
     - Atalhos de período: "Esta semana", "Semana passada", "Este mês", "Mês passado", ou intervalo personalizado (`data_inicio`, `data_fim`).
     - Dev, plataforma, tipo e prioridade.
   - Exibição na tela dos indicadores consolidados, tabelas de quebras e lista detalhada.
   - Botões para exportar em Excel e PDF.
3. **Exportação Excel (`openpyxl`)**:
   - Arquivo `.xlsx`:
     - Aba 1: Resumo Executivo (indicadores e quebras gerais).
     - Aba 2: Desempenho por Dev.
     - Aba 3: Desempenho por Plataforma.
     - Aba 4: Lista Detalhada de Chamados.
   - Formatação profissional de cabeçalhos e colunas.
   - Nome do arquivo: `relatorio_chamados_AAAA-MM-DD_AAAA-MM-DD.xlsx`.
4. **Exportação PDF (`WeasyPrint` com fallback HTML/PDF se GTK não disponível no Windows)**:
   - Template HTML específico para impressão e geração de PDF (`templates/relatorios/pdf.html`).
   - Nome do arquivo: `relatorio_chamados_AAAA-MM-DD_AAAA-MM-DD.pdf`.
5. **Testes Automatizados**:
   - Teste do serviço `relatorios/services.py` com dados de exemplo e resultados conhecidos calculados manualmente.
   - Teste de exportação Excel (geração válida de workbook openpyxl com as abas e dados corretos).
   - Teste de exportação PDF e permissões de acesso (Dev recebe 403).





