"""GET /api/v1/vistos: o DTO do contrato, os territórios de /mapa e número fixo de consultas."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from farol.api.app import criar_app, sessao_da_requisicao
from farol.api.dependencias import relogio_da_requisicao
from farol.dominio import CategoriaDeVisto
from farol.dominio.seed import executar
from farol.infra import Configuracoes

if TYPE_CHECKING:
    from tests.conftest import (
        ColetorDeVistos,
        ContadorDeConsultas,
        GravadorDeVisto,
        RelogioFalso,
    )

DADOS = Path(__file__).resolve().parents[4] / "dados"
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)

CAMPOS_DOS_VISTOS = {"dados_obtidos", "coletado_em", "desatualizado", "fonte", "territorios"}
CAMPOS_DO_TERRITORIO = {"codigo", "situacao", "aceita_rg"}
CAMPOS_DA_FONTE = {"nome", "url", "licenca"}
OITO_DO_RG = {"AR", "BO", "CL", "CO", "EC", "PY", "PE", "UY"}


def cliente(sessao: Session, relogio: "RelogioFalso") -> TestClient:
    app = criar_app(
        Configuracoes(
            database_url=SecretStr("postgresql+psycopg://x:y@nao-existe/z"), cache_ttl_segundos=0
        )
    )

    def fornecer_sessao() -> Iterator[Session]:
        yield sessao

    app.dependency_overrides[sessao_da_requisicao] = fornecer_sessao
    app.dependency_overrides[relogio_da_requisicao] = lambda: relogio
    return TestClient(app, raise_server_exceptions=False)


def com_vistos(
    sessao: Session, relogio: "RelogioFalso", coletar_vistos: "ColetorDeVistos", html: str
) -> TestClient:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html)
    return cliente(sessao, relogio)


# --------------------------------------------------------------------------- sem dados
def test_antes_da_primeira_coleta_nada_foi_obtido_e_todo_territorio_e_sem_informacao(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)

    resposta = cliente(sessao, relogio).get("/api/v1/vistos")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/json")
    corpo = resposta.json()
    assert set(corpo) == CAMPOS_DOS_VISTOS
    assert corpo["dados_obtidos"] is False
    assert corpo["coletado_em"] is None
    assert corpo["desatualizado"] is False
    assert set(corpo["fonte"]) == CAMPOS_DA_FONTE
    por_codigo = {t["codigo"]: t for t in corpo["territorios"]}
    assert por_codigo.pop("BR")["situacao"] == "nao_se_aplica"
    assert {(t["situacao"], t["aceita_rg"]) for t in por_codigo.values()} == {
        ("sem_informacao", False)
    }


# --------------------------------------------------------------------------- com dados
def test_com_dados_devolve_o_dto_do_contrato(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    http = com_vistos(sessao, relogio, coletar_vistos, html_da_wikipedia)

    corpo = http.get("/api/v1/vistos").json()

    assert set(corpo) == CAMPOS_DOS_VISTOS
    assert corpo["dados_obtidos"] is True
    assert corpo["coletado_em"].startswith("2026-10-23T12:00:00")
    assert corpo["desatualizado"] is False
    assert corpo["fonte"] == {
        "nome": "Wikipédia: Visa requirements for Brazilian citizens",
        "url": "https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens",
        "licenca": "CC BY-SA",
    }
    assert {frozenset(t) for t in corpo["territorios"]} == {frozenset(CAMPOS_DO_TERRITORIO)}
    por_codigo = {t["codigo"]: t for t in corpo["territorios"]}
    assert por_codigo["US"] == {"codigo": "US", "situacao": "visto_exigido", "aceita_rg": False}
    assert por_codigo["BR"] == {"codigo": "BR", "situacao": "nao_se_aplica", "aceita_rg": False}


def test_os_territorios_sao_os_mesmos_de_mapa(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    http = com_vistos(sessao, relogio, coletar_vistos, html_da_wikipedia)

    de_vistos = [t["codigo"] for t in http.get("/api/v1/vistos").json()["territorios"]]
    do_mapa = [t["codigo"] for t in http.get("/api/v1/mapa").json()["territorios"]]

    assert de_vistos == do_mapa
    assert len(de_vistos) == len(set(de_vistos)) > 200


def test_kosovo_e_malvinas_trazem_a_situacao_da_propria_linha_e_as_malvinas_nao_tem_rg(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    http = com_vistos(sessao, relogio, coletar_vistos, html_da_wikipedia)

    por_codigo = {t["codigo"]: t for t in http.get("/api/v1/vistos").json()["territorios"]}

    assert por_codigo["XK"] == {"codigo": "XK", "situacao": "isento", "aceita_rg": False}
    assert por_codigo["FK"] == {"codigo": "FK", "situacao": "isento", "aceita_rg": False}
    assert por_codigo["AR"]["aceita_rg"] is True  # a Argentina segue com RG


def test_a_situacao_de_kosovo_e_malvinas_nao_acompanha_o_soberano(
    sessao: Session, relogio: "RelogioFalso", gravar_visto: "GravadorDeVisto"
) -> None:
    executar(sessao, DADOS, AGORA)
    gravar_visto("AR", categoria=CategoriaDeVisto.ISENTO, aceita_rg=True)
    gravar_visto("RS", categoria=CategoriaDeVisto.ISENTO)
    gravar_visto("FK", categoria=CategoriaDeVisto.VISTO_EXIGIDO, rotulo="Visa required")
    # Kosovo sem linha própria: não herda a isenção da Sérvia
    http = cliente(sessao, relogio)

    por_codigo = {t["codigo"]: t for t in http.get("/api/v1/vistos").json()["territorios"]}

    assert por_codigo["FK"] == {"codigo": "FK", "situacao": "visto_exigido", "aceita_rg": False}
    assert por_codigo["XK"] == {"codigo": "XK", "situacao": "sem_informacao", "aceita_rg": False}
    assert por_codigo["RS"]["situacao"] == "isento"


def test_o_rg_vem_dos_oito_paises_da_fixture(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    http = com_vistos(sessao, relogio, coletar_vistos, html_da_wikipedia)

    territorios = http.get("/api/v1/vistos").json()["territorios"]

    com_rg = {t["codigo"] for t in territorios if t["aceita_rg"]}
    assert com_rg == OITO_DO_RG  # as Malvinas não herdam o RG da Argentina
    assert {t["codigo"] for t in territorios if t["codigo"] in ("VE", "GY") and t["aceita_rg"]} == (
        set()
    )


def test_dados_com_mais_de_14_dias_marcam_o_conjunto_como_desatualizado(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    http = com_vistos(sessao, relogio, coletar_vistos, html_da_wikipedia)
    relogio.avancar(days=15)

    corpo = http.get("/api/v1/vistos").json()

    assert corpo["dados_obtidos"] is True
    assert corpo["desatualizado"] is True


# --------------------------------------------------------------------------- erros e só leitura
def test_rota_so_aceita_leitura(sessao: Session, relogio: "RelogioFalso") -> None:
    http = cliente(sessao, relogio)
    for metodo in ("post", "put", "patch", "delete"):
        assert http.request(metodo.upper(), "/api/v1/vistos").status_code == 405


# --------------------------------------------------------------------------- consultas
def test_numero_de_consultas_e_fixo_e_igual_a_tres(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
    contar_consultas: "ContadorDeConsultas",
) -> None:
    executar(sessao, DADOS, AGORA)
    http = cliente(sessao, relogio)
    with contar_consultas as contador:
        assert http.get("/api/v1/vistos").status_code == 200
    sem_dados = contador.total

    coletar_vistos(html_da_wikipedia)
    with contar_consultas as contador:
        resposta = http.get("/api/v1/vistos")
    assert resposta.status_code == 200
    assert len(resposta.json()["territorios"]) > 200
    assert contador.total == 3  # última coleta válida, territórios, registros
    assert sem_dados <= contador.total
