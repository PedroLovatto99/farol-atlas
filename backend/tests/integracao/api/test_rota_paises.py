"""GET /api/v1/paises/{codigo}: o DTO do contrato, erros em JSON e número fixo de consultas."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from farol.api.app import criar_app, sessao_da_requisicao
from farol.api.dependencias import relogio_da_requisicao
from farol.dominio import (
    Alerta,
    Classificacao,
    ExecucaoColeta,
    NivelAlerta,
    NivelTerritorio,
    Posto,
    StatusClassificacao,
    Territorio,
    TipoExecucao,
    TipoTerritorio,
)
from farol.dominio.seed import executar
from farol.infra import Configuracoes

if TYPE_CHECKING:
    from tests.conftest import ContadorDeConsultas, RelogioFalso

DADOS = Path(__file__).resolve().parents[4] / "dados"
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)

CAMPOS_DO_PAIS = {
    "codigo", "nome", "tipo", "soberano", "bandeira", "identidade_do_soberano", "nivel",
    "regioes", "regiao_unica_do_alerta", "observacao", "observacao_no_topo", "eh_brasil",
    "alertas", "postos", "posto_responsavel", "sem_posto_indicado", "fonte_postos",
}  # fmt: skip
CAMPOS_DO_ALERTA = {
    "titulo", "url", "publicado_em", "modificado_em", "define_nivel", "situacao_normalizada",
    "pendente",
}  # fmt: skip
CAMPOS_DO_POSTO = {
    "id", "tipo", "cidade", "pais", "grupo", "endereco", "telefone_plantao",
    "contato_coletado_em", "contato_fonte_url",
}  # fmt: skip


def cliente(sessao: Session, relogio: "RelogioFalso") -> TestClient:
    app = criar_app(Configuracoes(database_url=SecretStr("postgresql+psycopg://x:y@nao-existe/z")))

    def fornecer_sessao() -> Iterator[Session]:
        yield sessao

    app.dependency_overrides[sessao_da_requisicao] = fornecer_sessao
    app.dependency_overrides[relogio_da_requisicao] = lambda: relogio
    return TestClient(app, raise_server_exceptions=False)


def coleta_completa(sessao: Session) -> ExecucaoColeta:
    execucao = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS, iniciada_em=AGORA, finalizada_em=AGORA, completa=True
    )
    sessao.add(execucao)
    sessao.flush()
    return execucao


def alerta_de(sessao: Session, execucao: ExecucaoColeta, numero: int, codigo: str) -> None:
    hash_do_alerta = f"{numero:064d}"
    alerta = Alerta(
        url=f"https://www.gov.br/mre/alerta-{numero}",
        titulo=f"Alerta {numero}",
        publicado_em=AGORA,
        primeira_coleta_em=AGORA,
        ultima_coleta_em=AGORA,
        hash=hash_do_alerta,
        confirmado_execucao_id=execucao.id,
        confirmado_hash=hash_do_alerta,
        confirmado_titulo=f"Alerta {numero}",
        confirmado_data_ref=AGORA - timedelta(days=numero),
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
            territorio_codigo=codigo,
            nivel_pais=NivelAlerta.EVITAR,
            regioes=[{"nome": "Região", "nivel": "nao_viajar"}],
        )
    )
    sessao.flush()


# --------------------------------------------------------------------------- contrato
def test_pais_devolve_o_dto_do_contrato(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    alerta_de(sessao, coleta_completa(sessao), 1, "US")

    resposta = cliente(sessao, relogio).get("/api/v1/paises/US")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/json")
    corpo = resposta.json()
    assert set(corpo) == CAMPOS_DO_PAIS
    assert corpo["codigo"] == "US"
    assert corpo["nome"] == "Estados Unidos"
    assert corpo["bandeira"] == "US"
    assert corpo["nivel"] == "evitar"
    assert corpo["regioes"] == [{"nome": "Região", "nivel": "nao_viajar"}]
    assert corpo["eh_brasil"] is False
    assert corpo["observacao_no_topo"] is False
    assert len(corpo["alertas"]) == 1
    assert set(corpo["alertas"][0]) == CAMPOS_DO_ALERTA
    assert corpo["alertas"][0]["define_nivel"] is True
    assert {set(p) == CAMPOS_DO_POSTO for p in corpo["postos"]} == {True}
    assert corpo["fonte_postos"]["conferido_em"] == "2026-10-21"
    assert [f["nome"] for f in corpo["fonte_postos"]["fontes"]] == ["Itamaraty", "Wikipédia"]


def test_postos_trazem_fonte_e_data_quando_ha_endereco_ou_telefone(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)
    posto = sessao.get(Posto, 89)  # Embaixada em Washington
    assert posto is not None
    posto.endereco = "3006 Whitehaven St NW"
    posto.telefone_plantao = "+1 202 555 0100"
    posto.contato_coletado_em = AGORA
    posto.contato_fonte_url = "https://www.gov.br/mre/washington"
    sessao.flush()

    corpo = cliente(sessao, relogio).get("/api/v1/paises/US").json()

    por_id = {p["id"]: p for p in corpo["postos"]}
    assert por_id[89]["endereco"] == "3006 Whitehaven St NW"
    assert por_id[89]["telefone_plantao"] == "+1 202 555 0100"
    assert por_id[89]["contato_coletado_em"].startswith("2026-10-23T12:00:00")
    assert por_id[89]["contato_fonte_url"] == "https://www.gov.br/mre/washington"
    assert por_id[90]["endereco"] is None
    assert por_id[90]["contato_fonte_url"] is None


def test_kosovo_devolve_o_painel_da_servia(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    corpo = cliente(sessao, relogio).get("/api/v1/paises/XK").json()
    assert (corpo["nome"], corpo["bandeira"]) == ("Sérvia", "RS")
    assert corpo["identidade_do_soberano"] is True
    assert corpo["observacao_no_topo"] is True


def test_pais_sem_posto_devolve_o_responsavel(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    corpo = cliente(sessao, relogio).get("/api/v1/paises/PR").json()
    assert corpo["postos"] == []
    assert corpo["posto_responsavel"]["cidade"] == "Miami"
    assert set(corpo["posto_responsavel"]) == CAMPOS_DO_POSTO


@pytest.mark.parametrize("codigo", ["IOA", "CLP", "ATC", "CSI"])
def test_dependencias_com_codigo_de_tres_letras_tem_painel(
    sessao: Session, relogio: "RelogioFalso", codigo: str
) -> None:
    executar(sessao, DADOS, AGORA)
    resposta = cliente(sessao, relogio).get(f"/api/v1/paises/{codigo}")
    assert resposta.status_code == 200
    assert resposta.json()["codigo"] == codigo


# --------------------------------------------------------------------------- erros
def test_codigo_desconhecido_devolve_404_em_json(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    resposta = cliente(sessao, relogio).get("/api/v1/paises/ZZ")
    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith("application/json")
    assert set(resposta.json()) == {"detalhe"}


def test_area_neutra_devolve_404(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    sessao.add(Territorio(codigo="EH", nome_pt="Saara Ocidental", tipo=TipoTerritorio.NEUTRO))
    sessao.flush()
    assert cliente(sessao, relogio).get("/api/v1/paises/EH").status_code == 404


@pytest.mark.parametrize("codigo", ["br", "B", "BRAS", "B1", "B-", "%20"])
def test_codigo_mal_formado_devolve_422(
    sessao: Session, relogio: "RelogioFalso", codigo: str
) -> None:
    resposta = cliente(sessao, relogio).get(f"/api/v1/paises/{codigo}")
    assert resposta.status_code == 422
    assert set(resposta.json()) == {"detalhe"}


def test_rota_so_aceita_leitura(sessao: Session, relogio: "RelogioFalso") -> None:
    assert cliente(sessao, relogio).post("/api/v1/paises/BR").status_code == 405


# --------------------------------------------------------------------------- consultas
def test_numero_de_consultas_e_fixo_e_no_maximo_oito(
    sessao: Session, relogio: "RelogioFalso", contar_consultas: "ContadorDeConsultas"
) -> None:
    executar(sessao, DADOS, AGORA)
    execucao = coleta_completa(sessao)
    http = cliente(sessao, relogio)

    alerta_de(sessao, execucao, 1, "US")
    with contar_consultas as contador:
        resposta = http.get("/api/v1/paises/US")
    assert resposta.status_code == 200
    com_poucos = contador.total

    for n in range(2, 40):
        alerta_de(sessao, execucao, n, "US")
        alerta_de(sessao, execucao, n + 100, "BR")
    with contar_consultas as contador:
        resposta = http.get("/api/v1/paises/US")
    assert len(resposta.json()["alertas"]) == 39
    assert contador.total == com_poucos
    assert contador.total <= 8


@pytest.mark.parametrize("codigo", ["BR", "PR", "LY", "XK", "GL"])
def test_consultas_dos_casos_especiais_tambem_ficam_no_limite(
    sessao: Session,
    relogio: "RelogioFalso",
    contar_consultas: "ContadorDeConsultas",
    codigo: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    alerta_de(sessao, coleta_completa(sessao), 1, "RS")
    http = cliente(sessao, relogio)
    with contar_consultas as contador:
        resposta = http.get(f"/api/v1/paises/{codigo}")
    assert resposta.status_code == 200
    assert contador.total <= 8
