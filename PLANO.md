# Plano de Desenvolvimento — Sistema de Gestão de Chamados

Este documento detalha o progresso e o planejamento de cada etapa do projeto conforme especificado em `SPEC.md`.

---

## Status Geral das Etapas

- [x] **Etapa 1 — Base, contas e permissões** (Concluída)
- [x] **Etapa 2 — Plataformas e chamados** (Concluída)
- [x] **Etapa 3 — Comentários, anexos, histórico e notificações** (Concluída)
- [ ] **Etapa 4 — Kanban** (Em andamento)
- [ ] **Etapa 5 — Dashboard**
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

## Detalhamento da Etapa 4 — Kanban

### Objetivos e Escopo:
1. **Visualização em Colunas por Status**:
   - Rota `/chamados/kanban/`.
   - 5 colunas correspondentes aos status: Aberto, Em andamento, Em revisão, Concluído, Cancelado.
   - Cada card exibe:
     - Código (ex: CH-0001) e link para o detalhe.
     - Título da demanda.
     - Badge da plataforma (com a cor hex customizada).
     - Badge de prioridade (urgente, alta, média, baixa).
     - Avatar ou iniciais do responsável.
     - Prazo em vermelho com alerta de atrasado caso esteja vencido.
2. **Arrastar e Soltar (Drag and Drop) com SortableJS**:
   - Integração do SortableJS via CDN (sem builds de JS).
   - Movimentação entre colunas dispara requisição assíncrona (via fetch/HTMX) chamando o mesmo serviço `mudar_status(chamado, novo_status, usuario, comentario)`.
   - Reordenação dentro da coluna salva em `ordem_kanban`.
3. **Tratamento de Transições Inválidas**:
   - Quando o usuário tentar arrastar para uma coluna não permitida (ou sem permissão do seu papel):
     - A transição é recusada pelo backend.
     - O card é retornado automaticamente para a coluna de origem.
     - Uma notificação/toast de erro é exibida com a mensagem exata da regra violada.
   - Para transições que exigem motivo obrigatório (ex: cancelamento, devolução, reabertura):
     - Exibição de modal/prompt solicitando o motivo obrigatório antes de efetivar ou confirmação controlada.
4. **Filtros do Kanban**:
   - Filtro por plataforma e filtro por responsável, preservando a experiência ágil.
5. **Permissões no Kanban**:
   - Admin vê todos os cards.
   - Dev vê apenas os cards aos quais tem acesso (atribuídos a ele ou criados por ele).
6. **Testes Automatizados**:
   - Endpoint de movimentação no Kanban chamando o serviço `mudar_status`.
   - Validação de atualização de `ordem_kanban`.
   - Recusa com erro 400 ou resposta de recusa quando a transição é inválida, mantendo o status original.



