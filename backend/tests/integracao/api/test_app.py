"""Esqueleto da API: CORS, documentação só em desenvolvimento, JSON sempre e /saude."""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from farol.api.app import criar_app, sessao_da_requisicao
from farol.dominio import Alerta, ExecucaoColeta, TipoExecucao
from farol.infra import Configuracoes

ORIGEM_PERMITIDA = "http://localhost:5173"
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


def configuracoes(**campos: Any) -> Configuracoes:
    base: dict[str, Any] = {
        "database_url": SecretStr("postgresql+psycopg://x:y@banco-que-nao-existe/z"),
        "cors_origens": [ORIGEM_PERMITIDA],
        "api_docs_habilitada": False,
    }
    base.update(campos)
    return Configuracoes(**base)


def cliente(sessao: Session | None = None, **campos: Any) -> TestClient:
    app = criar_app(configuracoes(**campos))
    if sessao is not None:

        def fornecer() -> Iterator[Session]:
            yield sessao

        app.dependency_overrides[sessao_da_requisicao] = fornecer
    return TestClient(app, raise_server_exceptions=False)


# --------------------------------------------------------------------------- CORS
def test_cors_aceita_a_origem_do_frontend() -> None:
    resposta = cliente().get("/api/v1/openapi.json", headers={"Origin": ORIGEM_PERMITIDA})
    assert resposta.headers["access-control-allow-origin"] == ORIGEM_PERMITIDA


def test_cors_nao_aceita_outras_origens() -> None:
    resposta = cliente().get("/api/v1/openapi.json", headers={"Origin": "https://outro.exemplo"})
    assert "access-control-allow-origin" not in resposta.headers


def test_cors_nao_libera_metodos_de_escrita() -> None:
    resposta = cliente().options(
        "/api/v1/saude",
        headers={"Origin": ORIGEM_PERMITIDA, "Access-Control-Request-Method": "POST"},
    )
    assert "POST" not in resposta.headers.get("access-control-allow-methods", "")


# --------------------------------------------------------------------------- documentação
@pytest.mark.parametrize("caminho", ["/docs", "/redoc"])
def test_documentacao_responde_404_quando_desligada(caminho: str) -> None:
    assert cliente(api_docs_habilitada=False).get(caminho).status_code == 404


@pytest.mark.parametrize("caminho", ["/docs", "/redoc"])
def test_documentacao_responde_200_quando_ligada(caminho: str) -> None:
    assert cliente(api_docs_habilitada=True).get(caminho).status_code == 200


@pytest.mark.parametrize("ligada", [False, True])
def test_openapi_json_sempre_disponivel(ligada: bool) -> None:
    resposta = cliente(api_docs_habilitada=ligada).get("/api/v1/openapi.json")
    assert resposta.status_code == 200
    assert "/api/v1/saude" in resposta.json()["paths"]


# --------------------------------------------------------------------------- erros em JSON
def test_rota_inexistente_devolve_erro_em_json() -> None:
    resposta = cliente().get("/api/v1/nao-existe")
    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith("application/json")
    assert "detalhe" in resposta.json()


def test_metodos_de_escrita_nao_existem() -> None:
    resposta = cliente().post("/api/v1/saude")
    assert resposta.status_code == 405
    assert resposta.headers["content-type"].startswith("application/json")


def test_erro_inesperado_vira_json_sem_vazar_detalhes() -> None:
    app = criar_app(configuracoes())

    def quebrar() -> None:
        raise RuntimeError("segredo-interno")

    app.dependency_overrides[sessao_da_requisicao] = quebrar
    resposta = TestClient(app, raise_server_exceptions=False).get("/api/v1/saude")
    assert resposta.status_code == 500
    assert resposta.json() == {"detalhe": "Erro interno"}
    assert "segredo-interno" not in resposta.text


# --------------------------------------------------------------------------- /saude
def test_saude_com_banco_ok_e_sem_coletas(sessao: Session) -> None:
    resposta = cliente(sessao).get("/api/v1/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {
        "banco": "ok",
        "ultima_coleta_completa_em": None,
        "ultima_tentativa_em": None,
        "alertas_pendentes": 0,
    }


def test_saude_mostra_ultimas_coletas_e_alertas_pendentes(sessao: Session) -> None:
    completa = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS, iniciada_em=AGORA, finalizada_em=AGORA, completa=True
    )
    incompleta = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS,
        iniciada_em=datetime(2026, 10, 24, 6, 17, tzinfo=UTC),
        finalizada_em=datetime(2026, 10, 24, 6, 20, tzinfo=UTC),
        completa=False,
    )
    sessao.add_all([completa, incompleta])
    sessao.flush()
    sessao.add(
        Alerta(  # confirmado por coleta completa, mas ainda sem classificação: pendente
            url="https://gov.br/a",
            titulo="Alerta",
            publicado_em=AGORA,
            primeira_coleta_em=AGORA,
            ultima_coleta_em=AGORA,
            hash="a" * 64,
            confirmado_execucao_id=completa.id,
            confirmado_hash="a" * 64,
            confirmado_titulo="Alerta",
            confirmado_data_ref=AGORA,
        )
    )
    sessao.flush()

    corpo = cliente(sessao).get("/api/v1/saude").json()

    assert corpo["ultima_coleta_completa_em"].startswith("2026-10-23T12:00:00")
    assert corpo["ultima_tentativa_em"].startswith("2026-10-24T06:17:00")
    assert corpo["alertas_pendentes"] == 1


class SessaoQueFalha:
    """Sessão cujo banco não responde."""

    def execute(self, *_: object, **__: object) -> None:
        raise OperationalError("select 1", {}, Exception("banco fora do ar"))

    scalar: Callable[..., None] = execute
    scalars: Callable[..., None] = execute


def test_saude_devolve_503_quando_o_banco_nao_responde() -> None:
    app = criar_app(configuracoes())

    def fornecer() -> Iterator[Any]:
        yield SessaoQueFalha()

    app.dependency_overrides[sessao_da_requisicao] = fornecer
    resposta = TestClient(app, raise_server_exceptions=False).get("/api/v1/saude")
    assert resposta.status_code == 503
    assert resposta.json()["banco"] == "falha"
