# Diário de desenvolvimento — Plataforma Tasks (Chamados)

> Arquivo vivo: atualizar a cada mudança relevante (código, deploy, infraestrutura).
> **Nunca registrar senhas ou segredos aqui.** A senha da VPS é sempre pedida ao usuário.

## Infraestrutura

| Item | Valor |
|---|---|
| Repositório | https://github.com/rdssystems/plataforma-chamados (branch `master`) |
| VPS | ZimaOS v1.8.0 (ZimaCube), hostname `server-test` |
| Endereço da VPS (Tailscale) | `100.124.217.8` |
| Usuário SSH | `klismanrds` (tem `sudo`) |
| Senha | **não salva** — pedir ao usuário |
| Pasta do app na VPS | `/DATA/AppData/plataforma-chamados` |
| URL do app | http://100.124.217.8:8030 (só acessível dentro da rede Tailscale) |

### Particularidades da VPS
- Disco raiz (`/`) é somente-leitura/cheio por design do ZimaOS; dados e Docker ficam em `/DATA`.
- O usuário `klismanrds` não está no grupo `docker`: comandos Docker precisam de `sudo`.
- Portas **80/443 ocupadas** pelo gateway do ZimaOS → por isso o app usa `compose.vps.yaml` (porta 8030, HTTP).
- Outros apps na mesma VPS (não mexer sem combinar): `naicas-app` (127.0.0.1:8020, público via Funnel), `gerenciamento-web-1`, `nextcloud` (10081/10443), `tailscale`.
- **Tailscale Funnel** (desde 2026-11-13): https://servidor-test.taile3dafe.ts.net (porta 443) → Naicas. HTTPS e Funnel já estão habilitados na tailnet. Se a Plataforma de Chamados precisar de HTTPS público, usar as portas de Funnel **8443** ou **10000** (`sudo docker exec tailscale tailscale funnel --bg --https=8443 8030`), e então ajustar `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` e `SECURE_SSL=True`.
- O Naicas tem deploy automático (`naicas-update.timer`, a cada minuto, mantido pelo Isaque Miranda) e regras próprias no `CLAUDE.md` do repositório dele.
- Acesso é por HTTP dentro do Tailscale (tráfego já criptografado pelo WireGuard). Por isso `SECURE_SSL=False`.
- Não há `openssl` na VPS: gerar segredos com `head -c 48 /dev/urandom | od -An -tx1 | tr -d " \n"`.
- Containers do app: `db` (Postgres 16), `redis` (eventos em tempo real, sem persistência), `web` (Daphne, HTTP + WebSocket), `proxy` (Caddy, porta 8030).
- Backups manuais ficam em `/DATA/Backup/plataforma-chamados/`.

## Como fazer deploy / atualizar

Depois de dar `git push` das alterações:
```bash
ssh klismanrds@100.124.217.8
cd /DATA/AppData/plataforma-chamados
./atualizar.sh
```
O [atualizar.sh](atualizar.sh) mostra os commits que vão entrar, pergunta antes de aplicar, faz backup do banco em `/DATA/Backup/plataforma-chamados/`, baixa o código (`git pull` só fast-forward), reconstrói e reinicia os containers (migrações automáticas), espera o app ficar saudável, testa o login e limpa imagens antigas. Se algo falhar, mostra como voltar à versão anterior. Opções: `--sim` (não pergunta), `--forcar` (reconstrói mesmo sem commits novos), `--help`.

Se houver arquivos editados à mão na VPS, o script para sem descartar nada e mostra quais são.

Outros comandos úteis (todos a partir da pasta do app):
```bash
sudo docker compose -f compose.vps.yaml --env-file .env.production logs -f web
sudo docker compose -f compose.vps.yaml --env-file .env.production exec web python manage.py criar_admin
sudo docker compose -f compose.vps.yaml --env-file .env.production ps
```
**Nunca** usar `down -v` (apaga banco e anexos).

Backup do banco antes de deploys com migração:
```bash
sudo sh -c 'docker compose -f compose.vps.yaml --env-file .env.production exec -T db sh -c "pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Fc" > /DATA/Backup/plataforma-chamados/backup-$(date +%Y%m%d-%H%M%S).dump'
```

Pilha de teste isolada (não toca na produção; usar para validar mudanças antes do deploy):
```bash
# .env.teste com WEB_PORT=8031, CSRF_TRUSTED_ORIGINS=http://100.124.217.8:8031 e banco/senha próprios
sudo APP_ENV_FILE=.env.teste docker compose -p chamados-teste -f compose.vps.yaml --env-file .env.teste up -d --build
# ... testar em http://100.124.217.8:8031 ...
sudo APP_ENV_FILE=.env.teste docker compose -p chamados-teste -f compose.vps.yaml --env-file .env.teste down -v   # -p chamados-teste é obrigatório!
```

O `.env.production` fica só na VPS (ignorado pelo git); o modelo é `.env.vps.example`.

## Histórico

### 2026-11-13
- Containerização do app (Dockerfile, compose com Postgres + Caddy) — commit `2756090`.
- Acesso à VPS e diagnóstico: Docker 27.5.1 + Compose 2.32.4 (precisam de `sudo`), portas 80/443 ocupadas, repo já clonado em `/DATA/AppData/plataforma-chamados`.
- Adicionado `SECURE_SSL` em `config/settings.py` (padrão `True`; `False` desliga redirect HTTPS e cookies Secure para uso via Tailscale/HTTP).
- Criados `compose.vps.yaml`, `Caddyfile.vps` e `.env.vps.example` para deploy na VPS sem usar 80/443.
- **Deploy concluído**: containers `db`, `web`, `proxy` saudáveis; migrações aplicadas; login em http://100.124.217.8:8030/login/ responde 200. Usuário admin criado (`admin`, senha entregue ao usuário e a trocar no primeiro acesso).
- **Banco local migrado para a VPS** (dumpdata → loaddata no Postgres): 2 usuários (`admin`, `Isaque`), 1 plataforma, 2 chamados, 5 mudanças de status, 1 anexo, 3 notificações, 9 históricos; pasta `media` copiada para o volume `media_data`. O admin criado no deploy foi substituído pelo `admin` local (mesma senha do ambiente local). Histórico de chamados já apagados (361 linhas órfãs) não foi migrado.
- **Chat em tempo real** (app `chat`):
  - Conversas diretas entre dois usuários (uma por par), histórico permanente (FKs `PROTECT`, admin somente leitura, sem tela de apagar). Usuário desativado: histórico visível, envio bloqueado.
  - Página `/chat/` com abas **Conversas** e **Online**; botão **Online (N)** no topo de todas as páginas com a lista de usuários e o botão "Conversar"; contador de não lidas no menu; avisos (toasts) de mensagens novas.
  - Presença: cada aba abre um WebSocket (`/ws/app/`) e envia ping a cada 25 s; offline quando todas as abas fecham ou após 70 s sem sinal (modelo `Presenca`).
  - Notificações de chamados agora chegam em tempo real (signal em `notificacoes/signals.py`), atualizando sino e contador.
  - Infra: Gunicorn → Daphne (ASGI); novo container `redis`; `CHANNEL_LAYERS` usa Redis quando há `REDIS_URL`, senão memória (dev/testes).
  - Validação: 23 testes novos (69 no total, todos passando); teste ponta a ponta com dois usuários e WebSocket real numa pilha de teste isolada na VPS (porta 8031, depois removida); backup `antes-do-chat-20261113-134806.dump` feito antes do deploy; produção atualizada, migração `chat.0001` aplicada.

- **Deploy pelo Git + `atualizar.sh`**:
  - Push de todos os commits para o GitHub. O repositório é **público**; por decisão do usuário, o diário (IP do Tailscale e usuário SSH, sem senhas) foi publicado como está.
  - A pasta da VPS tinha arquivos enviados por SFTP. Conferi arquivo por arquivo (hash do Git) que só diferiam em fim de linha (CRLF) e alinhei com `git reset --hard origin/master`. A VPS agora segue o GitHub sem alterações locais.
  - Criado `atualizar.sh` (deploy guiado com backup, verificação de saúde e instruções de rollback) e `.gitattributes` (força LF em `.sh`, Dockerfile e Caddyfile).
  - `.dockerignore` passou a excluir `*.md`, `atualizar.sh`, compose e Caddyfile: commits só de documentação não geram imagem nova nem reiniciam o app.

### 2026-11-24
- Banco local (`db.sqlite3`) estava sem a migração do chat (`no such table: chat_participante` ao logar). Aplicado `migrate`; cópia anterior em `db-antes-chat-20261124-123628.sqlite3` (ignorada pelo git).
- **Gráficos do dashboard migrados de Chart.js para Apache ECharts 6.1.0** (CDN com versão fixa e SRI + tradução pt-BR), código em `static/js/dashboard_graficos.js` e card reutilizável em `templates/dashboard/partials/grafico_card.html`.
  - Formatos: linha (abertos × concluídos, 2 séries com legenda, rótulo no fim da linha e crosshair); barras horizontais ordenadas para plataformas e devs (cor única; a cor de cada plataforma vira um marcador ao lado do nome); prioridade em barras na ordem natural com rampa ordinal de um tom (mais escuro = mais urgente) no lugar da rosca.
  - Paleta validada com o validador de dataviz contra o fundo branco dos cards (separação para daltonismo e contraste). Botão "Ver tabela" em cada gráfico, estados de vazio/erro, descrição para leitores de tela, nomes de usuários escapados nos tooltips.
  - Corrigida a série semanal: antes as semanas eram ordenadas como texto `dd/mm` (quebrava na virada do mês) e semanas sem chamados sumiam; agora são sempre 12 semanas em ordem cronológica com zeros. O JSON ganhou `linha.datas` e perdeu `prioridades.cores`.
  - Validação: 4 testes novos; páginas renderizadas no Edge headless (desktop, celular a 390px, vazios, tooltips e tabelas) e conferidas visualmente.
  - Ajustes do padrão de dashboards (`front-rules.md`): tooltip pelo teclado (Tab foca o gráfico, setas/Home/End percorrem, Esc fecha), recorte do filtro de dev nos subtítulos e botão "Tentar de novo" em caso de falha. A adoção completa do design system (paleta Naicas, Lexend, Bootstrap) fica para a próxima tarefa.
- **Correção no chat:** a contagem de não lidas comparava horários, e no Windows o relógio do Python muda só a cada ~3 ms, então uma mensagem enviada logo após marcar como lida contava como lida (teste falhava em 5 de 8 rodadas). Agora a leitura é marcada pelo id da última mensagem lida (`Participante.ultima_lida_id`, migração `chat.0002` que converte o histórico). Aplicada no banco local (cópia em `db-antes-chat0002-*.sqlite3`).

- **Segurança — XSS armazenado corrigido** (commit `93462a4`): a linha do tempo do chamado usava `|safe` em títulos com nome de arquivo anexado e nomes de usuários. Um anexo chamado `<img src=x onerror=...>.png` executava JavaScript para quem abrisse o chamado. **Em produção até o próximo deploy.**
- **Design system da Secretaria aplicado** (padrão do `front-rules.md`, referência visual do Naicas):
  - Tailwind trocado por Bootstrap 5.3.3 + Bootstrap Icons 1.11.3 + Lexend, todos com versão fixa e SRI. Tokens do padrão (`--cor-primaria`, `--cor-critica`, ...) em `static/css/secretaria.css`.
  - Barra superior anil com módulos e contexto do perfil; abaixo de 992px, menu lateral (offcanvas) com fundo `inert` e foco gerenciado (`static/js/navegacao.js`, igual ao Naicas).
  - Todas as telas reescritas: `cabecalho-pagina`, `filtros-pagina`, cards de indicador, selos de status/prioridade com cor + ícone + texto, linha do tempo, kanban com modal de motivo (substitui `prompt()`), chat.
  - Dashboard na anatomia do padrão: cabeçalho com até 3 ações, índice lateral (≥1200px), indicadores com unidade/recorte/link, recorte, fila de trabalho, análise (ECharts em anil/folha, validado) e atividades.
  - Indicadores e listagem usam as mesmas regras (`chamados/consultas.py`); novo filtro `situacao` na listagem. Filtros validados em dashboard, listagem, kanban e relatório (`config/filtros.py`): entrada inválida mostra erro no campo, preserva o valor e suspende resultados (antes: erro 500). Paginação preserva os filtros (`{% querystring %}`).
  - Formulários com `config/formularios.py` (classes Bootstrap, `is-invalid`, `aria-describedby`) e `templates/partials/campo.html`.
  - Relatório: "No prazo" mostra numerador/denominador e "—" sem base; durações em português (`|duracao`); PDF com as cores do padrão.
  - Ficha de adoção (seção 8) e situação dos critérios de aceite (seção 9) em `docs/ficha-adocao-dashboard.md`.
  - Validação: 91 testes (15 novos de critérios de aceite em `config/test_padrao_secretaria.py`); telas conferidas em 375/768/1440 px no Edge headless; contraste WCAG ≥ 4,5:1 em todas as combinações de texto usadas.
- **PDF do relatório no design system:** faixa anil com período, recorte aplicado e quem gerou; cards de indicador com faixa de cor; tabelas no padrão das telas; marcador de cor das plataformas; durações em português; "No prazo" com numerador/denominador e "—" sem base; nota "Como os números são calculados"; rodapé com "Página X de Y". Fonte Lexend embutida (`static/fonts/lexend/*.ttf`, SIL OFL). O template tem um ramo por motor (`motor`): WeasyPrint (produção, com gradiente e cantos arredondados) e xhtml2pdf (fallback). Antes o PDF não dizia qual filtro tinha sido aplicado. Validado com o xhtml2pdf local e com o WeasyPrint 70 da imagem de produção, num container descartável na VPS.
- **Deploy na VPS (pelo GitHub + `./atualizar.sh`)**: produção foi de `5f5bd37` para `d0e35be` (ECharts, design system, PDF novo, correção do chat e do XSS). Backup antes: `/DATA/Backup/plataforma-chamados/antes-de-atualizar-20261124-142933.dump`. Migração `chat.0002` aplicada (2 de 2 marcadores de leitura convertidos). Conferido de fora: telas 200, filtro inválido sem erro 500, PDF gerado pelo WeasyPrint 70 com Lexend, WebSocket recusando conexão sem login (4401), dados intactos (2 usuários, 2 chamados, 7 mensagens). **O XSS da linha do tempo deixou de existir em produção.**
## Pendências / próximos passos
- [ ] Testar o chat e o novo visual no navegador e em aparelho físico (percurso completo por teclado incluído).
- [ ] Decidir se o `front-rules.md` (padrão da Secretaria) entra no repositório.
- [ ] Decidir se haverá domínio + HTTPS público (nesse caso usar o `compose.yaml` original).
- [ ] Rotina de backup do Postgres e dos anexos (volumes `postgres_data` e `media_data`).
