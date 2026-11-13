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

## Como fazer deploy / atualizar

```bash
ssh klismanrds@100.124.217.8
cd /DATA/AppData/plataforma-chamados
git pull
sudo docker compose -f compose.vps.yaml --env-file .env.production up -d --build
```

Outros comandos úteis (todos a partir da pasta do app):
```bash
sudo docker compose -f compose.vps.yaml --env-file .env.production logs -f web
sudo docker compose -f compose.vps.yaml --env-file .env.production exec web python manage.py criar_admin
sudo docker compose -f compose.vps.yaml --env-file .env.production ps
```
**Nunca** usar `down -v` (apaga banco e anexos).

O `.env.production` fica só na VPS (ignorado pelo git); o modelo é `.env.vps.example`.

## Histórico

### 2026-11-13
- Containerização do app (Dockerfile, compose com Postgres + Caddy) — commit `2756090`.
- Acesso à VPS e diagnóstico: Docker 27.5.1 + Compose 2.32.4 (precisam de `sudo`), portas 80/443 ocupadas, repo já clonado em `/DATA/AppData/plataforma-chamados`.
- Adicionado `SECURE_SSL` em `config/settings.py` (padrão `True`; `False` desliga redirect HTTPS e cookies Secure para uso via Tailscale/HTTP).
- Criados `compose.vps.yaml`, `Caddyfile.vps` e `.env.vps.example` para deploy na VPS sem usar 80/443.
- **Deploy concluído**: containers `db`, `web`, `proxy` saudáveis; migrações aplicadas; login em http://100.124.217.8:8030/login/ responde 200. Usuário admin criado (`admin`, senha entregue ao usuário e a trocar no primeiro acesso).

## Pendências / próximos passos
- [ ] Trocar a senha do `admin` no primeiro acesso.
- [ ] Dar `git push` do commit local (arquivos de deploy foram copiados à VPS por SFTP; se o `git pull` na VPS acusar conflito, rodar `git checkout -- .` antes).
- [ ] Decidir se haverá domínio + HTTPS público (nesse caso usar o `compose.yaml` original).
- [ ] Rotina de backup do Postgres e dos anexos (volumes `postgres_data` e `media_data`).
- [ ] Migrar dados do `db.sqlite3` local, se necessário.
