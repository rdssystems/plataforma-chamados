Spec — Sistema de Gestão de Chamados (Django)
14 de out. de 2026 · @Klisman rDs
Visão geral e objetivos
Um sistema web em Django para o gestor distribuir chamados entre os desenvolvedores da equipe e acompanhar a entrega por dashboard e relatórios semanais e mensais. É uma versão enxuta de ferramentas como Jira ou Trello, focada em chamados de manutenção e evolução das plataformas que a equipe mantém.
Objetivos:
• Centralizar todos os chamados (bugs, melhorias, novas funcionalidades) por plataforma.
• Permitir que o gestor crie contas para os devs e atribua chamados a cada um.
• Dar visibilidade de status, prazos e atrasos em tempo real.
• Gerar relatórios de produtividade e tempo de resolução por período, dev e plataforma.
Escopo do MVP
O MVP cobre contas, chamados, kanban, dashboard e relatórios; o resto fica para depois.
Dentro do MVP
• Login, contas criadas pelo admin, troca de senha obrigatória no primeiro acesso.
• Cadastro de plataformas.
• Chamados com atribuição, prioridade, prazo, status, comentários, anexos e histórico.
• Lista com filtros e visão kanban com arrastar e soltar.
• Dashboard com indicadores e gráficos.
• Relatórios semanais, mensais e por período personalizado, com exportação em PDF e Excel.
• Notificações internas (sino no topo) quando um chamado é atribuído ou comentado.
Fora do MVP (fases futuras)
• Apontamento de horas, sprints, subtarefas e etiquetas customizáveis.
• Portal para solicitantes externos abrirem chamados.
• Envio automático do resumo semanal por e-mail ou WhatsApp (Evolution API).
• Integração com GitHub (vincular commits e PRs).
Stack e estrutura do projeto
Django com templates renderizados no servidor e HTMX, sem framework JavaScript separado.
Camada
Tecnologia
Backend
Python 3.12+, Django 5.x
Banco
SQLite em desenvolvimento, PostgreSQL em produção
Frontend
Templates Django, HTMX, Tailwind CSS (via CDN no início)
Kanban
SortableJS
Gráficos
Chart.js
Histórico
django-simple-history
Exportação
openpyxl (Excel), WeasyPrint (PDF)
Configuração
python-decouple ou django-environ, arquivo .env
Testes
pytest + pytest-django
Estrutura de apps sugerida:
chamados_app/
├── config/            # settings, urls, wsgi
├── accounts/          # usuário customizado, login, perfis
├── plataformas/       # cadastro das plataformas
├── chamados/          # chamados, comentários, anexos, kanban
├── notificacoes/      # notificações internas
├── dashboard/         # indicadores e gráficos
├── relatorios/        # relatórios e exportação
├── templates/
├── static/
└── media/             # anexos enviados
Papéis e permissões
Dois papéis: Admin (o gestor) controla tudo; Dev trabalha só nos chamados atribuídos a ele.
Ação
Admin
Dev
Criar, editar e desativar contas
Sim
Não
Cadastrar plataformas
Sim
Não
Criar chamado
Sim
Sim (fica sem responsável até o admin atribuir)
Atribuir ou reatribuir responsável
Sim
Não
Alterar prioridade e prazo
Sim
Não
Ver chamados
Todos
Os atribuídos a ele e os que criou
Mudar status
Qualquer transição
Só nos seus, até Em revisão
Concluir ou cancelar
Sim
Não
Comentar e anexar
Sim
Nos chamados que pode ver
Dashboard
Geral, com filtro por dev
Só os próprios números
Relatórios e exportação
Todos
Não
Regras de conta:
• Não existe cadastro público; só o admin cria contas.
• Conta nova recebe senha provisória e é obrigada a trocar no primeiro login.
• Contas não são apagadas, apenas desativadas, para preservar o histórico.
• Implementar com AbstractUser customizado e campo papel (admin/dev), checado por mixins nas views.
Modelos de dados
Sete modelos; Chamado é o centro e todo o resto se liga a ele.
Usuario (accounts, estende AbstractUser)
Campo
Tipo
Observação
papel
CharField (admin, dev)
default dev
deve_trocar_senha
BooleanField
default True
avatar
ImageField
opcional
Plataforma (plataformas)
Campo
Tipo
Observação
nome
CharField(100)
único
descricao
TextField
opcional
url
URLField
opcional
cor
CharField(7)
hex, para badges e gráficos
ativa
BooleanField
default True
Chamado (chamados)
Campo
Tipo
Observação
codigo
CharField
gerado automaticamente: CH-0001
titulo
CharField(200)
obrigatório
descricao
TextField
obrigatório
plataforma
FK Plataforma
PROTECT
tipo
CharField
bug, melhoria, nova_funcionalidade, suporte
prioridade
CharField
baixa, media, alta, urgente
status
CharField
aberto, em_andamento, em_revisao, concluido, cancelado
criado_por
FK Usuario
PROTECT
responsavel
FK Usuario
null permitido
prazo
DateField
opcional
criado_em
DateTimeField
auto_now_add
atualizado_em
DateTimeField
auto_now
iniciado_em
DateTimeField
preenchido ao entrar em Em andamento pela primeira vez
concluido_em
DateTimeField
preenchido ao concluir, limpo se reaberto
ordem_kanban
PositiveIntegerField
posição dentro da coluna
history
HistoricalRecords
django-simple-history
Propriedades: esta_atrasado (prazo vencido e status não final) e tempo_resolucao (concluido_em − criado_em).
Comentario: chamado (FK, CASCADE), autor (FK), texto, criado_em.
Anexo: chamado (FK, CASCADE), arquivo (FileField em anexos/%Y/%m/), nome_original, enviado_por (FK), enviado_em. Limite de 10 MB por arquivo.
MudancaStatus: chamado (FK), de_status, para_status, alterado_por (FK), alterado_em. Alimenta os relatórios de tempo por etapa.
Notificacao (notificacoes): destinatario (FK), chamado (FK), mensagem, lida (bool), criada_em.
Índices em Chamado: (status), (responsavel, status), (plataforma), (criado_em), (concluido_em).
Fluxo de status e regras de negócio
O dev leva o chamado até Em revisão; aprovar, devolver, reabrir e cancelar são decisões do admin.
Transições permitidas:
De
Para
Quem
Condição
Aberto
Em andamento
Responsável ou admin
Precisa ter responsável
Em andamento
Em revisão
Responsável ou admin
—
Em revisão
Concluído
Admin
—
Em revisão
Em andamento
Admin
Comentário obrigatório com o motivo
Concluído
Em andamento
Admin
Comentário obrigatório; limpa concluido_em
Aberto, Em andamento ou Em revisão
Cancelado
Admin
Comentário obrigatório
Regras de negócio:
• Toda transição grava um MudancaStatus e passa pelo serviço único mudar_status(chamado, novo_status, usuario, comentario=None), que recusa transições fora da tabela.
• iniciado_em é preenchido na primeira entrada em Em andamento; concluido_em na entrada em Concluído.
• Chamado atrasado = prazo anterior a hoje e status diferente de Concluído e Cancelado.
• Trocar o responsável notifica o novo responsável; o anterior perde o acesso se não for o criador.
• Chamado Concluído ou Cancelado não aceita edição de campos, só comentários.
Telas
Onze telas, todas com layout base (barra lateral, topo com sino de notificações e menu do usuário) e responsivas.
Tela
Rota
Quem acessa
Conteúdo principal
Login
/login/
Todos
Usuário e senha
Trocar senha
/conta/senha/
Todos
Obrigatória no primeiro acesso
Dashboard
/
Todos
Indicadores e gráficos (seção Dashboard)
Lista de chamados
/chamados/
Todos
Tabela paginada, busca por código ou título, filtros por status, prioridade, plataforma, responsável, tipo e período
Kanban
/chamados/kanban/
Todos
Uma coluna por status, cards arrastáveis, filtros de plataforma e responsável
Novo / editar chamado
/chamados/novo/, /chamados/<id>/editar/
Admin; Dev só cria
Formulário do chamado
Detalhe do chamado
/chamados/<id>/
Quem pode ver
Dados, ações de status, comentários, anexos e linha do tempo do histórico
Plataformas
/plataformas/
Admin
Lista e formulário
Usuários
/usuarios/
Admin
Lista, criar, editar, desativar, redefinir senha
Notificações
/notificacoes/
Todos
Lista, marcar como lida
Relatórios
/relatorios/
Admin
Filtros, resultado na tela, botões de exportar
Detalhes de interface:
• Card do kanban: código, título, badge da plataforma (com a cor dela), prioridade, avatar do responsável e prazo em vermelho quando atrasado.
• Ações rápidas via HTMX sem recarregar a página: mudar status, atribuir, comentar, marcar notificação como lida.
• Mensagens de sucesso e erro com o framework de messages do Django.
Dashboard
Uma tela que responde em cinco segundos: o que está aberto, o que está atrasado e quem entregou o quê no mês.
Cards de indicadores (topo)
• Abertos (status Aberto)
• Em andamento (Em andamento + Em revisão)
• Atrasados (prazo vencido e status não final), em destaque vermelho
• Concluídos no mês corrente
• Sem responsável (só admin)
Gráficos (Chart.js)
• Linha: chamados abertos × concluídos por semana, últimas 12 semanas.
• Barras: chamados ativos por plataforma, com a cor de cada plataforma.
• Barras: concluídos por dev no mês (só admin).
• Rosca: distribuição dos ativos por prioridade.
Listas
• Atrasados, ordenados pelo prazo mais antigo.
• Vencendo nos próximos 3 dias.
• Últimas 10 atividades (mudanças de status e comentários).
O dev vê a mesma tela filtrada pelos próprios chamados. Os dados dos gráficos vêm de uma view que retorna JSON, com consultas agregadas (annotate, TruncWeek), sem laços em Python.
Relatórios
O admin escolhe o período (semana, mês ou datas livres) e os filtros, vê o resultado na tela e exporta em PDF ou Excel.
Filtros: período (atalhos Esta semana, Semana passada, Este mês, Mês passado, ou intervalo personalizado), dev, plataforma, tipo e prioridade.
Métricas do período
Métrica
Como calcular
Chamados abertos
criado_em dentro do período
Chamados concluídos
concluido_em dentro do período
Tempo médio de resolução
média de concluido_em − criado_em dos concluídos
Entregues no prazo
% dos concluídos com concluido_em ≤ prazo (só os que têm prazo)
Atrasados no fim do período
prazo < fim do período e não concluídos até ele
Backlog
não finais na data de fim do período
Quebras: tabela por dev (concluídos, tempo médio, % no prazo), tabela por plataforma e distribuição por tipo e prioridade.
Lista detalhada: todos os chamados concluídos no período, com código, título, plataforma, responsável, datas e tempo de resolução.
Exportação
• Excel (openpyxl): uma aba de resumo, uma por dev e plataforma, e uma com a lista detalhada.
• PDF (WeasyPrint): cabeçalho com período e filtros, indicadores, tabelas e a lista, a partir de um template HTML próprio para impressão.
• Nome do arquivo: relatorio_chamados_AAAA-MM-DD_AAAA-MM-DD.xlsx / .pdf.
A lógica de cálculo fica num módulo de serviço (relatorios/services.py) usado pela tela e pelas duas exportações, para os números serem sempre os mesmos.
Etapas de desenvolvimento e critérios de aceite
Seis etapas; cada uma termina com algo usável e testes passando antes de começar a próxima.
Etapa 1 — Base, contas e permissões
[ ] Projeto Django criado com a estrutura de apps, .env, requirements.txt e .gitignore.
[ ] Usuário customizado com papel e deve_trocar_senha; comando criar_admin para o primeiro admin.
[ ] Login, logout e troca de senha; quem tem deve_trocar_senha é redirecionado até trocar.
[ ] Tela de usuários (só admin): criar com senha provisória, editar, desativar, redefinir senha.
[ ] Layout base com barra lateral, topo e menu conforme o papel.
[ ] Dev que acessa uma rota de admin recebe 403.
Etapa 2 — Plataformas e chamados
[ ] CRUD de plataformas (só admin).
[ ] Criar, editar e ver chamado; código CH-0001 gerado sem repetir.
[ ] Atribuição de responsável e regras de permissão da tabela de papéis.
[ ] Transições de status validadas num único serviço (chamados/services.py); transição inválida é recusada.
[ ] iniciado_em, concluido_em e MudancaStatus gravados nas transições.
[ ] Lista com busca, filtros e paginação; dev vê só o que pode ver.
Etapa 3 — Comentários, anexos, histórico e notificações
[ ] Comentários via HTMX no detalhe do chamado.
[ ] Upload de anexos com limite de 10 MB e download só para quem vê o chamado.
[ ] Linha do tempo no detalhe juntando histórico, mudanças de status e comentários.
[ ] Notificação ao responsável quando o chamado é atribuído, comentado ou muda de status; sino com contador de não lidas.
Etapa 4 — Kanban
[ ] Uma coluna por status; arrastar entre colunas chama o mesmo serviço de transição.
[ ] Arraste recusado volta o card para a coluna original e mostra a mensagem.
[ ] Ordem dentro da coluna salva em ordem_kanban.
[ ] Filtros de plataforma e responsável.
Etapa 5 — Dashboard
[ ] Cards, gráficos e listas da seção Dashboard.
[ ] Dev vê só os próprios números.
[ ] Consultas agregadas no banco; página carrega com até 15 queries.
Etapa 6 — Relatórios
[ ] Tela com filtros e todas as métricas da seção Relatórios.
[ ] Exportação Excel e PDF com os mesmos números da tela.
[ ] Testes do serviço de relatórios com dados de exemplo e resultados conhecidos.
Extra — Dados de demonstração
[ ] Comando popular_demo que cria 3 plataformas, 1 admin, 3 devs e cerca de 60 chamados espalhados nos últimos 3 meses, para testar dashboard e relatórios.