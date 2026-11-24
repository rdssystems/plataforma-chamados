# Sistema de Gestão de Chamados

Sistema web completo de triagem, acompanhamento e relatórios de chamados técnicos desenvolvido em **Django 5.x** e **Python 3.12+**, seguindo rigorosamente a especificação técnica do projeto.

---

## 🚀 Tecnologias Utilizadas

- **Backend:** Python 3.12+, Django 5.x
- **Banco de Dados:** SQLite (padrão de desenvolvimento) com suporte a PostgreSQL via `DATABASE_URL` (dj-database-url / psycopg2)
- **Frontend Interativo:** Templates Django server-side, [Tailwind CSS](https://tailwindcss.com) (CDN), [HTMX](https://htmx.org) (comentários reativos e updates sem reload), [SortableJS](https://sortablejs.github.io/Sortable/) (Kanban drag-and-drop) e [Apache ECharts](https://echarts.apache.org/) 6.1 (gráficos interativos do dashboard: evolução semanal, plataformas, desenvolvedores e prioridades, com tooltip, versão em tabela e descrição para leitores de tela).
- **Exportações:** [openpyxl](https://openpyxl.readthedocs.io/) (relatórios Excel com abas e formatação profissional) e [xhtml2pdf / WeasyPrint](https://xhtml2pdf.readthedocs.io/) (relatórios gerenciais em PDF).
- **Auditoria:** [django-simple-history](https://django-simple-history.readthedocs.io/) e histórico centralizado de mudanças de status.
- **Tempo real:** [Django Channels](https://channels.readthedocs.io/) (WebSocket) servido pelo [Daphne](https://github.com/django/daphne), com Redis em produção, para o chat entre usuários, a lista de quem está online e as notificações instantâneas.
- **Testes Automatizados:** [pytest](https://docs.pytest.org/) e [pytest-django](https://pytest-django.readthedocs.io/).

---

## 📋 Pré-requisitos

- Python 3.12 ou superior instalado.
- Git instalado.

---

## 🛠️ Guia de Instalação e Execução

### 1. Clonar ou Acessar a Raiz do Repositório
```bash
cd "c:/Users/Klisman rDs/Desktop/Plataforma Tasks"
```

### 2. Criar e Ativar o Ambiente Virtual
No Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
No Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar as Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar as Variáveis de Ambiente
Copie o arquivo `.env.example` para `.env`:
```powershell
cp .env.example .env
```
O arquivo `.env` já vem pré-configurado com valores seguros para desenvolvimento local:
- `SECRET_KEY`: chave criptográfica do Django.
- `DEBUG`: `True` para desenvolvimento.
- `ALLOWED_HOSTS`: `localhost,127.0.0.1`.
- `DATABASE_URL`: `sqlite:///db.sqlite3` (pode ser apontado para `postgres://usuario:senha@host:5432/nome_banco` em produção).

### 5. Executar as Migrações do Banco de Dados
```bash
python manage.py migrate
```

### 6. Criar o Primeiro Administrador
Utilize o comando de gerenciamento dedicado `criar_admin`:
```bash
python manage.py criar_admin --username admin --email admin@empresa.com --password admin123
```
*(Caso não informe os parâmetros via linha de comando, eles serão solicitados interativamente).*

### 7. Popular com Dados de Demonstração (Opcional, Recomendado)
Gera automaticamente 3 plataformas com cores, 1 gestor admin, 3 desenvolvedores e 60 chamados realistas espalhados ao longo dos últimos 3 meses:
```bash
python manage.py popular_demo
```
Para reiniciar os dados de teste do zero, use a flag `--limpar`:
```bash
python manage.py popular_demo --limpar
```

**Credenciais dos Usuários de Demonstração:**
| Papel | Usuário | Senha | Acesso / Permissões |
| :--- | :--- | :--- | :--- |
| **Admin** | `gestor` | `gestor123` | Acesso total: CRUD usuários, plataformas, todos os chamados, relatórios e métricas da equipe |
| **Dev** | `dev_lucas` | `dev123` | Acesso aos próprios chamados, kanban, comentários, anexos e dashboard pessoal |
| **Dev** | `dev_mariana` | `dev123` | Acesso aos próprios chamados, kanban, comentários, anexos e dashboard pessoal |
| **Dev** | `dev_carlos` | `dev123` | Acesso aos próprios chamados, kanban, comentários, anexos e dashboard pessoal |

### 8. Iniciar o Servidor de Desenvolvimento
```bash
python manage.py runserver
```
Acesse no navegador: **`http://127.0.0.1:8000/`**

O `runserver` já sobe com o Daphne, então o chat e as notificações em tempo real funcionam em desenvolvimento sem Redis (a camada de eventos fica em memória). Em produção, defina `REDIS_URL` (os arquivos compose já fazem isso).

### 9. Publicar em uma VPS com Docker

Na VPS, instale Docker Engine e o plugin Docker Compose, clone o repositório e entre na pasta do projeto. Aponte o DNS do domínio para o IP da VPS e libere as portas **80** e **443** no firewall.

Crie o arquivo de ambiente de produção:
```bash
cp .env.production.example .env.production
openssl rand -hex 48
openssl rand -hex 32
```
Edite `.env.production`: use a primeira saída como `SECRET_KEY`, a segunda como `POSTGRES_PASSWORD` e troque `chamados.example.com` pelo domínio real em `DOMAIN`, `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`. Mantenha a senha do banco em hexadecimal para evitar caracteres que precisariam de escape na URL de conexão.

Construa e inicie os serviços:
```bash
docker compose --env-file .env.production up -d --build
```
O primeiro início aplica as migrações e coleta os arquivos estáticos automaticamente. O Caddy configura HTTPS para o domínio (e repassa o WebSocket do chat sem configuração extra); os dados do PostgreSQL e anexos ficam em volumes persistentes. O Redis só distribui eventos em tempo real e não guarda dados. Para acompanhar a inicialização:
```bash
docker compose --env-file .env.production logs -f
```

Crie o administrador:
```bash
docker compose --env-file .env.production exec web python manage.py criar_admin
```

Para atualizar após enviar novas alterações ao repositório:
```bash
git pull
docker compose --env-file .env.production up -d --build
```
`docker compose down` para os serviços sem apagar os dados. Não use `docker compose down -v`, pois isso remove também os volumes do banco e dos anexos. Faça backups regulares do banco e dos anexos.

---

## 🧪 Executando os Testes Automatizados

O projeto conta com suíte de testes automatizados com cobertura completa para regras de negócio, permissões por papel, transições de status válidas e inválidas, preenchimento de datas e cálculos de relatórios com valores conhecidos.

Para rodar todos os testes com o `pytest`:
```bash
pytest
```
Ou com saída detalhada:
```bash
pytest -v
```

---

## 🏛️ Arquitetura e Estrutura de Apps

```text
├── config/             # Configurações do projeto, URLs globais e WSGI/ASGI
├── accounts/           # Modelo Usuario customizado, auth, CRUD de equipe e middleware
├── plataformas/        # Cadastro e gestão de plataformas/sistemas com cores
├── chamados/           # Chamados, transições de status (services.py), kanban, comentários e anexos
├── dashboard/          # Cards de indicadores, endpoint dos gráficos (ECharts em static/js/dashboard_graficos.js) e listas de atenção
├── relatorios/         # Serviço unificado de métricas (services.py) e exportadores (Excel e PDF)
├── notificacoes/       # Central e sino de notificações no topo (com aviso em tempo real)
├── chat/               # Chat direto entre usuários, presença online e WebSocket (consumers.py)
├── templates/          # Templates HTML Django com Tailwind CSS
└── static/             # Arquivos estáticos (JavaScript, CSS, ícones)
```

---

## 🔒 Regras de Negócio e Permissões

- **Controle de Acesso no Servidor:** Todas as rotas administrativas e querysets filtram permissões via servidor. Desenvolvedores visualizam exclusivamente chamados onde são criadores ou responsáveis.
- **Primeiro Acesso:** Usuários cadastrados com senha provisória têm `deve_trocar_senha=True` e são obrigatoriamente redirecionados à tela de troca de senha até concluírem o processo.
- **Serviço Único de Transição (`chamados/services.py:mudar_status`):** Todas as transições de status (pelo detalhe, pelo formulário ou por arraste no Kanban) passam pelo mesmo serviço centralizado. Transições fora do fluxo especificado são recusadas e registradas.
- **Cálculo Unificado de Métricas (`relatorios/services.py:calcular_metricas_relatorio`):** Garante total consistência: os números exibidos na tela de relatórios batem com exatidão com os arquivos exportados em Excel e PDF.
- **Chat permanente:** Conversas são diretas entre dois usuários (uma por par). Mensagens não podem ser editadas nem apagadas (as chaves usam `PROTECT` e o admin é somente leitura). Usuários desativados mantêm o histórico visível, mas não recebem novas mensagens. Só os participantes acessam uma conversa.
- **Desempenho no Banco:** O dashboard carrega com apenas 8 consultas SQL agregadas via ORM (`aggregate`, `annotate`, `TruncWeek`), muito abaixo do teto de 15 queries exigido.
