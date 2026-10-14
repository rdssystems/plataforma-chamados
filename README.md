# Sistema de Gestão de Chamados

Sistema web completo de triagem, acompanhamento e relatórios de chamados técnicos desenvolvido em **Django 5.x** e **Python 3.12+**, seguindo rigorosamente a especificação técnica do projeto.

---

## 🚀 Tecnologias Utilizadas

- **Backend:** Python 3.12+, Django 5.x
- **Banco de Dados:** SQLite (padrão de desenvolvimento) com suporte a PostgreSQL via `DATABASE_URL` (dj-database-url / psycopg2)
- **Frontend Interativo:** Templates Django server-side, [Tailwind CSS](https://tailwindcss.com) (CDN), [HTMX](https://htmx.org) (comentários reativos e updates sem reload), [SortableJS](https://sortablejs.github.io/Sortable/) (Kanban drag-and-drop) e [Chart.js](https://www.chartjs.org/) (gráficos interativos de evolução semanal, plataformas, desenvolvedores e prioridades).
- **Exportações:** [openpyxl](https://openpyxl.readthedocs.io/) (relatórios Excel com abas e formatação profissional) e [xhtml2pdf / WeasyPrint](https://xhtml2pdf.readthedocs.io/) (relatórios gerenciais em PDF).
- **Auditoria:** [django-simple-history](https://django-simple-history.readthedocs.io/) e histórico centralizado de mudanças de status.
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
├── dashboard/          # Cards de indicadores, endpoint de gráficos Chart.js e listas de atenção
├── relatorios/         # Serviço unificado de métricas (services.py) e exportadores (Excel e PDF)
├── notificacoes/       # Central e sino de notificações no topo
├── templates/          # Templates HTML Django com Tailwind CSS
└── static/             # Arquivos estáticos (JavaScript, CSS, ícones)
```

---

## 🔒 Regras de Negócio e Permissões

- **Controle de Acesso no Servidor:** Todas as rotas administrativas e querysets filtram permissões via servidor. Desenvolvedores visualizam exclusivamente chamados onde são criadores ou responsáveis.
- **Primeiro Acesso:** Usuários cadastrados com senha provisória têm `deve_trocar_senha=True` e são obrigatoriamente redirecionados à tela de troca de senha até concluírem o processo.
- **Serviço Único de Transição (`chamados/services.py:mudar_status`):** Todas as transições de status (pelo detalhe, pelo formulário ou por arraste no Kanban) passam pelo mesmo serviço centralizado. Transições fora do fluxo especificado são recusadas e registradas.
- **Cálculo Unificado de Métricas (`relatorios/services.py:calcular_metricas_relatorio`):** Garante total consistência: os números exibidos na tela de relatórios batem com exatidão com os arquivos exportados em Excel e PDF.
- **Desempenho no Banco:** O dashboard carrega com apenas 8 consultas SQL agregadas via ORM (`aggregate`, `annotate`, `TruncWeek`), muito abaixo do teto de 15 queries exigido.
