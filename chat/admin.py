from django.contrib import admin

from .models import Conversa, Mensagem


class SomenteLeituraAdmin(admin.ModelAdmin):
    """O histórico do chat é permanente: o admin só consulta."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Conversa)
class ConversaAdmin(SomenteLeituraAdmin):
    list_display = ('chave', 'criada_em', 'atualizada_em')


@admin.register(Mensagem)
class MensagemAdmin(SomenteLeituraAdmin):
    list_display = ('autor', 'conversa', 'criada_em', 'texto')
    list_filter = ('autor',)
    search_fields = ('texto',)
