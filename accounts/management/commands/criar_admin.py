from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Cria o primeiro usuário administrador do sistema'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Nome de usuário do admin (padrão: admin)')
        parser.add_argument('--email', type=str, default='admin@exemplo.com', help='E-mail do admin')
        parser.add_argument('--password', type=str, default='admin123', help='Senha inicial do admin')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        user, created = Usuario.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'papel': Usuario.PAPEL_ADMIN,
                'deve_trocar_senha': False,
                'is_staff': True,
                'is_superuser': True,
            }
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Administrador '{username}' criado com sucesso!"))
        else:
            user.papel = Usuario.PAPEL_ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.WARNING(f"Administrador '{username}' já existia. Permissões e senha foram atualizadas."))
