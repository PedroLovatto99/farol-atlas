"""Segurança da API (constituição, princípio VIII): só leitura, CORS fechado, sem segredos
vazados e texto de alerta sempre como texto.
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from farol.api.app import criar_app, sessao_da_requisicao
from farol.api.dependencias import relogio_da_requisicao
from farol.dominio import (
    Alerta,
    Classificacao,
    ExecucaoColeta,
    NivelAlerta,
    NivelTerritorio,
    StatusClassificacao,
    TipoExecucao,
)
from farol.dominio.seed import executar
from farol.infra import Configuracoes

if TYPE_CHECKING:
    from tests.conftest import RelogioFalso

DADOS = Path(__file__).resolve().parents[4] / "dados"
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
ORIGEM_PERMITIDA = "http://localhost:5173"
ORIGEM_DE_FORA = "https://site-malicioso.exemplo"
ROTAS = ["/api/v1/mapa", "/api/v1/paises/US", "/api/v1/saude", "/api/v1/openapi.json"]

SENHA_DO_BANCO = "senha-secreta-do-banco-9f3a"
CHAVE_DO_LLM = "chave-secreta-do-llm-71cd"
URL_DO_BANCO = f"postgresql+psycopg://usuario-secreto:{SENHA_DO_BANCO}@127.0.0.1:1/farol"


def configuracoes() -> Configuracoes:
    return Configuracoes(
        database_url=SecretStr(URL_DO_BANCO),
        google_api_key=SecretStr(CHAVE_DO_LLM),
        cors_origens=[ORIGEM_PERMITIDA],
        api_docs_habilitada=True,
    )


def cliente_com_sessao(sessao: Session, relogio: "RelogioFalso") -> TestClient:
    app = criar_app(configuracoes())

    def fornecer_sessao() -> Iterator[Session]:
        yield sessao

    app.dependency_overrides[sessao_da_requisicao] = fornecer_sessao
    app.dependency_overrides[relogio_da_requisicao] = lambda: relogio
    return TestClient(app, raise_server_exceptions=False)


def alerta_com_html(sessao: Session, titulo: str, corpo_html: str) -> None:
    execucao = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS, iniciada_em=AGORA, finalizada_em=AGORA, completa=True
    )
    sessao.add(execucao)
    sessao.flush()
    hash_do_alerta = "a" * 64
    alerta = Alerta(
        url="https://www.gov.br/mre/alerta-html",
        titulo=titulo,
        texto=corpo_html,
        html_corpo=corpo_html,
        publicado_em=AGORA,
        primeira_coleta_em=AGORA,
        ultima_coleta_em=AGORA,
        hash=hash_do_alerta,
        confirmado_execucao_id=execucao.id,
        confirmado_hash=hash_do_alerta,
        confirmado_titulo=titulo,
        confirmado_data_ref=AGORA,
    )
    sessao.add(alerta)
    sessao.flush()
    classificacao = Classificacao(
        alerta_id=alerta.id,
        alerta_hash=hash_do_alerta,
        status=StatusClassificacao.OK,
        e_alerta_de_viagem=True,
        modelo="modelo-falso",
        classificado_em=AGORA,
    )
    sessao.add(classificacao)
    sessao.flush()
    sessao.add(
        NivelTerritorio(
            classificacao_id=classificacao.id,
            territorio_codigo="US",
            nivel_pais=NivelAlerta.EVITAR,
            regioes=[],
        )
    )
    sessao.flush()


# --------------------------------------------------------------------------- só leitura
def test_nenhuma_rota_da_api_aceita_escrita() -> None:
    """Varre as rotas pelo OpenAPI, que lista todas as que a API publica."""
    rotas = criar_app(configuracoes()).openapi()["paths"]
    assert "/api/v1/mapa" in rotas  # a varredura enxerga as rotas de verdade
    for caminho, operacoes in rotas.items():
        assert set(operacoes) == {"get"}, f"{caminho} aceita {set(operacoes)}"


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("caminho", ["/api/v1/mapa", "/api/v1/paises/US", "/api/v1/saude"])
def test_escrita_e_recusada_em_json(
    sessao: Session, relogio: "RelogioFalso", metodo: str, caminho: str
) -> None:
    resposta = cliente_com_sessao(sessao, relogio).request(metodo.upper(), caminho, json={"x": 1})
    assert resposta.status_code == 405
    assert resposta.headers["content-type"].startswith("application/json")


# --------------------------------------------------------------------------- CORS
@pytest.mark.parametrize("caminho", ROTAS)
def test_origem_nao_listada_nao_recebe_permissao_de_cors(
    sessao: Session, relogio: "RelogioFalso", caminho: str
) -> None:
    resposta = cliente_com_sessao(sessao, relogio).get(caminho, headers={"Origin": ORIGEM_DE_FORA})
    assert "access-control-allow-origin" not in resposta.headers
    assert "access-control-allow-credentials" not in resposta.headers


def test_pre_voo_de_origem_nao_listada_e_recusado(sessao: Session, relogio: "RelogioFalso") -> None:
    resposta = cliente_com_sessao(sessao, relogio).options(
        "/api/v1/mapa",
        headers={"Origin": ORIGEM_DE_FORA, "Access-Control-Request-Method": "GET"},
    )
    assert resposta.status_code == 400
    assert "access-control-allow-origin" not in resposta.headers


def test_origem_listada_recebe_so_o_necessario(sessao: Session, relogio: "RelogioFalso") -> None:
    resposta = cliente_com_sessao(sessao, relogio).options(
        "/api/v1/mapa",
        headers={"Origin": ORIGEM_PERMITIDA, "Access-Control-Request-Method": "GET"},
    )
    assert resposta.headers["access-control-allow-origin"] == ORIGEM_PERMITIDA
    assert resposta.headers["access-control-allow-methods"] == "GET"
    assert "access-control-allow-credentials" not in resposta.headers  # sem cookies nem login


def test_cors_sem_origens_configuradas_nao_libera_nenhuma(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    config = Configuracoes(database_url=SecretStr(URL_DO_BANCO), cors_origens=[])
    app = criar_app(config)
    resposta = TestClient(app, raise_server_exceptions=False).get(
        "/api/v1/openapi.json", headers={"Origin": ORIGEM_PERMITIDA}
    )
    assert "access-control-allow-origin" not in resposta.headers


# --------------------------------------------------------------------------- segredos
def tudo_o_que_a_api_devolve(cliente: TestClient) -> str:
    """Corpo e cabeçalhos de uma bateria de requisições, incluindo erros."""
    pedidos = [
        *ROTAS,
        "/api/v1/paises/ZZZ",  # 404
        "/api/v1/paises/!!!",  # 422
        "/api/v1/nao-existe",  # 404 de rota
        "/docs",
        "/redoc",
    ]
    partes = []
    for caminho in pedidos:
        resposta = cliente.get(caminho, headers={"Origin": ORIGEM_PERMITIDA})
        partes.append(resposta.text)
        partes.append(json.dumps(dict(resposta.headers)))
    return "\n".join(partes)


def test_nenhum_segredo_aparece_nas_respostas_nem_no_openapi(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)
    saida = tudo_o_que_a_api_devolve(cliente_com_sessao(sessao, relogio))
    for segredo in (SENHA_DO_BANCO, CHAVE_DO_LLM, "usuario-secreto"):
        assert segredo not in saida


def test_os_segredos_da_configuracao_nao_aparecem_em_repr_str_nem_json() -> None:
    config = configuracoes()
    for texto in (repr(config), str(config), config.model_dump_json()):
        assert SENHA_DO_BANCO not in texto
        assert CHAVE_DO_LLM not in texto


def test_falha_real_do_banco_nao_vaza_senha_nem_na_resposta_nem_no_log(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Um banco que não responde: o erro é registrado, mas sem a senha da URL.

    O log da API sai em JSON na saída padrão (`configurar_logs`), então é de lá que se lê.
    """
    engine = create_engine(URL_DO_BANCO, connect_args={"connect_timeout": 1})
    app = criar_app(configuracoes())  # configura o log para a saída padrão deste teste

    def sessao_do_banco_fora() -> Iterator[Session]:
        with Session(engine) as sessao:
            yield sessao

    app.dependency_overrides[sessao_da_requisicao] = sessao_do_banco_fora
    cliente = TestClient(app, raise_server_exceptions=False)

    respostas = [cliente.get(caminho) for caminho in ("/api/v1/mapa", "/api/v1/saude")]
    registro = capsys.readouterr().out
    engine.dispose()

    assert {r.status_code for r in respostas} == {500, 503}
    assert "erro inesperado" in registro  # o 500 foi mesmo registrado, com a causa
    for segredo in (SENHA_DO_BANCO, CHAVE_DO_LLM):
        assert segredo not in registro
        assert all(segredo not in r.text for r in respostas)


# --------------------------------------------------------------------------- texto é texto
MARCACAO = '<script>alert("xss")</script><img src=x onerror=alert(1)> & <b>negrito</b>'


def test_html_no_titulo_do_alerta_sai_como_texto_no_json(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)
    alerta_com_html(sessao, titulo=MARCACAO, corpo_html=f"<p>{MARCACAO}</p>")

    resposta = cliente_com_sessao(sessao, relogio).get("/api/v1/paises/US")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/json")  # nunca text/html
    [alerta] = resposta.json()["alertas"]
    assert alerta["titulo"] == MARCACAO  # exatamente o texto, sem interpretar nem escapar
    assert alerta["url"] == "https://www.gov.br/mre/alerta-html"


def test_o_html_guardado_do_corpo_do_alerta_nunca_sai_pela_api(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)
    alerta_com_html(sessao, titulo="Alerta", corpo_html="<p>conteudo-so-do-banco-77</p>")

    cliente = cliente_com_sessao(sessao, relogio)
    for caminho in ("/api/v1/paises/US", "/api/v1/mapa"):
        texto = cliente.get(caminho).text
        assert "conteudo-so-do-banco-77" not in texto
        assert "html_corpo" not in texto
