from django import forms

from config.formularios import FormularioBootstrap
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model

Usuario = get_user_model()


class CustomLoginForm(FormularioBootstrap, AuthenticationForm):
    username = forms.CharField(
        label='Usuário',
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'autocomplete': 'username',
            'autocapitalize': 'none',
        })
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'})
    )


class CustomPasswordChangeForm(FormularioBootstrap, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs['autocomplete'] = 'current-password'
        for nome in ('new_password1', 'new_password2'):
            self.fields[nome].widget.attrs['autocomplete'] = 'new-password'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.deve_trocar_senha = False
        if commit:
            user.save()
        return user


class UsuarioCriarForm(FormularioBootstrap, forms.ModelForm):
    senha_provisoria = forms.CharField(
        label='Senha Provisória',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Digite uma senha temporária'
        }),
        help_text='O usuário será obrigado a alterá-la no primeiro acesso.'
    )

    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'papel', 'avatar', 'senha_provisoria']
        widgets = {
            'username': forms.TextInput(attrs={}),
            'first_name': forms.TextInput(attrs={}),
            'last_name': forms.TextInput(attrs={}),
            'email': forms.EmailInput(attrs={}),
            'papel': forms.Select(attrs={}),
            'avatar': forms.FileInput(attrs={}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['senha_provisoria'])
        user.deve_trocar_senha = True
        if user.papel == Usuario.PAPEL_ADMIN:
            user.is_staff = True
        else:
            user.is_staff = False
        if commit:
            user.save()
        return user


class UsuarioEditarForm(FormularioBootstrap, forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'papel', 'is_active', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={}),
            'last_name': forms.TextInput(attrs={}),
            'email': forms.EmailInput(attrs={}),
            'papel': forms.Select(attrs={}),
            'is_active': forms.CheckboxInput(attrs={}),
            'avatar': forms.FileInput(attrs={}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.papel == Usuario.PAPEL_ADMIN:
            user.is_staff = True
        else:
            user.is_staff = False
        if commit:
            user.save()
        return user


class UsuarioRedefinirSenhaForm(FormularioBootstrap, forms.Form):
    nova_senha_provisoria = forms.CharField(
        label='Nova Senha Provisória',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Digite a nova senha provisória'
        }),
        help_text='O usuário será marcado para trocar de senha no próximo acesso.'
    )
