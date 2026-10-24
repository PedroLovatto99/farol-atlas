"""A rodada real não coleta sem um contato de verdade no User-Agent (princípio IV)."""

import pytest
from pydantic import SecretStr

from farol.infra import Configuracoes
from farol.worker import CONTATO_DE_EXEMPLO, ContatoInvalido, rodada_real


def configuracao(contato: str | None) -> Configuracoes:
    return Configuracoes(
        database_url=SecretStr("postgresql+psycopg://x:y@banco-que-nao-existe/z"),
        contato_coleta=contato,
    )


@pytest.mark.parametrize("contato", [None, "", "   ", CONTATO_DE_EXEMPLO])
def test_sem_contato_de_verdade_a_coleta_nem_comeca(contato: str | None) -> None:
    # o erro vem antes de qualquer acesso ao banco ou à rede
    with pytest.raises(ContatoInvalido, match="CONTATO_COLETA"):
        rodada_real(configuracao(contato))
