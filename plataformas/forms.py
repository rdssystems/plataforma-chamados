from django import forms

from config.formularios import FormularioBootstrap
from .models import Plataforma


class PlataformaForm(FormularioBootstrap, forms.ModelForm):
    class Meta:
        model = Plataforma
        fields = ['nome', 'descricao', 'url', 'cor', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={
                'placeholder': 'Ex: Portal do Cliente, App Mobile, API Financeira'
            }),
            'descricao': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Breve descrição da plataforma e tecnologias...'
            }),
            'url': forms.URLInput(attrs={
                'placeholder': 'https://exemplo.com'
            }),
            'cor': forms.TextInput(attrs={
                'type': 'color',
            }),
            'ativa': forms.CheckboxInput(attrs={}),
        }
