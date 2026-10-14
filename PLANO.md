# Plano de Desenvolvimento — Sistema de Gestão de Chamados

Este documento detalha o progresso e o planejamento de cada etapa do projeto conforme especificado em `SPEC.md`.

---

## Status Geral das Etapas

- [x] **Etapa 1 — Base, contas e permissões** (Concluída)
- [x] **Etapa 2 — Plataformas e chamados** (Concluída)
- [x] **Etapa 3 — Comentários, anexos, histórico e notificações** (Concluída)
- [x] **Etapa 4 — Kanban** (Concluída)
- [ ] **Etapa 5 — Dashboard** (Em andamento)
- [ ] **Etapa 6 — Relatórios**
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

## Detalhamento da Etapa 5 — Dashboard

### Objetivos e Escopo:
1. **Cards de Indicadores (Topo)**:
   - Abertos (status Aberto)
   - Em andamento (Em andamento + Em revisão)
   - Atrasados (prazo vencido e status não final), com destaque visual em vermelho
   - Concluídos no mês corrente (concluido_em no mês atual)
   - Sem responsável (apenas admin vê este indicador)
2. **Gráficos com Chart.js**:
   - Dados servidos via view especializada retornando JSON (`/dashboard/dados-graficos/`):
     - Linha: chamados abertos × concluídos por semana nas últimas 12 semanas (com `TruncWeek` e agregações no banco, sem laços em Python).
     - Barras: chamados ativos por plataforma, utilizando a cor cadastrada de cada plataforma.
     - Barras: chamados concluídos por dev no mês corrente (exibido apenas para Admin).
     - Rosca (Doughnut): distribuição de chamados ativos por prioridade (urgente, alta, média, baixa).
3. **Listas Rápidas no Dashboard**:
   - Atrasados, ordenados pelo prazo mais antigo.
   - Vencendo nos próximos 3 dias (prazo entre hoje e hoje + 3 dias).
   - Últimas 10 atividades (mudanças de status e comentários recentes).
4. **Regras de Visualização por Papel**:
   - Admin vê os números gerais da equipe e filtro por dev.
   - Dev vê a mesma tela filtrada estritamente pelos próprios chamados (atribuídos a ele ou criados por ele).
5. **Otimização de Consultas**:
   - Consultas agregadas diretamente no banco de dados (`aggregate`, `annotate`, `TruncWeek`, `Count`, `Q`).
   - Carregamento com até 15 queries (usando `assertNumQueries` nos testes).
6. **Testes Automatizados**:
   - Verificação dos cálculos dos 5 cards com dados controlados.
   - Verificação de isolamento do Dev (vê apenas seus números).
   - Verificação da view JSON de gráficos com consultas agregadas.
   - Teste de limite de consultas SQL (<= 15 queries).




