"""Entende a pergunta antes de chamar o modelo: de que país se fala.

O país vem da pergunta atual e, na falta, das mensagens anteriores DA PESSOA, da mais recente para a
mais antiga (D6). O que o assistente disse antes nunca conta (o navegador pode forjar o histórico),
e o país aberto no mapa também não. Sem país ou com nome ambíguo (Congo, Guiné), a resposta é uma
pergunta de volta, feita pelo código, sem chamar o modelo.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from farol.chat.protocolos import PaisEncontrado, ResolvedorDePaises


@dataclass(frozen=True)
class MensagemAnterior:
    papel: Literal["pessoa", "assistente"]
    texto: str


@dataclass(frozen=True)
class Entendimento:
    paises: tuple[PaisEncontrado, ...] = ()
    pergunta_de_volta: str | None = None


PERGUNTA_SEM_PAIS = (
    "De qual país você está falando? Diga o nome do país ou do território "
    "e eu busco nos alertas e nos dados do site."
)


def _opcoes(candidatos: tuple[PaisEncontrado, ...]) -> str:
    nomes = [c.nome for c in candidatos]
    return f"{', '.join(nomes[:-1])} ou {nomes[-1]}" if len(nomes) > 1 else nomes[0]


def entender(
    pergunta: str, historico: Sequence[MensagemAnterior], resolvedor: ResolvedorDePaises
) -> Entendimento:
    atual = resolvedor.resolver(pergunta)
    if atual.ambiguos:
        return Entendimento(
            pergunta_de_volta=f"Qual destes você quis dizer: {_opcoes(atual.ambiguos[0])}?"
        )
    if atual.encontrados:
        return Entendimento(paises=atual.encontrados)
    for mensagem in reversed(historico):
        if mensagem.papel != "pessoa":
            continue
        anterior = resolvedor.resolver(mensagem.texto)
        if anterior.encontrados and not anterior.ambiguos:
            return Entendimento(paises=anterior.encontrados)
    return Entendimento(pergunta_de_volta=PERGUNTA_SEM_PAIS)
