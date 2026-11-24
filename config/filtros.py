"""Leitura e validação dos filtros de consulta (parâmetros GET).

Padrão da Secretaria, "Filtro inválido": preservar as entradas, identificar o campo e
suspender os resultados dependentes até a correção. Por isso nada aqui lança exceção:
cada leitura devolve o valor limpo (ou None) e registra a mensagem em `erros[nome]`.
"""
from datetime import date


class Filtros:
    def __init__(self, params):
        self.params = params
        self.erros = {}
        self.brutos = {}

    @property
    def validos(self):
        return not self.erros

    def _ler(self, nome):
        valor = (self.params.get(nome) or '').strip()
        self.brutos[nome] = valor
        return valor

    def opcao(self, nome, opcoes, mensagem):
        """Valor que precisa estar entre as chaves de `opcoes` (lista de pares ou de valores)."""
        valor = self._ler(nome)
        if not valor:
            return None
        validas = {o[0] if isinstance(o, (list, tuple)) else o for o in opcoes}
        if valor not in validas:
            self.erros[nome] = mensagem
            return None
        return valor

    def registro(self, nome, queryset, mensagem):
        """Id de um registro que precisa existir no queryset permitido."""
        valor = self._ler(nome)
        if not valor:
            return None
        if not valor.isdigit() or not queryset.filter(pk=int(valor)).exists():
            self.erros[nome] = mensagem
            return None
        return int(valor)

    def id_entre(self, nome, ids_validos, mensagem):
        """Id que precisa estar entre os já carregados para o formulário (sem consulta extra)."""
        valor = self._ler(nome)
        if not valor:
            return None
        if not valor.isdigit() or int(valor) not in set(ids_validos):
            self.erros[nome] = mensagem
            return None
        return int(valor)

    def data(self, nome, mensagem='Informe uma data válida.'):
        valor = self._ler(nome)
        if not valor:
            return None
        try:
            return date.fromisoformat(valor)
        except ValueError:
            self.erros[nome] = mensagem
            return None

    def periodo(self, inicio, fim, nome_fim='data_fim'):
        if inicio and fim and fim < inicio:
            self.erros[nome_fim] = 'A data final deve ser igual ou posterior à inicial.'
            return False
        return True

    def texto(self, nome, maximo=100):
        return self._ler(nome)[:maximo]
