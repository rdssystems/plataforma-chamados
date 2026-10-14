# Decisões de Projeto e Arquitetura

Este documento registra decisões técnicas, simplificações e escolhas arquiteturais adotadas no desenvolvimento do Sistema de Gestão de Chamados, em conformidade com o `SPEC.md`.

## 1. Estrutura do Projeto
- **Raiz do projeto**: `manage.py` fica na raiz do workspace, com a pasta `config/` contendo as configurações principais do Django (`settings.py`, `urls.py`, `wsgi.py`).
- **Apps**: Criados como apps Django de primeiro nível (`accounts`, `plataformas`, `chamados`, `notificacoes`, `dashboard`, `relatorios`).
- **Frontend**: Templates centralizados em `templates/` com herança de `base.html`. Estilização com Tailwind CSS via CDN, HTMX via CDN, SortableJS e Chart.js via CDN conforme especificado no `SPEC.md`.

## 2. Configurações de Ambiente
- Utilização de `python-decouple` para leitura de `.env` e `dj-database-url` para parsing de `DATABASE_URL`.
- Default de banco de dados para SQLite (`db.sqlite3`), com suporte imediato a PostgreSQL caso `DATABASE_URL` esteja presente no `.env`.
- Fuso horário configurado para `America/Sao_Paulo` e idioma `pt-br`.

## 3. Modelo de Usuário e Autenticação
- Modelo `Usuario` estende `AbstractUser` e é registrado na primeira migração do app `accounts` com `AUTH_USER_MODEL = 'accounts.Usuario'`.
- Campos adicionais: `papel` (choices: `admin`, `dev`, default: `dev`), `deve_trocar_senha` (BooleanField, default: `True`), `avatar` (ImageField, upload_to='avatares/', blank=True, null=True).
- Middleware de verificação de troca de senha obrigatória: usuários com `deve_trocar_senha=True` são redirecionados automaticamente para `/conta/senha/` até realizarem a troca, com exceção de rotas estáticas, logout e a própria tela de troca de senha.

## 4. Permissões e Segurança
- Mixins no servidor (`AdminRequiredMixin`, `DevOrAdminRequiredMixin` ou decorators equivalentes) aplicados em todas as views sensíveis. Dev tentando acessar rotas administrativas recebe HTTP 403 Forbidden.
- Filtragem estrita de querysets no banco de dados para garantir que desenvolvedores vejam apenas chamados permitidos (atribuídos a eles ou criados por eles).

## 5. Exportação de Relatórios (Excel e PDF)
- **Excel**: Gerado via `openpyxl` com 4 abas estruturadas (Resumo, Desempenho por Dev, Desempenho por Plataforma e Lista Detalhada).
- **PDF**: O `SPEC.md` especifica WeasyPrint. No ambiente operacional Windows onde bibliotecas GTK C (`libgobject-2.0-0`) não estejam instaladas no sistema, o sistema utiliza automaticamente fallback robusto com `xhtml2pdf` a partir do mesmo template HTML de impressão, garantindo a geração transparente e perfeita do arquivo `.pdf` sem falhas de runtime.

