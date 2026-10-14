from django import forms
from .models import Plataforma


class PlataformaForm(forms.ModelForm):
    class Meta:
        model = Plataforma
        fields = ['nome', 'descricao', 'url', 'cor', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none',
                'placeholder': 'Ex: Portal do Cliente, App Mobile, API Financeira'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none',
                'rows': 3,
                'placeholder': 'Breve descrição da plataforma e tecnologias...'
            }),
            'url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none',
                'placeholder': 'https://exemplo.com'
            }),
            'cor': forms.TextInput(attrs={
                'type': 'color',
                'class': 'h-10 w-20 p-1 border rounded cursor-pointer'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 rounded focus:ring-blue-500'
            }),
        }
