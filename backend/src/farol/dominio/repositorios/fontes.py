"""Fonte e data dos dados do seed (atribuição exibida no painel)."""

from sqlalchemy.orm import Session

from farol.dominio.modelos import FonteDados


class FonteDadosRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def obter(self, chave: str) -> FonteDados | None:
        return self._sessao.get(FonteDados, chave)

    def adicionar(self, fonte: FonteDados) -> None:
        self._sessao.add(fonte)
