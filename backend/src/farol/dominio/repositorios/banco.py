"""Verificação de que o banco responde (usada por /saude)."""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class BancoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def responde(self) -> bool:
        try:
            return self._sessao.execute(select(1)).scalar() == 1
        except SQLAlchemyError:
            return False
