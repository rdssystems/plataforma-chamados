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
- Outros apps na mesma VPS (não mexer): `naicas-app` (8020), `gerenciamento-web-1`, `nextcloud` (10081/10443), `tailscale`.
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

## Pendências / próximos passos
- [ ] Testar o chat no navegador com dois usuários reais (interface não foi vista em navegador, só validada via HTTP/WebSocket).
- [ ] Decidir se haverá domínio + HTTPS público (nesse caso usar o `compose.yaml` original).
- [ ] Rotina de backup do Postgres e dos anexos (volumes `postgres_data` e `media_data`).
