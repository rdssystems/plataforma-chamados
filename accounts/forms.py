from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model

Usuario = get_user_model()


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuário',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition',
            'placeholder': 'Digite seu usuário'
        })
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition',
            'placeholder': 'Digite sua senha'
        })
    )


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition'
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.deve_trocar_senha = False
        if commit:
            user.save()
        return user


class UsuarioCriarForm(forms.ModelForm):
    senha_provisoria = forms.CharField(
        label='Senha Provisória',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition',
            'placeholder': 'Digite uma senha temporária'
        }),
        help_text='O usuário será obrigado a alterá-la no primeiro acesso.'
    )

    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'papel', 'avatar', 'senha_provisoria']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'papel': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'avatar': forms.FileInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
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


class UsuarioEditarForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'papel', 'is_active', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'papel': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 rounded focus:ring-blue-500'}),
            'avatar': forms.FileInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
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


class UsuarioRedefinirSenhaForm(forms.Form):
    nova_senha_provisoria = forms.CharField(
        label='Nova Senha Provisória',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition',
            'placeholder': 'Digite a nova senha provisória'
        }),
        help_text='O usuário será marcado para trocar de senha no próximo acesso.'
    )
