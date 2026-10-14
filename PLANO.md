# Plano de Desenvolvimento — Sistema de Gestão de Chamados

Este documento detalha o progresso e o planejamento de cada etapa do projeto conforme especificado em `SPEC.md`.

---

## Status Geral das Etapas

- [x] **Etapa 1 — Base, contas e permissões** (Concluída)
- [ ] **Etapa 2 — Plataformas e chamados** (Em andamento)
- [ ] **Etapa 3 — Comentários, anexos, histórico e notificações**
- [ ] **Etapa 4 — Kanban**
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

## Detalhamento da Etapa 2 — Plataformas e chamados

### Objetivos e Escopo:
1. **App Plataformas (`plataformas`)**:
   - Modelo `Plataforma`:
     - `nome` (CharField 100, único)
     - `descricao` (TextField, opcional)
     - `url` (URLField, opcional)
     - `cor` (CharField 7, hexadecimal para badges e gráficos)
     - `ativa` (BooleanField, default True)
   - CRUD de Plataformas:
     - Protegido por `AdminRequiredMixin` (só admin acessa).
     - Lista, criação, edição e desativação/ativação (soft delete).
     - Formulário com seletor de cor hexadecimal.
2. **App Chamados (`chamados`)**:
   - Modelo `Chamado`:
     - `codigo`: gerado automaticamente sequencial no formato `CH-0001` (sem repetições).
     - `titulo`: CharField 200 obrigatório.
     - `descricao`: TextField obrigatório.
     - `plataforma`: FK Plataforma (on_delete=PROTECT).
     - `tipo`: CharField choices (`bug`, `melhoria`, `nova_funcionalidade`, `suporte`).
     - `prioridade`: CharField choices (`baixa`, `media`, `alta`, `urgente`).
     - `status`: CharField choices (`aberto`, `em_andamento`, `em_revisao`, `concluido`, `cancelado`).
     - `criado_por`: FK Usuario (on_delete=PROTECT).
     - `responsavel`: FK Usuario (null=True, blank=True).
     - `prazo`: DateField (opcional).
     - `criado_em`: DateTimeField (auto_now_add=True).
     - `atualizado_em`: DateTimeField (auto_now=True).
     - `iniciado_em`: DateTimeField (null=True, blank=True, preenchido na primeira transição para `em_andamento`).
     - `concluido_em`: DateTimeField (null=True, blank=True, preenchido ao entrar em `concluido`, limpo ao reabrir).
     - `ordem_kanban`: PositiveIntegerField (default 0).
     - `history`: HistoricalRecords (django-simple-history).
     - Índices de banco: `(status)`, `(responsavel, status)`, `(plataforma)`, `(criado_em)`, `(concluido_em)`.
     - Propriedades: `esta_atrasado` e `tempo_resolucao`.
   - Modelo `MudancaStatus`:
     - `chamado`: FK Chamado.
     - `de_status`: CharField.
     - `para_status`: CharField.
     - `alterado_por`: FK Usuario.
     - `alterado_em`: DateTimeField (auto_now_add=True).
     - `comentario_motivo`: TextField (opcional, obrigatório em certas transições como cancelamento ou devolução).
3. **Serviço Centralizado de Transições (`chamados/services.py`)**:
   - Função única: `mudar_status(chamado, novo_status, usuario, comentario=None)`.
   - Validações estritas da tabela do `SPEC.md`:
     - De Aberto para Em andamento: Responsável ou Admin, precisa ter responsável definido.
     - De Em andamento para Em revisão: Responsável ou Admin.
     - De Em revisão para Concluído: Admin.
     - De Em revisão para Em andamento: Admin, comentário obrigatório com motivo.
     - De Concluído para Em andamento: Admin, comentário obrigatório, limpa `concluido_em`.
     - De Aberto/Em andamento/Em revisão para Cancelado: Admin, comentário obrigatório.
   - Atualiza `iniciado_em` na primeira vez em que entrar em `em_andamento`.
   - Atualiza `concluido_em` ao entrar em `concluido`, e limpa se for reaberto para `em_andamento`.
   - Registra o histórico em `MudancaStatus`.
   - Recusa com exceção `ValidationError` ou regra de negócio qualquer transição fora da tabela ou sem autorização do papel.
4. **Regras de Permissão e Visualização**:
   - Admin vê todos os chamados. Dev vê somente os atribuídos a ele ou criados por ele.
   - Dev pode criar chamados (fica sem responsável até o admin atribuir).
   - Dev NÃO pode atribuir responsável, nem alterar prioridade ou prazo.
   - Chamado Concluído ou Cancelado não aceita edição de campos.
5. **Views e Telas**:
   - Plataformas: `/plataformas/`, `/plataformas/novo/`, `/plataformas/<id>/editar/`.
   - Chamados:
     - Lista: `/chamados/` (busca por código ou título, filtros por status, prioridade, plataforma, responsável, tipo, período; paginação; select_related).
     - Novo: `/chamados/novo/` (campos adaptados se for Dev ou Admin).
     - Editar: `/chamados/<id>/editar/` (Admin apenas; bloqueado se concluído/cancelado).
     - Detalhe: `/chamados/<id>/` (informações completas, ações de transição rápida).
6. **Testes Automatizados**:
   - CRUD de Plataformas.
   - Criação e numeração sequencial de código `CH-0001`, `CH-0002`...
   - Permissões de visualização (Dev só vê os seus ou criados por ele; Admin vê todos).
   - Transições de status válidas e recusa de inválidas.
   - Validação de preenchimento de `iniciado_em`, `concluido_em` e limpeza na reabertura.
   - Registro de `MudancaStatus`.

