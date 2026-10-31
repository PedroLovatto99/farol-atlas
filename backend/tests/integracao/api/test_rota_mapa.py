"""GET /api/v1/mapa: o DTO do contrato, número fixo de consultas e nenhum objeto do banco."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
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

CAMPOS_DO_MAPA = {
    "dados_obtidos", "desatualizado", "atualizado_em", "territorios", "postos", "paises_sem_posto"
}  # fmt: skip
CAMPOS_DO_TERRITORIO = {
    "codigo", "nome", "rotulo_busca", "termos_busca", "tipo", "soberano", "bandeira",
    "identidade_do_soberano", "nivel", "regioes", "observacao",
}  # fmt: skip
CAMPOS_DO_POSTO = {"id", "territorio", "tipo", "cidade", "latitude", "longitude", "grupo"}
CAMPOS_SEM_POSTO = {"territorio", "latitude", "longitude", "posto_responsavel_id"}


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


def popular_alerta(sessao: Session, execucao: ExecucaoColeta, numero: int, codigo: str) -> None:
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


def popular(sessao: Session, quantidade_de_territorios: int) -> None:
    execucao = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS, iniciada_em=AGORA, finalizada_em=AGORA, completa=True
    )
    sessao.add(execucao)
    sessao.add_all(
        Territorio(codigo=f"T{n:03d}", nome_pt=f"País {n}", tipo=TipoTerritorio.PAIS)
        for n in range(quantidade_de_territorios)
    )
    sessao.flush()
    for n in range(3):
        popular_alerta(sessao, execucao, n, f"T{n:03d}")


# --------------------------------------------------------------------------- contrato
def test_mapa_devolve_o_dto_do_contrato(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    sessao.add(
        ExecucaoColeta(
            tipo=TipoExecucao.ALERTAS,
            iniciada_em=AGORA - timedelta(hours=1),
            finalizada_em=AGORA - timedelta(minutes=50),
            completa=True,
        )
    )
    sessao.flush()

    resposta = cliente(sessao, relogio).get("/api/v1/mapa")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/json")
    corpo = resposta.json()
    assert set(corpo) == CAMPOS_DO_MAPA
    assert corpo["dados_obtidos"] is True
    assert corpo["desatualizado"] is False
    assert corpo["atualizado_em"].startswith("2026-10-23T11:10:00")
    assert {set(t) == CAMPOS_DO_TERRITORIO for t in corpo["territorios"]} == {True}
    assert {set(p) == CAMPOS_DO_POSTO for p in corpo["postos"]} == {True}
    assert {set(p) == CAMPOS_SEM_POSTO for p in corpo["paises_sem_posto"]} == {True}
    assert len(corpo["postos"]) == 209


def test_nenhum_objeto_do_banco_vaza_na_resposta(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    texto = cliente(sessao, relogio).get("/api/v1/mapa").text
    for rastro in ("_sa_instance_state", "na_lista_itamaraty", "icone_latitude", "nome_pt"):
        assert rastro not in texto  # colunas do banco não são parte do contrato


def test_todos_os_198_paises_da_lista_estao_presentes(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)
    corpo = cliente(sessao, relogio).get("/api/v1/mapa").json()
    codigos = {t["codigo"] for t in corpo["territorios"]}
    na_lista = set(
        sessao.scalars(select(Territorio.codigo).where(Territorio.na_lista_itamaraty.is_(True)))
    )
    assert len(na_lista) == 198
    assert na_lista <= codigos
    assert {t["nivel"] for t in corpo["territorios"]} == {"nao_verificado"}  # nenhuma coleta ainda


def test_niveis_e_regioes_vem_resolvidos(sessao: Session, relogio: "RelogioFalso") -> None:
    popular(sessao, 5)
    corpo = cliente(sessao, relogio).get("/api/v1/mapa").json()
    por_codigo = {t["codigo"]: t for t in corpo["territorios"]}
    assert por_codigo["T000"]["nivel"] == "evitar"
    assert por_codigo["T000"]["regioes"] == [{"nome": "Região", "nivel": "nao_viajar"}]
    assert por_codigo["T004"]["nivel"] == "sem_alerta"
    assert por_codigo["T004"]["regioes"] == []


def test_dados_desatualizados_sao_calculados_no_backend(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    popular(sessao, 5)
    relogio.avancar(days=4)
    corpo = cliente(sessao, relogio).get("/api/v1/mapa").json()
    assert corpo["desatualizado"] is True


def test_rota_so_aceita_leitura(sessao: Session, relogio: "RelogioFalso") -> None:
    assert cliente(sessao, relogio).post("/api/v1/mapa").status_code == 405


# --------------------------------------------------------------------------- consultas
@pytest.mark.parametrize("quantidade", [5, 200])
def test_numero_de_consultas_nao_depende_do_numero_de_territorios(
    sessao: Session,
    relogio: "RelogioFalso",
    contar_consultas: "ContadorDeConsultas",
    quantidade: int,
) -> None:
    popular(sessao, quantidade)
    http = cliente(sessao, relogio)
    with contar_consultas as contador:
        resposta = http.get("/api/v1/mapa")
    assert resposta.status_code == 200
    assert len(resposta.json()["territorios"]) == quantidade
    assert contador.total == 6  # igual com 5 ou com 200 territórios
