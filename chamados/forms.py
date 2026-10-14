from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from plataformas.models import Plataforma
from .models import Chamado

Usuario = get_user_model()


class ChamadoForm(forms.ModelForm):
    class Meta:
        model = Chamado
        fields = ['titulo', 'descricao', 'plataforma', 'tipo', 'prioridade', 'responsavel', 'prazo']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none',
                'placeholder': 'Título claro e objetivo da demanda'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none',
                'rows': 4,
                'placeholder': 'Descreva detalhadamente o problema, passos para reproduzir ou requisitos...'
            }),
            'plataforma': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }),
            'prioridade': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }),
            'responsavel': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }),
            'prazo': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Apenas plataformas ativas podem ser selecionadas
        self.fields['plataforma'].queryset = Plataforma.objects.filter(ativa=True)

        # Responsaveis ativos
        self.fields['responsavel'].queryset = Usuario.objects.filter(is_active=True).order_by('first_name', 'username')

        # Se for Dev criando ou editando:
        if self.user and not getattr(self.user, 'is_admin', False):
            # Dev não pode atribuir responsável, alterar prioridade nem prazo
            if 'responsavel' in self.fields:
                self.fields.pop('responsavel')
            if 'prioridade' in self.fields:
                self.fields.pop('prioridade')
            if 'prazo' in self.fields:
                self.fields.pop('prazo')

    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.instance.pk:
            if self.instance.status in Chamado.STATUS_FINAIS:
                raise ValidationError("Chamado Concluído ou Cancelado não aceita edição de campos.")
        return cleaned_data

    def save(self, commit=True):
        chamado = super().save(commit=False)
        if not chamado.pk:
            chamado.criado_por = self.user
            # Se for Dev, fica sem responsável até o admin atribuir
            if self.user and not getattr(self.user, 'is_admin', False):
                chamado.responsavel = None
                chamado.prioridade = Chamado.PRIORIDADE_MEDIA
        if commit:
            chamado.save()
        return chamado


class MudarStatusForm(forms.Form):
    novo_status = forms.ChoiceField(choices=Chamado.STATUS_CHOICES)
    comentario = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Motivo da alteração (obrigatório para devolução, cancelamento e reabertura)...',
            'class': 'w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm'
        })
    )


class ComentarioForm(forms.ModelForm):
    class Meta:
        from .models import Comentario
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm',
                'placeholder': 'Escreva um comentário ou atualização sobre este chamado...'
            })
        }


class AnexoForm(forms.ModelForm):
    class Meta:
        from .models import Anexo
        model = Anexo
        fields = ['arquivo']
        widgets = {
            'arquivo': forms.FileInput(attrs={
                'class': 'block w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
            })
        }

    def clean_arquivo(self):
        from .models import Anexo
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo:
            if arquivo.size > Anexo.LIMITE_TAMANHO_BYTES:
                raise ValidationError("O arquivo excede o limite máximo permitido de 10 MB.")
        return arquivo

