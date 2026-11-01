"""Uma pergunta ao chat, de ponta a ponta (contracts/ferramentas-do-chat.md, seção 4).

    [código] entender a pergunta ──► sem país ou ambíguo: pergunta de volta (sem chamar o modelo)
                                 ──► sem nenhuma coleta ainda: "ainda não há dados"
    [modelo] agente com a ferramenta de busca ──► RespostaDoModelo (prosa, assuntos, situação)
    [código] verificador de prosa ──► violação: contingência (só os trechos, frase fixa)
    [código] montador: citações e "Ver trecho" a partir dos artefatos ──► evento `resposta`

Os eventos de progresso saem nos pontos reais (quando a ferramenta é de fato chamada). O prazo
de 20 s é de `com_prazo`, que corta a pergunta no meio e devolve `tempo_esgotado`. Nada da
pergunta nem da resposta vai a log: só códigos de evento e tipos de erro.

Falha do provedor do modelo e falha do nosso código (ferramenta, banco, verificador) chegam à pessoa
com a mesma mensagem, mas não se confundem: a primeira é `servico_indisponivel` e conta em
`falhas_servico`; a segunda é `erro_interno`, conta em `erros_internos` e vai ao log como erro, com
o lugar do código onde estourou.
"""

import traceback
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import anyio
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

import farol
from farol.chat.agente import RespostaDoModelo, criar_agente
from farol.chat.entendimento import MensagemAnterior, entender
from farol.chat.ferramentas import (
    ContextoDaPergunta,
    FonteDeAlertas,
    Recuperador,
    TrechoUsado,
    criar_ferramentas,
)
from farol.chat.modelo import ModeloDoChat
from farol.chat.montador import (
    RespostaMontada,
    montar_contingencia,
    montar_pergunta_de_volta,
    montar_resposta,
    montar_sem_dados,
)
from farol.chat.protocolos import ConsultaDeNivel, NivelConsultado, ResolvedorDePaises
from farol.chat.verificador import verificar_prosa
from farol.infra import obter_logger

_log = obter_logger("farol.chat")
_PACOTE = Path(farol.__file__).parent

Etapa = Literal[
    "identificando_pais",
    "buscando_nos_alertas",
    "consultando_nivel",
    "consultando_visto",
    "consultando_postos",
    "montando_resposta",
]
MENSAGENS_DE_PROGRESSO: dict[str, str] = {
    "identificando_pais": "Identificando o país…",
    "buscando_nos_alertas": "Buscando nos alertas…",
    "consultando_nivel": "Consultando o nível de alerta…",
    "consultando_visto": "Consultando o visto…",
    "consultando_postos": "Consultando os postos…",
    "montando_resposta": "Montando a resposta…",
}
ETAPA_DA_FERRAMENTA: dict[str, Etapa] = {"buscar_nos_alertas": "buscando_nos_alertas"}

MENSAGEM_SERVICO_INDISPONIVEL = (
    "O assistente está fora do ar agora. O mapa e o painel dos países continuam funcionando; "
    "tente de novo em alguns minutos."
)
MENSAGEM_TEMPO_ESGOTADO = (
    "A resposta demorou mais do que o esperado. Tente de novo; se continuar, consulte o painel do "
    "país no mapa."
)


@dataclass(frozen=True)
class EventoDeProgresso:
    etapa: Etapa
    mensagem: str


@dataclass(frozen=True)
class EventoDeResposta:
    resposta: RespostaMontada


@dataclass(frozen=True)
class EventoDeErro:
    codigo: Literal["servico_indisponivel", "tempo_esgotado", "erro_interno"]
    mensagem: str
    pode_tentar_de_novo: bool


EventoDoChat = EventoDeProgresso | EventoDeResposta | EventoDeErro


def _progresso(etapa: Etapa) -> EventoDeProgresso:
    return EventoDeProgresso(etapa, MENSAGENS_DE_PROGRESSO[etapa])


def _onde_no_nosso_codigo(erro: BaseException) -> str | None:
    """`arquivo:linha` do ponto mais fundo do pacote `farol` por onde o erro passou, sem contar o
    quadro que o pegou; nulo se ele veio só de fora (o provedor do modelo, a rede)."""
    onde = None
    for quadro, linha in list(traceback.walk_tb(erro.__traceback__))[1:]:
        arquivo = Path(quadro.f_code.co_filename)
        if arquivo.is_relative_to(_PACOTE):
            onde = f"{arquivo.relative_to(_PACOTE).as_posix()}:{linha}"
    return onde


class _NivelMemorizado:
    """A mesma consulta de nível, guardada durante uma pergunta (sem repetir o painel)."""

    def __init__(self, consulta: ConsultaDeNivel) -> None:
        self._consulta = consulta
        self._guardados: dict[str, NivelConsultado] = {}

    def consultar(self, codigo: str) -> NivelConsultado:
        if codigo not in self._guardados:
            self._guardados[codigo] = self._consulta.consultar(codigo)
        return self._guardados[codigo]


class PipelineDoChat:
    def __init__(
        self,
        *,
        modelo: ModeloDoChat | None,
        resolvedor: ResolvedorDePaises,
        consulta_de_nivel: ConsultaDeNivel,
        recuperador: Recuperador,
        alertas: FonteDeAlertas,
        contar: Callable[[str], None] = lambda chave: None,
        limite_de_trechos: int = 4,
    ) -> None:
        self._modelo = modelo
        self._resolvedor = resolvedor
        self._consulta_de_nivel = consulta_de_nivel
        self._recuperador = recuperador
        self._alertas = alertas
        self._contar = contar
        self._limite_de_trechos = limite_de_trechos

    async def perguntar(
        self, pergunta: str, historico: Sequence[MensagemAnterior] = ()
    ) -> AsyncIterator[EventoDoChat]:
        try:
            async for evento in self._perguntar(pergunta, historico):
                yield evento
        except Exception as erro:
            # só o tipo e o lugar vão ao log: a mensagem do erro pode repetir a pergunta
            _log.error(
                "erro interno no chat: %s em %s",
                type(erro).__name__,
                _onde_no_nosso_codigo(erro) or "?",
            )
            self._contar("erros_internos")
            yield EventoDeErro("erro_interno", MENSAGEM_SERVICO_INDISPONIVEL, True)

    async def _perguntar(
        self, pergunta: str, historico: Sequence[MensagemAnterior]
    ) -> AsyncIterator[EventoDoChat]:
        yield _progresso("identificando_pais")
        entendimento = entender(pergunta, historico, self._resolvedor)
        if entendimento.pergunta_de_volta is not None:
            self._contar("pergunta_de_volta")
            yield EventoDeResposta(montar_pergunta_de_volta(entendimento.pergunta_de_volta))
            return

        nivel = _NivelMemorizado(self._consulta_de_nivel)
        if not nivel.consultar(entendimento.paises[0].codigo).dados_obtidos:
            yield EventoDeResposta(montar_sem_dados())
            return
        if self._modelo is None:
            yield EventoDeErro("servico_indisponivel", MENSAGEM_SERVICO_INDISPONIVEL, True)
            return

        contexto = ContextoDaPergunta(
            paises=entendimento.paises,
            recuperador=self._recuperador,
            consulta_de_nivel=nivel,
            alertas=self._alertas,
            contar=self._contar,
            limite_de_trechos=self._limite_de_trechos,
        )
        agente = criar_agente(self._modelo, criar_ferramentas(contexto))
        paises = ", ".join(f"{p.nome} ({p.codigo})" for p in entendimento.paises)
        entrada = {
            "messages": [HumanMessage(content=f"{pergunta}\n\nPaíses da pergunta: {paises}")]
        }

        trechos: list[TrechoUsado] = []
        estruturada: RespostaDoModelo | None = None
        try:
            async for modo, dados in agente.astream(entrada, stream_mode=["updates", "values"]):
                if modo == "values":
                    estruturada = dados.get("structured_response") or estruturada
                    continue
                for atualizacao in dados.values():
                    for mensagem in (atualizacao or {}).get("messages", []):
                        if isinstance(mensagem, AIMessage):
                            for chamada in mensagem.tool_calls:
                                if etapa := ETAPA_DA_FERRAMENTA.get(chamada["name"]):
                                    yield _progresso(etapa)
                        elif isinstance(mensagem, ToolMessage) and mensagem.artifact:
                            trechos.extend(mensagem.artifact)
        except Exception as erro:
            if _onde_no_nosso_codigo(erro) is not None:
                raise  # estourou numa ferramenta nossa: erro interno, não o modelo fora do ar
            # só o tipo vai ao log: a mensagem do provedor pode repetir a pergunta
            _log.warning("o serviço de linguagem falhou: %s", type(erro).__name__)
            self._contar("falhas_servico")
            yield EventoDeErro("servico_indisponivel", MENSAGEM_SERVICO_INDISPONIVEL, True)
            return

        yield _progresso("montando_resposta")
        yield EventoDeResposta(self._montar(estruturada, trechos, pergunta, contexto))

    def _montar(
        self,
        estruturada: RespostaDoModelo | None,
        trechos: Sequence[TrechoUsado],
        pergunta: str,
        contexto: ContextoDaPergunta,
    ) -> RespostaMontada:
        if estruturada is None:  # o modelo bateu no limite de chamadas sem responder
            self._contar("so_registros")
            return montar_contingencia(trechos)
        if estruturada.situacao != "nao_encontrei":
            violacao = verificar_prosa(
                estruturada.texto,
                trechos=trechos,
                pergunta=pergunta,
                paises=contexto.paises,
                resolvedor=self._resolvedor,
            )
            if violacao is not None:
                _log.info("prosa do modelo descartada pelo verificador: %s", violacao.regra)
                self._contar("so_registros")
                return montar_contingencia(trechos)
        resposta = montar_resposta(estruturada.situacao, estruturada.texto, trechos)
        if resposta.situacao in ("nao_encontrei", "recusa"):
            self._contar("nao_encontrei" if resposta.situacao == "nao_encontrei" else "recusas")
        return resposta


async def com_prazo(
    eventos: AsyncIterator[EventoDoChat], segundos: float
) -> AsyncIterator[EventoDoChat]:
    """Os eventos da pergunta, cortados no prazo com um evento `erro` `tempo_esgotado`.

    O prazo vale para a pergunta inteira; cada espera roda sob o tempo que resta, sem escopo de
    cancelamento aberto entre um `yield` e outro.
    """
    limite = anyio.current_time() + segundos
    iterador = eventos.__aiter__()
    try:
        while True:
            restante = limite - anyio.current_time()
            try:
                with anyio.fail_after(max(restante, 0)):
                    evento = await iterador.__anext__()
            except StopAsyncIteration:
                return
            except TimeoutError:
                yield EventoDeErro("tempo_esgotado", MENSAGEM_TEMPO_ESGOTADO, True)
                return
            yield evento
    finally:
        fechar = getattr(iterador, "aclose", None)
        if fechar is not None:
            with anyio.CancelScope(shield=True):
                await fechar()
