"""Tradução das observações da fonte: o contrato do tradutor e as regras que valem para qualquer um.

O modelo de linguagem é usado só para traduzir o texto das observações (categoria e prazo nunca
passam por ele). O texto da fonte é dado, não instrução (princípio VIII): o adaptador o coloca entre
delimitadores e a resposta só vale se passar no esquema daqui. Uma falha do tradutor nunca derruba a
coleta: o texto fica sem tradução (aparece em inglês) e é tentado de novo na coleta seguinte.
"""

import re
from collections.abc import Sequence
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from farol.infra import obter_logger

TAMANHO_DO_LOTE = 20  # observações por chamada ao modelo
LIMITE_DA_TRADUCAO = 6000  # caracteres; a maior nota da fonte tem 1500

_log = obter_logger("farol.vistos")
_QUEBRA_DE_LINHA = re.compile(r"\r\n|\r|\n")


class TraducaoInvalida(Exception):
    """A resposta do tradutor não cobre os textos pedidos; o lote inteiro fica sem tradução."""


class Tradutor(Protocol):
    """O que o serviço de coleta usa do tradutor (`TradutorLangChain` ou um falso nos testes)."""

    nome_do_modelo: str

    def traduzir(self, textos: Sequence[str]) -> list[str]:
        """Traduz até `TAMANHO_DO_LOTE` textos para o português, na ordem. Pode levantar erro."""
        ...


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ItemTraduzido(_Estrito):
    indice: int = Field(ge=1, description="Número do item, como aparece no pedido (a partir de 1)")
    traducao: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=LIMITE_DA_TRADUCAO)
    ] = Field(description="A observação em português do Brasil, com as mesmas linhas do original")


class RespostaDaTraducao(_Estrito):
    traducoes: list[ItemTraduzido] = Field(
        max_length=TAMANHO_DO_LOTE, description="Um item por observação do pedido"
    )


def validar_traducoes(resposta: RespostaDaTraducao, textos: Sequence[str]) -> list[str]:
    """As traduções na ordem dos textos; levanta `TraducaoInvalida` se faltar ou sobrar item."""
    quantidade = len(textos)
    if len(resposta.traducoes) != quantidade:
        raise TraducaoInvalida(
            f"o modelo devolveu {len(resposta.traducoes)} traduções para {quantidade} textos"
        )
    por_indice = {item.indice: item.traducao for item in resposta.traducoes}
    if set(por_indice) != set(range(1, quantidade + 1)):
        raise TraducaoInvalida(f"os índices da resposta não são 1 a {quantidade}, um por texto")
    return [por_indice[indice] for indice in range(1, quantidade + 1)]


def _linhas(texto: str) -> list[str]:
    linhas = (" ".join(linha.split()) for linha in _QUEBRA_DE_LINHA.split(texto))
    return [linha for linha in linhas if linha]


def preservar_linhas(original: str, traducao: str) -> str | None:
    """A tradução com as linhas limpas, se tiver tantas linhas quanto o original; senão, nulo.

    Cada linha de uma observação é um item (uma regra, um aviso); uma tradução que junta ou divide
    linhas muda o que o painel mostra, então é descartada e o texto fica em inglês.
    """
    do_original, da_traducao = _linhas(original), _linhas(traducao)
    if not da_traducao or len(do_original) != len(da_traducao):
        return None
    return "\n".join(da_traducao)


def traduzir_em_lotes(tradutor: Tradutor, textos: Sequence[str]) -> dict[str, str]:
    """Traduz os textos (sem repetir) em lotes de até 20; devolve só o que foi bem traduzido.

    Nunca levanta erro: um lote que falha, vem com quantidade errada ou traz uma tradução que não
    preserva as linhas simplesmente não entra no resultado.
    """
    unicos = list(dict.fromkeys(textos))
    traduzidos: dict[str, str] = {}
    for inicio in range(0, len(unicos), TAMANHO_DO_LOTE):
        lote = unicos[inicio : inicio + TAMANHO_DO_LOTE]
        try:
            traducoes = tradutor.traduzir(lote)
        except Exception as erro:
            _log.warning(
                "vistos: tradução do lote de %d observações falhou (%s: %s); "
                "elas aparecem em inglês até a próxima coleta",
                len(lote),
                type(erro).__name__,
                erro,
            )
            continue
        if len(traducoes) != len(lote):
            _log.warning(
                "vistos: tradução descartada: %d traduções para %d observações",
                len(traducoes),
                len(lote),
            )
            continue
        for original, traducao in zip(lote, traducoes, strict=True):
            limpa = preservar_linhas(original, traducao)
            if limpa is None:
                _log.warning("vistos: tradução descartada: ela não preserva as linhas do original")
                continue
            traduzidos[original] = limpa
    return traduzidos
