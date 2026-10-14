from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('papel', Usuario.PAPEL_DEV)
        extra_fields.setdefault('deve_trocar_senha', True)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('papel', Usuario.PAPEL_ADMIN)
        extra_fields.setdefault('deve_trocar_senha', False)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser precisa ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser precisa ter is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError('O nome de usuário é obrigatório.')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Usuario(AbstractUser):
    PAPEL_ADMIN = 'admin'
    PAPEL_DEV = 'dev'
    PAPEIS_CHOICES = [
        (PAPEL_ADMIN, 'Administrador'),
        (PAPEL_DEV, 'Desenvolvedor'),
    ]

    papel = models.CharField(
        max_length=10,
        choices=PAPEIS_CHOICES,
        default=PAPEL_DEV,
        verbose_name='Papel'
    )
    deve_trocar_senha = models.BooleanField(
        default=True,
        verbose_name='Deve trocar senha no próximo acesso'
    )
    avatar = models.ImageField(
        upload_to='avatares/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Avatar'
    )

    objects = UsuarioManager()

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['first_name', 'username']

    @property
    def is_admin(self):
        return self.papel == self.PAPEL_ADMIN or self.is_superuser

    @property
    def is_dev(self):
        return self.papel == self.PAPEL_DEV and not self.is_superuser

    def __str__(self):
        nome = self.get_full_name()
        return nome if nome else self.username
