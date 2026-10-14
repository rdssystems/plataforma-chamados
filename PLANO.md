# Plano de Desenvolvimento — Sistema de Gestão de Chamados

Este documento detalha o progresso e o planejamento de cada etapa do projeto conforme especificado em `SPEC.md`.

---

## Status Geral das Etapas

- [x] **Etapa 1 — Base, contas e permissões** (Concluída)
- [x] **Etapa 2 — Plataformas e chamados** (Concluída)
- [ ] **Etapa 3 — Comentários, anexos, histórico e notificações** (Em andamento)
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

## Detalhamento da Etapa 3 — Comentários, anexos, histórico e notificações

### Objetivos e Escopo:
1. **Modelos**:
   - `Comentario` (`chamados`):
     - `chamado`: FK Chamado (CASCADE)
     - `autor`: FK Usuario (PROTECT)
     - `texto`: TextField
     - `criado_em`: DateTimeField (auto_now_add=True)
   - `Anexo` (`chamados`):
     - `chamado`: FK Chamado (CASCADE)
     - `arquivo`: FileField(upload_to='anexos/%Y/%m/') com validação de limite de 10 MB por arquivo
     - `nome_original`: CharField(255)
     - `enviado_por`: FK Usuario (PROTECT)
     - `enviado_em`: DateTimeField (auto_now_add=True)
   - `Notificacao` (`notificacoes`):
     - `destinatario`: FK Usuario (CASCADE/PROTECT)
     - `chamado`: FK Chamado (CASCADE)
     - `mensagem`: CharField(255)
     - `lida`: BooleanField (default False)
     - `criada_em`: DateTimeField (auto_now_add=True)
2. **Comentários via HTMX no detalhe do chamado**:
   - Adição assíncrona de comentários sem recarregar a página.
   - Listagem ordenada e exibição com avatar e data legível.
3. **Upload e Download Seguro de Anexos**:
   - Upload de anexos no detalhe do chamado com validação estrita de tamanho (máximo 10 MB).
   - Rota de download protegida: apenas usuários com permissão de visualização do chamado correspondente (Admin ou Dev criador/responsável) podem baixar o arquivo (HTTP 403 para não autorizados).
4. **Linha do Tempo Unificada no Detalhe**:
   - Combinação de histórico (`HistoricalChamado`), mudanças de status (`MudancaStatus`) e comentários (`Comentario`), ordenados cronologicamente.
5. **Notificações Internas e Contador no Sino**:
   - Disparo automático de notificação ao responsável quando:
     - Chamado é atribuído ao dev.
     - Chamado recebe um novo comentário.
     - Status do chamado é alterado.
   - Sino no topo da interface com contador de mensagens não lidas.
   - Tela de notificações (`/notificacoes/`) com listagem e ação HTMX de marcar como lida / marcar todas como lidas.
6. **Testes Automatizados**:
   - Inclusão de comentários via HTMX/POST e permissão.
   - Validação de limite de 10 MB no anexo.
   - Restrição de download de anexo para usuários não autorizados.
   - Criação de notificações e atualização do contador de não lidas.


