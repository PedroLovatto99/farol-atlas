"""Versão dos dados: um contador no banco que sobe a cada escrita confirmada.

O cache da API compara a versão guardada com a atual: se mudou, a resposta velha é descartada.
Nenhum job nem comando precisa lembrar de chamar nada: toda sessão aberta por `abrir_sessao` que
gravou algo (objeto novo, alterado, apagado ou UPDATE/DELETE em massa) sobe o contador antes de
confirmar. Leituras e transações desfeitas não sobem.
"""

from sqlalchemy import event, text
from sqlalchemy.orm import ORMExecuteState, Session, UOWTransaction

_MARCA = "escreveu"

_LER = text("SELECT contador FROM versao_dados WHERE id = 1")
_SUBIR = text(
    "INSERT INTO versao_dados (id, contador) VALUES (1, 1) "
    "ON CONFLICT (id) DO UPDATE SET contador = versao_dados.contador + 1"
)


def _marcar_apos_flush(sessao: Session, _contexto: UOWTransaction) -> None:
    if sessao.new or sessao.dirty or sessao.deleted:
        sessao.info[_MARCA] = True


def _marcar_em_massa(estado: ORMExecuteState) -> None:
    if estado.is_update or estado.is_delete or estado.is_insert:
        estado.session.info[_MARCA] = True


event.listen(Session, "after_flush", _marcar_apos_flush)
event.listen(Session, "do_orm_execute", _marcar_em_massa)


def subir_se_escreveu(sessao: Session) -> bool:
    """Sobe o contador se a sessão gravou algo. Chamada logo antes do commit."""
    if not sessao.info.pop(_MARCA, False):
        return False
    sessao.execute(_SUBIR)
    return True


def ler_versao_dos_dados(sessao: Session) -> int:
    """O contador atual (0 se ninguém gravou ainda)."""
    return sessao.execute(_LER).scalar() or 0
