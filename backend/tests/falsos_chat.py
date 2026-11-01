"""Falsos dos testes do chat: nada de rede, de chave nem de modelo real.

`EmbeddadorFalso` vetoriza por "hash de palavras": cada palavra (sem acento, em minúsculas, com
quatro letras ou mais) cai numa posição do vetor, que depois é normalizado. Textos com palavras em
comum ficam próximos, então a busca de teste devolve o que um leitor esperaria, e o resultado é
sempre o mesmo.

`carregar_alertas` grava no banco de teste os alertas de `fixtures/chat/alertas.json` (exportados do
banco de desenvolvimento por `ferramentas/exportar_alertas_para_gabarito.py`), já confirmados e
classificados, como a coleta e a classificação deixariam.
"""

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from farol.dominio import (
    Alerta,
    Classificacao,
    ExecucaoColeta,
    NivelAlerta,
    NivelTerritorio,
    StatusClassificacao,
    Territorio,
    TipoExecucao,
)
from farol.dominio.seed import executar

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
ALERTAS_JSON = RAIZ_BACKEND / "tests" / "fixtures" / "chat" / "alertas.json"
DADOS = RAIZ_BACKEND.parent / "dados"
AGORA = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
MODELO_FALSO = "falso:hash-de-palavras"


class RelogioFixo:
    """Relógio que marca sempre o mesmo instante (cumpre `farol.infra.Relogio`)."""

    def __init__(self, instante: datetime = AGORA + timedelta(hours=1)) -> None:
        self.instante = instante

    def agora(self) -> datetime:
        return self.instante


def _palavras(texto: str) -> list[str]:
    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return [p for p in re.findall(r"[a-z0-9]+", sem_acentos.lower()) if len(p) >= 4]


class EmbeddadorFalso:
    """Cumpre o protocolo `Embeddador`, mais o `modelo` e as `dimensoes` que o índice grava."""

    def __init__(self, dimensoes: int = 256, modelo: str = MODELO_FALSO) -> None:
        self.dimensoes = dimensoes
        self.modelo = modelo
        self.lotes_de_documentos: list[list[str]] = []
        self.perguntas: list[str] = []
        self.falhar_quando: Callable[[str], bool] | None = None
        self.falhar_na_pergunta = False

    @property
    def textos_vetorizados(self) -> int:
        return sum(len(lote) for lote in self.lotes_de_documentos)

    def vetor_de(self, texto: str) -> list[float]:
        vetor = [0.0] * self.dimensoes
        for palavra in _palavras(texto):
            resumo = hashlib.sha256(palavra.encode()).digest()
            posicao = int.from_bytes(resumo[:4], "big") % self.dimensoes
            vetor[posicao] += 1.0
        norma = math.sqrt(sum(v * v for v in vetor))
        if norma == 0:
            vetor[0], norma = 1.0, 1.0
        return [v / norma for v in vetor]

    def vetorizar_documentos(self, textos: Sequence[str]) -> list[Sequence[float]]:
        if self.falhar_quando is not None and any(self.falhar_quando(t) for t in textos):
            raise RuntimeError("cota do serviço de embeddings esgotada (falso)")
        self.lotes_de_documentos.append(list(textos))
        return [self.vetor_de(t) for t in textos]

    def vetorizar_pergunta(self, texto: str) -> Sequence[float]:
        if self.falhar_na_pergunta:
            raise RuntimeError("serviço de embeddings fora do ar (falso)")
        self.perguntas.append(texto)
        return self.vetor_de(texto)


def ler_alertas_json(caminho: Path = ALERTAS_JSON) -> list[dict[str, Any]]:
    return list(json.loads(caminho.read_text(encoding="utf-8"))["alertas"])


def _data(valor: str | None) -> datetime | None:
    return datetime.fromisoformat(valor) if valor else None


def semear_territorios(sessao: Session) -> None:
    if not sessao.scalar(select(func.count()).select_from(Territorio)):
        executar(sessao, DADOS, AGORA)


def hash_do_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()


def gravar_alerta(
    sessao: Session,
    execucao: ExecucaoColeta,
    *,
    url: str,
    titulo: str,
    texto: str,
    html_corpo: str | None = None,
    publicado_em: datetime = AGORA,
    modificado_em: datetime | None = None,
    niveis: Sequence[dict[str, Any]] = (),
    e_alerta_de_viagem: bool = True,
) -> Alerta:
    """Um alerta confirmado pela `execucao` e com classificação `ok` do mesmo conteúdo."""
    resumo = hash_do_texto(texto)
    alerta = Alerta(
        url=url,
        titulo=titulo,
        texto=texto,
        html_corpo=html_corpo,
        publicado_em=publicado_em,
        modificado_em=modificado_em,
        hash=resumo,
        primeira_coleta_em=AGORA,
        ultima_coleta_em=AGORA,
        pagina_lida=True,
        confirmado_execucao_id=execucao.id,
        confirmado_hash=resumo,
        confirmado_titulo=titulo,
        confirmado_data_ref=modificado_em or publicado_em,
    )
    sessao.add(alerta)
    sessao.flush()
    classificacao = Classificacao(
        alerta_id=alerta.id,
        alerta_hash=resumo,
        status=StatusClassificacao.OK,
        e_alerta_de_viagem=e_alerta_de_viagem,
        modelo="falso",
        classificado_em=AGORA,
    )
    sessao.add(classificacao)
    sessao.flush()
    for nivel in niveis:
        sessao.add(
            NivelTerritorio(
                classificacao_id=classificacao.id,
                territorio_codigo=nivel["territorio"],
                nivel_pais=NivelAlerta(nivel["nivel_pais"]) if nivel["nivel_pais"] else None,
                regioes=nivel["regioes"],
            )
        )
    sessao.flush()
    return alerta


def execucao_completa(sessao: Session, finalizada_em: datetime = AGORA) -> ExecucaoColeta:
    execucao = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS,
        iniciada_em=finalizada_em - timedelta(minutes=5),
        finalizada_em=finalizada_em,
        paginas_esperadas=10,
        paginas_lidas=10,
        lista_lida_inteira=True,
        completa=True,
    )
    sessao.add(execucao)
    sessao.flush()
    return execucao


def carregar_alertas(sessao: Session, caminho: Path = ALERTAS_JSON) -> dict[str, int]:
    """Grava os alertas do arquivo (territórios incluídos) e devolve `id lógico -> id no banco`."""
    semear_territorios(sessao)
    execucao = execucao_completa(sessao)
    ids: dict[str, int] = {}
    for item in ler_alertas_json(caminho):
        alerta = gravar_alerta(
            sessao,
            execucao,
            url=item["url"],
            titulo=item["titulo"],
            texto=item["texto"],
            html_corpo=item["html_corpo"],
            publicado_em=_data(item["publicado_em"]) or AGORA,
            modificado_em=_data(item["modificado_em"]),
            niveis=item["niveis"],
            e_alerta_de_viagem=item["e_alerta_de_viagem"],
        )
        ids[item["id"]] = alerta.id
    return ids


def vigor_do_arquivo(
    ids: dict[str, int], caminho: Path = ALERTAS_JSON
) -> dict[int, frozenset[str]]:
    """O `vigor` que o worker calcularia, lido do arquivo (campo `rege` de cada alerta)."""
    return {ids[a["id"]]: frozenset(a["rege"]) for a in ler_alertas_json(caminho) if a["rege"]}


# --------------------------------------------------------------------------- modelo de chat falso
class ModeloDeChatFalso(BaseChatModel):
    """Modelo de chat roteirizado, que aceita `bind_tools` como os de verdade.

    O roteiro é uma lista de passos, um por chamada ao modelo: uma `AIMessage` (use `chamar` e
    `responder`), uma exceção (é lançada) ou uma função que recebe as mensagens e devolve uma
    `AIMessage`. `recebidas` guarda as mensagens de cada chamada, para os testes olharem o prompt.
    """

    roteiro: list[Any] = Field(default_factory=list)
    recebidas: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "falso-roteirizado"

    def bind_tools(self, tools: Sequence[Any], **_: Any) -> Runnable[Any, AIMessage]:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.recebidas.append(list(messages))
        if not self.roteiro:
            raise AssertionError("o roteiro do modelo falso acabou")
        passo = self.roteiro.pop(0)
        if isinstance(passo, BaseException):
            raise passo
        mensagem = passo(messages) if callable(passo) else passo
        return ChatResult(generations=[ChatGeneration(message=mensagem)])


def chamar(ferramenta: str, **argumentos: Any) -> AIMessage:
    """Passo do roteiro: o modelo pede uma ferramenta."""
    identificador = f"chamada-{ferramenta}-{abs(hash(str(argumentos))) % 10**6}"
    return AIMessage(
        content="",
        tool_calls=[{"name": ferramenta, "args": argumentos, "id": identificador}],
    )


def responder(
    texto: str,
    situacao: str = "resposta",
    assuntos: Sequence[str] = ("alertas",),
) -> AIMessage:
    """Passo do roteiro: a resposta final estruturada (`RespostaDoModelo`)."""
    return chamar("RespostaDoModelo", texto=texto, assuntos=list(assuntos), situacao=situacao)
