"""POST /api/v1/chat: fluxo `text/event-stream`, validação, chat desligado e erros no fluxo.

O pipeline é o de verdade (banco de teste, alertas reais de teste, índice com o embeddador falso);
só o modelo de linguagem é o falso roteirizado. Nada de rede nem de chave.
"""

import json
import time
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import BaseMessage
from pydantic import SecretStr
from sqlalchemy.orm import Session
from tests.falsos_chat import (
    EmbeddadorFalso,
    ModeloDeChatFalso,
    RelogioFixo,
    carregar_alertas,
    chamar,
    responder,
    vigor_do_arquivo,
)

from farol.api.app import criar_app, sessao_da_requisicao
from farol.api.chat import ConsultaDeNivelDoSite, ResolvedorDePaisesDoSite, fabrica_do_pipeline
from farol.api.dtos import EventoErro, EventoProgresso, EventoResposta
from farol.chat import ModeloDoChat, PipelineDoChat, RecuperadorDeTrechos, indexar_pendentes
from farol.dominio import TrechoAlertaRepositorio
from farol.infra import Configuracoes

ROTA = "/api/v1/chat"
PERGUNTA = "o que o Itamaraty recomenda para quem está no Irã?"
PROSA = "Para quem já está no Irã, o Itamaraty recomenda seguir as autoridades locais."


@pytest.fixture
def indexado(sessao: Session) -> Session:
    ids = carregar_alertas(sessao)
    embeddador = EmbeddadorFalso()
    indexar_pendentes(
        sessao,
        embeddador,
        vigor_do_arquivo(ids),
        modelo=embeddador.modelo,
        dimensoes=embeddador.dimensoes,
        relogio=RelogioFixo(),
    )
    return sessao


class Montagem:
    """O app de teste e o que a fábrica do pipeline recebeu."""

    def __init__(self, sessao: Session, roteiro: Sequence[Any], **campos: Any) -> None:
        self.modelo = ModeloDeChatFalso(roteiro=list(roteiro))
        self.pipelines_criados = 0
        config = Configuracoes(
            database_url=SecretStr("postgresql+psycopg://x:y@nao-existe/z"),
            cache_ttl_segundos=0,
            limite_pedidos_por_minuto=0,
            cors_origens=["https://farol.exemplo"],
            **{"chat_habilitado": True, **campos},
        )
        app = criar_app(config)

        def fornecer_sessao() -> Iterator[Session]:
            yield sessao

        def fabrica() -> Callable[[], PipelineDoChat]:
            def criar() -> PipelineDoChat:
                self.pipelines_criados += 1
                embeddador = EmbeddadorFalso()
                return PipelineDoChat(
                    modelo=ModeloDoChat(self.modelo),
                    resolvedor=ResolvedorDePaisesDoSite(sessao),
                    consulta_de_nivel=ConsultaDeNivelDoSite(sessao),
                    recuperador=RecuperadorDeTrechos(
                        sessao, embeddador, modelo=embeddador.modelo, dimensoes=embeddador.dimensoes
                    ),
                    alertas=TrechoAlertaRepositorio(sessao),
                )

            return criar

        app.dependency_overrides[sessao_da_requisicao] = fornecer_sessao
        app.dependency_overrides[fabrica_do_pipeline] = fabrica
        self.cliente = TestClient(app, raise_server_exceptions=False)


def eventos(texto: str) -> list[tuple[str, dict[str, Any]]]:
    """Os eventos do fluxo SSE, na ordem: `(nome, dados)`."""
    saida = []
    for bloco in texto.replace("\r\n", "\n").strip().split("\n\n"):
        campos = dict(linha.split(": ", 1) for linha in bloco.split("\n") if ": " in linha)
        saida.append((campos["event"], json.loads(campos["data"])))
    return saida


def corpo(
    pergunta: str = PERGUNTA, historico: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    return {"pergunta": pergunta, "historico": historico or []}


def buscar_ira() -> Any:
    return chamar("buscar_nos_alertas", consulta="recomendações para quem está no Irã", pais="IR")


# ------------------------------------------------------------------------------ fluxo
def test_devolve_o_fluxo_de_eventos_com_progresso_e_uma_resposta(indexado: Session) -> None:
    montagem = Montagem(indexado, [buscar_ira(), responder(PROSA)])

    resposta = montagem.cliente.post(ROTA, json=corpo())

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/event-stream")
    recebidos = eventos(resposta.text)
    assert [nome for nome, _ in recebidos] == ["progresso", "progresso", "progresso", "resposta"]
    assert [dados["etapa"] for _, dados in recebidos[:3]] == [
        "identificando_pais",
        "buscando_nos_alertas",
        "montando_resposta",
    ]
    for _, dados in recebidos[:3]:
        EventoProgresso.model_validate(dados)
    final = EventoResposta.model_validate(recebidos[-1][1])
    assert final.situacao == "resposta" and final.texto == PROSA
    assert final.cartoes == []
    assert final.citacoes and all(c.tipo == "alerta" and c.trecho for c in final.citacoes)


def test_o_fluxo_nao_e_comprimido_nem_guardado(indexado: Session) -> None:
    montagem = Montagem(indexado, [buscar_ira(), responder(PROSA)])

    resposta = montagem.cliente.post(ROTA, json=corpo(), headers={"Accept-Encoding": "gzip"})

    assert "content-encoding" not in resposta.headers
    assert resposta.headers["cache-control"] == "no-store"


def test_pergunta_sem_pais_responde_com_pergunta_de_volta(indexado: Session) -> None:
    montagem = Montagem(indexado, [])

    recebidos = eventos(montagem.cliente.post(ROTA, json=corpo("Posso levar remédios?")).text)

    assert recebidos[-1][0] == "resposta"
    assert recebidos[-1][1]["situacao"] == "pergunta_de_volta"
    assert montagem.modelo.recebidas == []


def test_o_historico_da_pessoa_da_o_pais_do_seguimento(indexado: Session) -> None:
    montagem = Montagem(indexado, [buscar_ira(), responder(PROSA)])
    historico = [
        {"papel": "pessoa", "texto": "Como está o Irã?"},
        {"papel": "assistente", "texto": "Há um alerta de não viajar."},
    ]

    recebidos = eventos(
        montagem.cliente.post(ROTA, json=corpo("E se eu já estiver lá?", historico)).text
    )

    assert recebidos[-1][1]["situacao"] == "resposta"


def test_servico_fora_do_ar_vira_evento_de_erro(indexado: Session) -> None:
    montagem = Montagem(indexado, [RuntimeError("fora do ar")])

    resposta = montagem.cliente.post(ROTA, json=corpo())

    assert resposta.status_code == 200  # o erro chega dentro do fluxo
    nome, dados = eventos(resposta.text)[-1]
    assert nome == "erro"
    erro = EventoErro.model_validate(dados)
    assert erro.codigo == "servico_indisponivel" and erro.pode_tentar_de_novo


def test_estouro_do_prazo_vira_tempo_esgotado(indexado: Session) -> None:
    def demora(mensagens: list[BaseMessage]) -> Any:
        time.sleep(1.5)
        return responder(PROSA)

    montagem = Montagem(indexado, [demora], chat_tempo_maximo_segundos=1)

    nome, dados = eventos(montagem.cliente.post(ROTA, json=corpo()).text)[-1]

    assert (nome, dados["codigo"]) == ("erro", "tempo_esgotado")


# ------------------------------------------------------------------------------ antes do fluxo
def test_chat_desligado_responde_503_sem_montar_o_pipeline(indexado: Session) -> None:
    montagem = Montagem(indexado, [], chat_habilitado=False)

    resposta = montagem.cliente.post(ROTA, json=corpo())

    assert resposta.status_code == 503
    assert resposta.headers["content-type"].startswith("application/json")
    assert resposta.json()["codigo"] == "chat_desligado"
    assert resposta.json()["detalhe"]
    assert montagem.pipelines_criados == 0


@pytest.mark.parametrize(
    "invalido",
    [
        {"pergunta": "", "historico": []},
        {"pergunta": "   ", "historico": []},
        {"pergunta": "x" * 501, "historico": []},
        {"pergunta": "oi\x07", "historico": []},
        {"pergunta": "oi"},
        {"pergunta": "oi", "historico": [{"papel": "pessoa", "texto": "a"}] * 7},
        {"pergunta": "oi", "historico": [{"papel": "sistema", "texto": "a"}]},
        {"pergunta": "oi", "historico": [{"papel": "pessoa", "texto": "x" * 1501}]},
        {"pergunta": "oi", "historico": [], "pais_selecionado": "IR"},
    ],
)
def test_corpo_invalido_e_422_em_json_e_nao_chega_ao_pipeline(
    indexado: Session, invalido: dict[str, Any]
) -> None:
    montagem = Montagem(indexado, [])

    resposta = montagem.cliente.post(ROTA, json=invalido)

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith("application/json")
    assert "detalhe" in resposta.json()
    assert montagem.pipelines_criados == 0


def test_pergunta_de_500_caracteres_e_aceita(indexado: Session) -> None:
    montagem = Montagem(indexado, [])
    resposta = montagem.cliente.post(ROTA, json=corpo("x" * 500))
    assert resposta.status_code == 200


def test_os_espacos_das_pontas_nao_contam(indexado: Session) -> None:
    montagem = Montagem(indexado, [])
    resposta = montagem.cliente.post(ROTA, json=corpo("  " + "x" * 500 + "  "))
    assert resposta.status_code == 200


def test_get_no_chat_nao_existe(indexado: Session) -> None:
    resposta = Montagem(indexado, []).cliente.get(ROTA)
    assert resposta.status_code == 405
