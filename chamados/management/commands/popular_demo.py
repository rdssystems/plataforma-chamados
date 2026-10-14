import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from accounts.models import Usuario
from plataformas.models import Plataforma
from chamados.models import Chamado, MudancaStatus, Comentario


class Command(BaseCommand):
    help = "Popula o banco de dados com 3 plataformas, 1 admin, 3 devs e ~60 chamados dos últimos 3 meses."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Limpa chamados, plataformas e usuários de teste antes de popular.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando geração de dados de demonstração..."))

        if options["limpar"]:
            self.stdout.write(self.style.WARNING("Limpando dados anteriores..."))
            Chamado.objects.all().delete()
            Plataforma.objects.all().delete()
            Usuario.objects.exclude(is_superuser=True).delete()

        agora = timezone.now()
        hoje = agora.date()

        # 1. Usuários
        admin_gestor, _ = Usuario.objects.get_or_create(
            username="gestor",
            defaults={
                "first_name": "Gestor",
                "last_name": "Geral",
                "email": "gestor@empresa.com",
                "papel": Usuario.PAPEL_ADMIN,
                "deve_trocar_senha": False,
            },
        )
        admin_gestor.set_password("gestor123")
        admin_gestor.papel = Usuario.PAPEL_ADMIN
        admin_gestor.deve_trocar_senha = False
        admin_gestor.save()

        devs_info = [
            ("dev_lucas", "Lucas", "Silva", "lucas@empresa.com"),
            ("dev_mariana", "Mariana", "Costa", "mariana@empresa.com"),
            ("dev_carlos", "Carlos", "Oliveira", "carlos@empresa.com"),
        ]

        devs = []
        for username, fname, lname, email in devs_info:
            dev, _ = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": fname,
                    "last_name": lname,
                    "email": email,
                    "papel": Usuario.PAPEL_DEV,
                    "deve_trocar_senha": False,
                },
            )
            dev.set_password("dev123")
            dev.papel = Usuario.PAPEL_DEV
            dev.deve_trocar_senha = False
            dev.save()
            devs.append(dev)

        self.stdout.write(self.style.SUCCESS("[OK] Usuarios criados: gestor (admin), dev_lucas, dev_mariana, dev_carlos"))

        # 2. Plataformas
        plat_dados = [
            ("Portal do Cliente", "#3B82F6", "Área web onde clientes acessam faturas e contratos"),
            ("Aplicativo Mobile", "#10B981", "App Android e iOS para clientes finais"),
            ("API de Pagamentos", "#8B5CF6", "Serviço interno de processamento de transações Pix e Cartão"),
        ]

        plataformas = []
        for nome, cor, desc in plat_dados:
            plat, _ = Plataforma.objects.get_or_create(
                nome=nome,
                defaults={"cor": cor, "descricao": desc, "ativa": True},
            )
            plat.cor = cor
            plat.ativa = True
            plat.save()
            plataformas.append(plat)

        self.stdout.write(self.style.SUCCESS("[OK] 3 Plataformas configuradas com cores."))

        # 3. Modelos de chamados com títulos realistas por tipo
        exemplos_titulos = [
            # Bugs
            ("Erro 500 ao gerar PDF do boleto na 2ª via", Chamado.TIPO_BUG, Chamado.PRIORIDADE_URGENTE),
            ("Timeout na consulta de saldo no app mobile", Chamado.TIPO_BUG, Chamado.PRIORIDADE_ALTA),
            ("Falha no login com autenticação biométrica em Android 14", Chamado.TIPO_BUG, Chamado.PRIORIDADE_ALTA),
            ("Botão de pagamento duplicando requisição com duplo clique", Chamado.TIPO_BUG, Chamado.PRIORIDADE_URGENTE),
            ("Formatação quebrada da data de vencimento no extrato", Chamado.TIPO_BUG, Chamado.PRIORIDADE_BAIXA),
            ("WebHook Pix disparando notificações em duplicidade", Chamado.TIPO_BUG, Chamado.PRIORIDADE_ALTA),
            ("Campo de CPF permitindo caracteres especiais no cadastro", Chamado.TIPO_BUG, Chamado.PRIORIDADE_MEDIA),
            ("Erro de CORS ao acessar rota de produtos no ambiente de homologação", Chamado.TIPO_BUG, Chamado.PRIORIDADE_MEDIA),
            ("Imagens de avatar não renderizando em Safari iOS", Chamado.TIPO_BUG, Chamado.PRIORIDADE_BAIXA),
            ("Falha intermitente na fila Celery de envio de e-mails", Chamado.TIPO_BUG, Chamado.PRIORIDADE_ALTA),
            ("Loop de redirecionamento no fluxo de recuperação de senha", Chamado.TIPO_BUG, Chamado.PRIORIDADE_URGENTE),
            ("Erro de chave estrangeira ao excluir item cancelado do carrinho", Chamado.TIPO_BUG, Chamado.PRIORIDADE_ALTA),
            ("Alerta de sessão expirada exibido antes do tempo configurado", Chamado.TIPO_BUG, Chamado.PRIORIDADE_MEDIA),
            ("Filtro por data não respeita o fuso horário de Brasília", Chamado.TIPO_BUG, Chamado.PRIORIDADE_BAIXA),
            ("Upload de comprovante falha silenciosamente quando extensão é .jpeg", Chamado.TIPO_BUG, Chamado.PRIORIDADE_MEDIA),
            # Melhorias
            ("Otimizar queries N+1 no endpoint de listagem de faturas", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_ALTA),
            ("Adicionar feedback visual de loading no botão de checkout", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_MEDIA),
            ("Redesenhar card de resumo financeiro do dashboard do cliente", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_MEDIA),
            ("Implementar paginação infinita na listagem de extratos", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_BAIXA),
            ("Cache de respostas da API com Redis para rotas públicas", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_ALTA),
            ("Compressão automática de imagens no upload de documentos", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_MEDIA),
            ("Melhorar contraste de cores para conformidade WCAG AA", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_BAIXA),
            ("Migrar consultas de busca de texto para Full-Text Search", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_MEDIA),
            ("Atualizar versão das dependências com vulnerabilidades reportadas", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_ALTA),
            ("Adicionar máscara automática de telefone com 9 dígitos", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_BAIXA),
            ("Limpeza de logs antigos em background para economizar disco", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_BAIXA),
            ("Melhorar mensagens de validação no formulário de endereço", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_BAIXA),
            ("Suporte a temas claro e escuro no aplicativo mobile", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_MEDIA),
            ("Indexar colunas de chave estrangeira com alto volume de escrita", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_ALTA),
            ("Refatorar módulo de emissão de notas fiscais para desacoplar serviço", Chamado.TIPO_MELHORIA, Chamado.PRIORIDADE_ALTA),
            # Novas Funcionalidades
            ("Integração com gateway de pagamento secundário de contingência", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_ALTA),
            ("Exportação de relatórios gerenciais em formato XLSX e PDF", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_MEDIA),
            ("Implementação de notificações push para lembrete de vencimento", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_ALTA),
            ("Módulo de autenticação de dois fatores (2FA) via app autenticador", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_URGENTE),
            ("Dashboard com gráficos interativos de faturamento mensal", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_MEDIA),
            ("Fluxo de onboarding com tutorial interativo para novos usuários", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_BAIXA),
            ("Suporte a parcelamento de compras via Pix parcelado", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_ALTA),
            ("Webhook para notificar sistemas externos sobre alteração de status", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_MEDIA),
            ("Funcionalidade de cancelamento de assinatura com pesquisa de churn", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_MEDIA),
            ("Geração de relatórios programados com envio automático por e-mail", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_BAIXA),
            ("Visualização de histórico de acessos por IP e dispositivo", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_BAIXA),
            ("Emissão de declaração anual de quitação de débitos em PDF", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_MEDIA),
            ("Atendimento com chatbot integrado para dúvidas frequentes", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_ALTA),
            ("Agendamento de pagamentos recorrentes no cartão de crédito", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_ALTA),
            ("Sistema de cashback para pagamentos antecipados", Chamado.TIPO_NOVA_FUNCIONALIDADE, Chamado.PRIORIDADE_MEDIA),
            # Suporte
            ("Solicitação de reprocessamento manual de remessa bancária", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_ALTA),
            ("Reset manual de bloqueio por tentativas excessivas de login", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_URGENTE),
            ("Auditoria de transação divergente solicitada pela contabilidade", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_ALTA),
            ("Orientação técnica para equipe de atendimento sobre erro de token", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_MEDIA),
            ("Criação de script para sincronização de cadastro duplicado", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_MEDIA),
            ("Extração de logs brutos de requisição para análise de segurança", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_MEDIA),
            ("Investigação de lentidão no banco durante o fechamento de mês", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_URGENTE),
            ("Configuração de certificado SSL no subdomínio da API", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_ALTA),
            ("Validação de regras de negócio com o time de compliance", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_BAIXA),
            ("Ajuste manual de permissão de usuário legado no banco", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_BAIXA),
            ("Dúvida sobre endpoint de consulta de webhook de estorno", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_BAIXA),
            ("Atualização de tabelas de alíquotas de impostos estaduais", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_MEDIA),
            ("Geração de chave de API para novo parceiro integrado", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_MEDIA),
            ("Verificação de integridade dos backups semanais no S3", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_ALTA),
            ("Restauração de dados de ambiente de homologação a partir de dump", Chamado.TIPO_SUPORTE, Chamado.PRIORIDADE_BAIXA),
        ]

        # Garantir exatamente 60 chamados
        exemplos_titulos = exemplos_titulos[:60]

        # Distribuição de status para os 60 chamados:
        # - 25 CONCLUIDO
        # - 12 EM_ANDAMENTO (alguns atrasados)
        # - 8 EM_REVISAO
        # - 8 ABERTO (alguns sem responsável, alguns atrasados)
        # - 7 CANCELADO
        status_dist = (
            [Chamado.STATUS_CONCLUIDO] * 25
            + [Chamado.STATUS_EM_ANDAMENTO] * 12
            + [Chamado.STATUS_EM_REVISAO] * 8
            + [Chamado.STATUS_ABERTO] * 8
            + [Chamado.STATUS_CANCELADO] * 7
        )

        random.seed(42)  # Reprodutibilidade
        random.shuffle(status_dist)

        chamados_criados = 0

        with transaction.atomic():
            for i, (titulo, tipo, prioridade) in enumerate(exemplos_titulos):
                status_alvo = status_dist[i]
                plat = plataformas[i % len(plataformas)]
                criador = admin_gestor if i % 4 == 0 else devs[i % len(devs)]

                # Atribuição de responsável
                if status_alvo == Chamado.STATUS_ABERTO and (i % 3 == 0):
                    # Sem responsável (para aparecer no card do admin)
                    responsavel = None
                else:
                    responsavel = devs[i % len(devs)]

                # Espalhar criado_em entre 85 dias atrás e 2 dias atrás
                dias_atras = random.randint(3, 85)
                data_criacao = agora - timedelta(days=dias_atras, hours=random.randint(1, 10))

                # Definir prazo
                # Alguns chamados têm prazo, outros não
                tem_prazo = random.random() > 0.15
                if tem_prazo:
                    # Prazo entre criação + 2 dias e criação + 14 dias
                    duracao_esperada = random.randint(2, 12)
                    prazo = (data_criacao + timedelta(days=duracao_esperada)).date()
                else:
                    prazo = None

                # Datas de iniciado_em e concluido_em
                iniciado_em = None
                concluido_em = None

                if status_alvo in (Chamado.STATUS_EM_ANDAMENTO, Chamado.STATUS_EM_REVISAO, Chamado.STATUS_CONCLUIDO):
                    iniciado_em = data_criacao + timedelta(hours=random.randint(2, 48))

                if status_alvo == Chamado.STATUS_CONCLUIDO:
                    if not iniciado_em:
                        iniciado_em = data_criacao + timedelta(hours=random.randint(2, 24))
                    
                    # Decidir se foi entregue no prazo ou atrasado
                    if prazo and (random.random() < 0.25):  # 25% entregue atrasado
                        concluido_em = timezone.make_aware(
                            timezone.datetime.combine(prazo + timedelta(days=random.randint(1, 4)), timezone.datetime.min.time())
                        )
                    else:
                        dias_ate_conclusao = random.randint(1, 5)
                        concluido_em = iniciado_em + timedelta(days=dias_ate_conclusao, hours=random.randint(1, 8))
                    
                    # Se concluído após agora, ajustar para agora
                    if concluido_em > agora:
                        concluido_em = agora - timedelta(hours=random.randint(1, 12))

                chamado = Chamado(
                    titulo=titulo,
                    descricao=f"Descrição detalhada para a demanda '{titulo}'.\n\nRequisitos técnicos e contexto operacional verificados durante triagem.",
                    tipo=tipo,
                    prioridade=prioridade,
                    status=status_alvo,
                    plataforma=plat,
                    responsavel=responsavel,
                    criado_por=criador,
                    prazo=prazo,
                    iniciado_em=iniciado_em,
                    concluido_em=concluido_em,
                    ordem_kanban=i,
                )
                chamado.save()

                # Forçar criado_em retroativo no banco
                Chamado.objects.filter(pk=chamado.pk).update(criado_em=data_criacao)
                chamado.refresh_from_db()

                # Criar histórico de mudanças de status
                m1 = MudancaStatus.objects.create(
                    chamado=chamado,
                    de_status=Chamado.STATUS_ABERTO,
                    para_status=Chamado.STATUS_ABERTO,
                    alterado_por=criador,
                )
                MudancaStatus.objects.filter(pk=m1.pk).update(alterado_em=data_criacao)

                if iniciado_em and status_alvo != Chamado.STATUS_ABERTO:
                    m2 = MudancaStatus.objects.create(
                        chamado=chamado,
                        de_status=Chamado.STATUS_ABERTO,
                        para_status=Chamado.STATUS_EM_ANDAMENTO,
                        alterado_por=responsavel or criador,
                    )
                    MudancaStatus.objects.filter(pk=m2.pk).update(alterado_em=iniciado_em)

                if status_alvo == Chamado.STATUS_EM_REVISAO:
                    m3 = MudancaStatus.objects.create(
                        chamado=chamado,
                        de_status=Chamado.STATUS_EM_ANDAMENTO,
                        para_status=Chamado.STATUS_EM_REVISAO,
                        alterado_por=responsavel or criador,
                    )
                    MudancaStatus.objects.filter(pk=m3.pk).update(alterado_em=iniciado_em + timedelta(days=1))

                if status_alvo == Chamado.STATUS_CONCLUIDO:
                    m4 = MudancaStatus.objects.create(
                        chamado=chamado,
                        de_status=Chamado.STATUS_EM_REVISAO if random.random() > 0.5 else Chamado.STATUS_EM_ANDAMENTO,
                        para_status=Chamado.STATUS_CONCLUIDO,
                        alterado_por=responsavel or criador,
                    )
                    MudancaStatus.objects.filter(pk=m4.pk).update(alterado_em=concluido_em or agora)

                if status_alvo == Chamado.STATUS_CANCELADO:
                    data_cancel = data_criacao + timedelta(days=random.randint(1, 5))
                    m5 = MudancaStatus.objects.create(
                        chamado=chamado,
                        de_status=Chamado.STATUS_ABERTO,
                        para_status=Chamado.STATUS_CANCELADO,
                        alterado_por=admin_gestor,
                        comentario_motivo="Cancelado conforme alinhamento com a diretoria técnica.",
                    )
                    MudancaStatus.objects.filter(pk=m5.pk).update(alterado_em=data_cancel)

                # Criar alguns comentários de exemplo
                if i % 3 == 0:
                    c1 = Comentario.objects.create(
                        chamado=chamado,
                        autor=admin_gestor,
                        texto="Favor priorizar esta entrega pois impacta a esteira de liberação.",
                    )
                    Comentario.objects.filter(pk=c1.pk).update(criado_em=data_criacao + timedelta(hours=3))

                if responsavel and i % 2 == 0:
                    c2 = Comentario.objects.create(
                        chamado=chamado,
                        autor=responsavel,
                        texto="Ambiente de desenvolvimento atualizado e testes locais em andamento.",
                    )
                    Comentario.objects.filter(pk=c2.pk).update(criado_em=data_criacao + timedelta(days=1))

                chamados_criados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] {chamados_criados} chamados criados com sucesso espalhados nos ultimos 3 meses!"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Credenciais para teste:\n"
                "  - Admin: gestor / gestor123\n"
                "  - Devs:  dev_lucas / dev123\n"
                "           dev_mariana / dev123\n"
                "           dev_carlos / dev123"
            )
        )
