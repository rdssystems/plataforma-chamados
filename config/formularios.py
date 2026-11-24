"""Formulários no padrão visual da Secretaria (Bootstrap 5.3).

O mixin aplica a classe Bootstrap certa a cada campo pelo tipo do widget e, após a
validação, marca os campos com erro (`is-invalid`, `aria-invalid`) e liga a mensagem
de erro e o texto de ajuda ao campo (`aria-describedby`), como pede o padrão:
"Exiba mensagens de erro junto aos campos e associe-as ao controle".

Os templates renderizam cada campo com `templates/partials/campo.html`, que usa os
mesmos ids (`<id do campo>-erro`, `<id do campo>-ajuda`).
"""
from django import forms


def _classe_bootstrap(widget):
    if isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
        return ''
    if isinstance(widget, forms.CheckboxInput):
        return 'form-check-input'
    if isinstance(widget, (forms.Select, forms.SelectMultiple)):
        return 'form-select'
    if widget.attrs.get('type') == 'color' or getattr(widget, 'input_type', '') == 'color':
        return 'form-control form-control-color'
    return 'form-control'


class FormularioBootstrap:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            classe = _classe_bootstrap(campo.widget)
            if classe:
                atuais = campo.widget.attrs.get('class', '').split()
                campo.widget.attrs['class'] = ' '.join(dict.fromkeys(atuais + classe.split()))
            if campo.help_text:
                self._descrever(nome, 'ajuda')

    def _id_campo(self, nome):
        return self[nome].auto_id or f'id_{nome}'

    def _descrever(self, nome, sufixo):
        attrs = self.fields[nome].widget.attrs
        alvo = f'{self._id_campo(nome)}-{sufixo}'
        ids = attrs.get('aria-describedby', '').split()
        if alvo not in ids:
            attrs['aria-describedby'] = ' '.join(ids + [alvo])

    def full_clean(self):
        super().full_clean()
        for nome in self.errors:
            if nome not in self.fields:
                continue
            attrs = self.fields[nome].widget.attrs
            classes = attrs.get('class', '').split()
            if 'is-invalid' not in classes:
                attrs['class'] = ' '.join(classes + ['is-invalid'])
            attrs['aria-invalid'] = 'true'
            self._descrever(nome, 'erro')
