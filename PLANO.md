# Plano de Desenvolvimento — Sistema de Gestão de Chamados

Este documento detalha o progresso e o planejamento de cada etapa do projeto conforme especificado em `SPEC.md`.

---

## Status Geral das Etapas

- [x] **Etapa 1 — Base, contas e permissões** (Concluída)
- [x] **Etapa 2 — Plataformas e chamados** (Concluída)
- [x] **Etapa 3 — Comentários, anexos, histórico e notificações** (Concluída)
- [x] **Etapa 4 — Kanban** (Concluída)
- [x] **Etapa 5 — Dashboard** (Concluída)
- [x] **Etapa 6 — Relatórios** (Concluída)
- [ ] **Extra — Dados de demonstração** (Em andamento)

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

## Conclusão da Etapa 6 — Relatórios

### Critérios de Aceite da Etapa 6:
- [x] Tela com filtros e todas as métricas da seção Relatórios.
- [x] Exportação Excel e PDF com os mesmos números da tela.
- [x] Testes do serviço de relatórios com dados de exemplo e resultados conhecidos.
- [x] Todos os 44 testes passando no pytest.

---

## Detalhamento do Extra — Dados de demonstração

### Objetivos e Escopo:
1. **Comando de Gerenciamento `popular_demo`**:
   - Local: `chamados/management/commands/popular_demo.py`
   - Cria:
     - 3 plataformas (ex: Portal Web, App Mobile, API Financeira) com cores hexadecimais distintas.
     - 1 admin gestor (ex: `gestor`, senha `gestor123`, `papel='admin'`, `deve_trocar_senha=False`).
     - 3 devs (ex: `dev_lucas`, `dev_mariana`, `dev_carlos`, senha `dev123`, `papel='dev'`, `deve_trocar_senha=False`).
     - Cerca de 60 chamados realistas espalhados ao longo dos últimos 3 meses:
       - Variedade de tipos (bug, melhoria, nova funcionalidade, suporte).
       - Variedade de prioridades (urgente, alta, média, baixa).
       - Variedade de status (abertos, em andamento, em revisão, concluídos, cancelados).
       - Prazos realistas (alguns vencidos para testar atrasados, alguns futuros, alguns sem prazo).
       - `iniciado_em` e `concluido_em` consistentes com os status.
       - Histórico de `MudancaStatus` e comentários para simular atividade real.
### Critérios de Aceite Concluídos:
- [x] Comando `popular_demo` implementado em `chamados/management/commands/popular_demo.py`.
- [x] Criação de 3 plataformas com cores hexadecimais distintas.
- [x] Criação de 1 gestor admin (`gestor` / `gestor123`) e 3 desenvolvedores (`dev_lucas`, `dev_mariana`, `dev_carlos` / `dev123`).
- [x] Geração de 60 chamados distribuídos nos últimos 3 meses com histórico de status e comentários.
- [x] Suporte à flag `--limpar`.
- [x] Testes automatizados cobrindo os comandos em `chamados/tests/test_commands.py`.
- [x] Todos os 46 testes passando com sucesso no pytest.
