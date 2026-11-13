#!/usr/bin/env bash
# =============================================================================
#  atualizar.sh - atualiza a Plataforma de Chamados na VPS (ZimaOS)
# =============================================================================
#
#  O que este script faz, em ordem:
#    1. Confere se está tudo no lugar (pasta do app, .env.production, git, docker).
#    2. Busca as novidades no GitHub e mostra quais commits vão entrar.
#    3. Faz backup do banco PostgreSQL antes de mexer em qualquer coisa.
#    4. Baixa o código novo (equivalente a "git pull").
#    5. Reconstrói a imagem e reinicia os containers. As migrações do banco
#       rodam sozinhas quando o container "web" sobe.
#    6. Espera o app ficar saudável e testa se a tela de login responde.
#    7. Remove imagens antigas deste app que ficaram sem uso.
#
#  Como usar (na VPS):
#      cd /DATA/AppData/plataforma-chamados
#      ./atualizar.sh             # mostra o que vai entrar e pergunta antes de aplicar
#      ./atualizar.sh --sim       # não pergunta (útil para automação)
#      ./atualizar.sh --forcar    # reconstrói e reinicia mesmo sem commits novos
#
#  O Docker desta VPS exige root: o script chama "sudo" sozinho quando precisa,
#  e o sudo pede a senha do seu usuário. Também funciona com "sudo ./atualizar.sh".
#
#  Se algo der errado, nada é apagado: o backup do banco fica em
#  /DATA/Backup/plataforma-chamados/ e o script mostra como voltar à versão anterior.
#
#  Nunca rode "docker compose down -v" neste app: o "-v" apaga o banco e os anexos.
# =============================================================================

set -Eeuo pipefail

# Todo o script fica dentro de main(). O bash lê a função inteira antes de
# executá-la, então o "git pull" pode trocar este arquivo sem atrapalhar a execução.
main() {
    # --- Configuração ---------------------------------------------------------
    PASTA_APP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    ARQUIVO_COMPOSE="compose.vps.yaml"
    ARQUIVO_ENV=".env.production"
    BRANCH="master"
    PROJETO="plataforma-chamados"          # nome do projeto no compose.vps.yaml
    PASTA_BACKUP="/DATA/Backup/plataforma-chamados"
    ENDERECO_VPS="100.124.217.8"           # IP da VPS na rede Tailscale

    configurar_cores
    PERGUNTAR=1
    FORCAR=0
    for arg in "$@"; do
        case "$arg" in
            --sim)      PERGUNTAR=0 ;;
            --forcar)   FORCAR=1 ;;
            -h|--help)  sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,2\}//'; return 0 ;;
            *)          erro "Opção desconhecida: $arg (use --help)"; exit 1 ;;
        esac
    done

    cd "$PASTA_APP"

    # Docker precisa de root nesta VPS. Já o git deve rodar como o dono da pasta,
    # para os arquivos baixados não ficarem pertencendo ao root.
    if [ "$(id -u)" -eq 0 ]; then
        DOCKER=(docker)
        if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
            GIT=(sudo -u "$SUDO_USER" git)
        else
            GIT=(git -c "safe.directory=$PASTA_APP")
        fi
    else
        DOCKER=(sudo docker)
        GIT=(git)
    fi

    ETAPA="início"
    BACKUP_FEITO=""
    COMMIT_ANTES=""
    trap 'falhou' ERR

    # =========================================================================
    etapa 1 "Conferindo o ambiente"
    # =========================================================================
    [ -f "$ARQUIVO_COMPOSE" ] || { erro "Não achei $ARQUIVO_COMPOSE em $PASTA_APP."; exit 1; }
    [ -f "$ARQUIVO_ENV" ] || { erro "Não achei $ARQUIVO_ENV. Crie a partir de .env.vps.example (veja DESENVOLVIMENTO.md)."; exit 1; }
    command -v git >/dev/null || { erro "git não está instalado."; exit 1; }
    "${DOCKER[@]}" compose version >/dev/null || { erro "docker compose não respondeu."; exit 1; }

    PORTA="$(grep -E '^WEB_PORT=' "$ARQUIVO_ENV" | cut -d= -f2 | tr -d '[:space:]' || true)"
    PORTA="${PORTA:-8030}"
    ok "Pasta: $PASTA_APP"
    ok "Arquivos $ARQUIVO_COMPOSE e $ARQUIVO_ENV encontrados; app publicado na porta $PORTA."

    # Alterações feitas à mão na VPS seriam sobrescritas (ou travariam o pull).
    # Em vez de descartá-las, o script para e mostra quais são.
    ALTERADOS="$("${GIT[@]}" status --porcelain --untracked-files=no)"
    if [ -n "$ALTERADOS" ]; then
        erro "Há arquivos alterados diretamente na VPS:"
        printf '%s\n' "$ALTERADOS" >&2
        info "Veja as diferenças com: git diff"
        info "Se puderem ser descartadas: git checkout -- .   (e rode este script de novo)"
        exit 1
    fi
    ok "Nenhuma alteração local pendente."

    # =========================================================================
    etapa 2 "Buscando novidades no GitHub"
    # =========================================================================
    "${GIT[@]}" fetch --quiet origin "$BRANCH"
    COMMIT_ANTES="$("${GIT[@]}" rev-parse --short HEAD)"
    COMMIT_REMOTO="$("${GIT[@]}" rev-parse --short "origin/$BRANCH")"
    info "Versão atual na VPS: $COMMIT_ANTES    Versão no GitHub: $COMMIT_REMOTO"

    if ! "${GIT[@]}" merge-base --is-ancestor HEAD "origin/$BRANCH"; then
        erro "A VPS tem commits que não estão no GitHub (histórico divergente)."
        info "Confira com: git log --oneline origin/$BRANCH..HEAD"
        exit 1
    fi

    NOVOS="$("${GIT[@]}" log --oneline --no-decorate "HEAD..origin/$BRANCH")"
    if [ -z "$NOVOS" ]; then
        if [ "$FORCAR" -eq 0 ]; then
            ok "A VPS já está na versão mais recente. Nada a fazer."
            info "Para reconstruir e reiniciar mesmo assim: ./atualizar.sh --forcar"
            return 0
        fi
        aviso "Nenhum commit novo, mas --forcar foi usado: vou reconstruir e reiniciar."
    else
        info "Commits que vão entrar:"
        printf '%s\n' "$NOVOS" | sed 's/^/      /'
        if "${GIT[@]}" diff --name-only "HEAD..origin/$BRANCH" | grep -q '/migrations/'; then
            aviso "Esta atualização traz migrações de banco (serão aplicadas automaticamente)."
        fi
    fi

    if [ "$PERGUNTAR" -eq 1 ] && [ -t 0 ]; then
        printf '\n'
        read -r -p "   Aplicar a atualização? [s/N] " resposta || resposta=""
        case "$resposta" in
            s|S|sim|SIM) ;;
            *) info "Cancelado. Nada foi alterado."; return 0 ;;
        esac
    fi

    # =========================================================================
    etapa 3 "Fazendo backup do banco de dados"
    # =========================================================================
    # pg_dump roda dentro do container do Postgres; o arquivo (formato custom,
    # restaurável com pg_restore) é gravado na VPS, fora do Docker.
    if [ -n "$(compose ps --status running -q db)" ]; then
        # Pede a senha do sudo agora, para ela não ser pedida no meio do pipe abaixo.
        [ "$(id -u)" -eq 0 ] || sudo -v
        sudo_se_preciso mkdir -p "$PASTA_BACKUP"
        BACKUP="$PASTA_BACKUP/antes-de-atualizar-$(date +%Y%m%d-%H%M%S).dump"
        compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
            | sudo_se_preciso tee "$BACKUP" >/dev/null
        sudo_se_preciso chmod 600 "$BACKUP"
        # Confere se o arquivo é um backup válido lendo o índice dele.
        TABELAS="$(sudo_se_preciso cat "$BACKUP" | compose exec -T db pg_restore -l | grep -c 'TABLE DATA' || true)"
        [ "${TABELAS:-0}" -gt 0 ] || { erro "O backup parece vazio ou inválido: $BACKUP"; exit 1; }
        BACKUP_FEITO="$BACKUP"
        ok "Backup salvo: $BACKUP ($TABELAS tabelas, $(sudo_se_preciso du -h "$BACKUP" | cut -f1))"
    else
        aviso "O banco não está rodando (primeira instalação?). Backup pulado."
    fi

    # =========================================================================
    etapa 4 "Baixando o código novo"
    # =========================================================================
    # Avança só se for "fast-forward": nunca cria merge nem descarta nada.
    if [ -n "$NOVOS" ]; then
        "${GIT[@]}" merge --ff-only --quiet "origin/$BRANCH"
        ok "Código atualizado: $COMMIT_ANTES -> $("${GIT[@]}" rev-parse --short HEAD)"
    else
        ok "Código já estava atualizado."
    fi

    # =========================================================================
    etapa 5 "Reconstruindo a imagem e reiniciando os containers"
    # =========================================================================
    # Só os serviços que mudaram são recriados. O banco e os anexos ficam em
    # volumes do Docker e não são afetados. Ao subir, o container "web" roda
    # as migrações e o collectstatic antes de começar a atender.
    INICIO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    compose build web
    compose up -d --remove-orphans
    ok "Containers iniciados."

    # =========================================================================
    etapa 6 "Conferindo se o app está saudável"
    # =========================================================================
    ID_WEB="$(compose ps -q web)"
    for _ in {1..40}; do
        SAUDE="$("${DOCKER[@]}" inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$ID_WEB")"
        [ "$SAUDE" = "healthy" ] && break
        sleep 3
    done
    if [ "$SAUDE" != "healthy" ]; then
        erro "O container web não ficou saudável (estado: $SAUDE). Últimas linhas do log:"
        compose logs --tail 40 web >&2
        false
    fi
    ok "Container web saudável."

    MIGRACOES="$(compose logs --no-log-prefix --since "$INICIO" web 2>/dev/null | grep -E '^ *Applying ' || true)"
    if [ -n "$MIGRACOES" ]; then
        info "Migrações aplicadas:"
        printf '%s\n' "$MIGRACOES" | sed 's/^ */      /'
    else
        info "Nenhuma migração nova."
    fi

    CODIGO="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORTA/login/" || true)"
    if [ "$CODIGO" != "200" ]; then
        erro "A tela de login respondeu HTTP $CODIGO (esperado 200)."
        compose logs --tail 40 web proxy >&2
        false
    fi
    ok "Tela de login respondendo (HTTP 200)."
    compose ps --format '{{.Service}}: {{.Status}}' | sed 's/^/      /'

    # =========================================================================
    etapa 7 "Limpando imagens antigas deste app"
    # =========================================================================
    # Remove só imagens sem uso que foram geradas por builds anteriores deste
    # projeto. Imagens de outros apps da VPS não são tocadas.
    "${DOCKER[@]}" image prune -f --filter "label=com.docker.compose.project=$PROJETO" >/dev/null
    ok "Limpeza concluída."

    trap - ERR
    printf '\n%s✔ Atualização concluída!%s\n' "$VERDE$NEGRITO" "$NORMAL"
    printf '   Versão: %s -> %s\n' "$COMMIT_ANTES" "$("${GIT[@]}" rev-parse --short HEAD)"
    [ -n "$BACKUP_FEITO" ] && printf '   Backup: %s\n' "$BACKUP_FEITO"
    printf '   Acesse: http://%s:%s\n\n' "$ENDERECO_VPS" "$PORTA"
}

# --- Funções auxiliares --------------------------------------------------------

compose() {
    "${DOCKER[@]}" compose -f "$ARQUIVO_COMPOSE" --env-file "$ARQUIVO_ENV" "$@"
}

# Executa como root quando o script não está rodando como root (ex.: gravar em /DATA/Backup).
sudo_se_preciso() {
    if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi
}

configurar_cores() {
    if [ -t 1 ]; then
        NEGRITO=$'\e[1m'; VERDE=$'\e[32m'; AMARELO=$'\e[33m'; VERMELHO=$'\e[31m'; AZUL=$'\e[36m'; NORMAL=$'\e[0m'
    else
        NEGRITO=''; VERDE=''; AMARELO=''; VERMELHO=''; AZUL=''; NORMAL=''
    fi
}

etapa() { ETAPA="$1. $2"; printf '\n%s[%s/7] %s%s\n' "$NEGRITO$AZUL" "$1" "$2" "$NORMAL"; }
ok()    { printf '   %s✔%s %s\n' "$VERDE" "$NORMAL" "$*"; }
info()  { printf '   %s\n' "$*"; }
aviso() { printf '   %s!%s %s\n' "$AMARELO" "$NORMAL" "$*"; }
erro()  { printf '   %s✘ %s%s\n' "$VERMELHO" "$*" "$NORMAL" >&2; }

# Chamado automaticamente se qualquer comando falhar: explica onde parou e como voltar.
falhou() {
    trap - ERR
    erro "A atualização parou na etapa: $ETAPA"
    if [ -n "$COMMIT_ANTES" ]; then
        info ""
        info "Para voltar o código à versão anterior ($COMMIT_ANTES):"
        info "    git checkout $COMMIT_ANTES"
        info "    sudo docker compose -f $ARQUIVO_COMPOSE --env-file $ARQUIVO_ENV up -d --build"
        info "    (depois, para voltar a seguir o GitHub: git checkout $BRANCH)"
    fi
    if [ -n "$BACKUP_FEITO" ]; then
        info ""
        info "Se o banco precisar voltar ao estado de antes (só se uma migração quebrou algo):"
        info "    sudo cat $BACKUP_FEITO | sudo docker compose -f $ARQUIVO_COMPOSE --env-file $ARQUIVO_ENV \\"
        info "      exec -T db sh -c 'pg_restore -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --clean --if-exists'"
    fi
    exit 1
}

main "$@"; exit $?
