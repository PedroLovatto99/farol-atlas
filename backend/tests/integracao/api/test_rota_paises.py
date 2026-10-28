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
    RequisitoVisto,
    StatusClassificacao,
    Territorio,
    TipoExecucao,
    TipoTerritorio,
)
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

CAMPOS_DO_PAIS = {
    "codigo", "nome", "tipo", "soberano", "bandeira", "identidade_do_soberano", "nivel",
    "regioes", "regiao_unica_do_alerta", "observacao", "observacao_no_topo", "eh_brasil",
    "alertas", "postos", "posto_responsavel", "sem_posto_indicado", "fonte_postos", "visto",
}  # fmt: skip
CAMPOS_DO_ALERTA = {
    "titulo", "url", "publicado_em", "modificado_em", "define_nivel", "situacao_normalizada",
    "pendente",
}  # fmt: skip
CAMPOS_DO_POSTO = {
    "id", "tipo", "cidade", "pais", "grupo", "endereco", "telefone_plantao",
    "contato_coletado_em", "contato_fonte_url",
}  # fmt: skip
CAMPOS_DO_VISTO = {
    "situacao", "motivo_outra_situacao", "rotulo_original", "aceita_rg", "varia_conforme_motivo",
    "permanencia", "observacoes", "origem", "soberano_nome", "territorio_nome", "dado_de",
    "desatualizado", "fonte",
}  # fmt: skip
CAMPOS_DA_PERMANENCIA = {"tipo", "texto"}
CAMPOS_DA_OBSERVACAO = {"texto_original", "traducao"}
# A 001 fazia até 8 consultas; o visto acrescenta 3 (coleta válida, território, registros)
LIMITE_DE_CONSULTAS = 8 + 3


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
def test_numero_de_consultas_e_fixo_e_no_maximo_onze(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
    contar_consultas: "ContadorDeConsultas",
) -> None:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html_da_wikipedia)
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
    assert contador.total <= LIMITE_DE_CONSULTAS


@pytest.mark.parametrize("codigo", ["BR", "PR", "LY", "XK", "GL"])
def test_consultas_dos_casos_especiais_tambem_ficam_no_limite(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
    contar_consultas: "ContadorDeConsultas",
    codigo: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html_da_wikipedia)
    alerta_de(sessao, coleta_completa(sessao), 1, "RS")
    http = cliente(sessao, relogio)
    with contar_consultas as contador:
        resposta = http.get(f"/api/v1/paises/{codigo}")
    assert resposta.status_code == 200
    assert contador.total <= LIMITE_DE_CONSULTAS


# --------------------------------------------------------------------------- visto (feature 002)
def test_o_visto_do_painel_traz_o_dto_do_contrato(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html_da_wikipedia)

    corpo = cliente(sessao, relogio).get("/api/v1/paises/ET").json()

    visto = corpo["visto"]
    assert set(visto) == CAMPOS_DO_VISTO
    assert visto["situacao"] == "autorizacao_eletronica"
    assert visto["rotulo_original"] == "eVisa / Visa on arrival"
    assert (visto["aceita_rg"], visto["varia_conforme_motivo"]) == (False, False)
    assert visto["permanencia"] == {"tipo": "original", "texto": "up to 90 days"}
    assert set(visto["permanencia"]) == CAMPOS_DA_PERMANENCIA
    assert (visto["origem"], visto["soberano_nome"]) == ("proprio", None)
    assert visto["dado_de"].startswith("2026-10-23T12:00:00")
    assert visto["desatualizado"] is False
    assert visto["fonte"]["licenca"] == "CC BY-SA"
    assert visto["fonte"]["url"].startswith("https://en.wikipedia.org/wiki/Visa_requirements")


def test_as_observacoes_do_visto_saem_com_o_original_e_a_traducao(
    sessao: Session, relogio: "RelogioFalso", gravar_visto: "GravadorDeVisto"
) -> None:
    executar(sessao, DADOS, AGORA)
    gravar_visto("US", observacoes=[("Original A", "Tradução A"), ("Original B", None)])

    observacoes = cliente(sessao, relogio).get("/api/v1/paises/US").json()["visto"]["observacoes"]

    assert observacoes == [
        {"texto_original": "Original A", "traducao": "Tradução A"},
        {"texto_original": "Original B", "traducao": None},
    ]
    assert set(observacoes[0]) == CAMPOS_DA_OBSERVACAO


def test_todo_pais_com_painel_traz_visto_e_so_o_brasil_traz_nulo(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html_da_wikipedia)
    http = cliente(sessao, relogio)
    codigos = [t["codigo"] for t in http.get("/api/v1/mapa").json()["territorios"]]

    sem_visto = []
    for codigo in codigos:
        resposta = http.get(f"/api/v1/paises/{codigo}")
        assert resposta.status_code == 200, codigo
        if resposta.json()["visto"] is None:
            sem_visto.append(codigo)

    assert len(codigos) > 200
    assert sem_visto == ["BR"]


def test_pais_sem_dado_de_visto_traz_a_secao_com_sem_informacao(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)

    visto = cliente(sessao, relogio).get("/api/v1/paises/US").json()["visto"]

    assert set(visto) == CAMPOS_DO_VISTO
    assert visto["situacao"] == "sem_informacao"
    assert visto["aceita_rg"] is False
    assert (visto["rotulo_original"], visto["permanencia"], visto["origem"]) == (None, None, None)
    assert (visto["soberano_nome"], visto["dado_de"], visto["desatualizado"]) == (None, None, False)
    assert visto["observacoes"] == []
    assert visto["fonte"]["nome"].startswith("Wikipédia")


def test_o_brasil_nao_tem_secao_de_visto(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)

    corpo = cliente(sessao, relogio).get("/api/v1/paises/BR").json()

    assert "visto" in corpo
    assert corpo["visto"] is None


def test_dependencia_com_entrada_propria_e_sem_ela(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html_da_wikipedia)
    http = cliente(sessao, relogio)

    hong_kong = http.get("/api/v1/paises/HK").json()["visto"]
    guernsey = http.get("/api/v1/paises/GG").json()["visto"]

    assert (hong_kong["situacao"], hong_kong["origem"], hong_kong["soberano_nome"]) == (
        "isento",
        "proprio",
        None,
    )
    assert (guernsey["situacao"], guernsey["origem"], guernsey["soberano_nome"]) == (
        "autorizacao_eletronica",
        "soberano",
        "Reino Unido",
    )


def test_kosovo_e_malvinas_abrem_o_painel_do_soberano_com_o_visto_da_propria_linha(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html_da_wikipedia)
    http = cliente(sessao, relogio)

    kosovo = http.get("/api/v1/paises/XK").json()
    malvinas = http.get("/api/v1/paises/FK").json()

    # a identidade do painel (001) é a do soberano...
    assert (kosovo["nome"], kosovo["bandeira"]) == ("Sérvia", "RS")
    assert (malvinas["nome"], malvinas["bandeira"]) == ("Argentina", "AR")
    # ...mas a seção de visto é da linha própria e diz de que território é
    assert (kosovo["visto"]["origem"], kosovo["visto"]["soberano_nome"]) == ("proprio", None)
    assert kosovo["visto"]["territorio_nome"] == "Kosovo"
    assert malvinas["visto"]["territorio_nome"] == "Ilhas Malvinas"
    assert (malvinas["visto"]["origem"], malvinas["visto"]["soberano_nome"]) == ("proprio", None)
    assert malvinas["visto"]["aceita_rg"] is False  # a Argentina aceita RG, as Malvinas não
    assert http.get("/api/v1/paises/AR").json()["visto"]["aceita_rg"] is True
    assert http.get("/api/v1/paises/AR").json()["visto"]["territorio_nome"] is None


def test_o_visto_com_mais_de_14_dias_sai_como_desatualizado(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html_da_wikipedia)
    relogio.avancar(days=15)

    visto = cliente(sessao, relogio).get("/api/v1/paises/AR").json()["visto"]

    assert visto["desatualizado"] is True
    assert visto["dado_de"].startswith("2026-10-23T12:00:00")


def test_sem_nenhuma_coleta_so_o_brasil_tem_visto_nulo_e_os_demais_dizem_sem_informacao(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)
    http = cliente(sessao, relogio)
    codigos = [t["codigo"] for t in http.get("/api/v1/mapa").json()["territorios"]]

    nulos, explicitos = [], []
    for codigo in codigos:
        visto = http.get(f"/api/v1/paises/{codigo}").json()["visto"]
        if visto is None:
            nulos.append(codigo)
        else:
            assert visto["situacao"] == "sem_informacao", codigo  # nunca a seção ausente
            explicitos.append(codigo)

    assert nulos == ["BR"]
    assert len(explicitos) == len(codigos) - 1 > 200


def test_o_visto_nulo_so_existe_no_brasil_mesmo_depois_da_coleta(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html_da_wikipedia)
    # um território que perdeu o dado (a linha saiu e o dono confirmou) volta a "sem informação"
    requisito = sessao.get(RequisitoVisto, "AU")
    assert requisito is not None
    sessao.delete(requisito)
    sessao.flush()

    http = cliente(sessao, relogio)

    assert http.get("/api/v1/paises/BR").json()["visto"] is None
    australia = http.get("/api/v1/paises/AU").json()["visto"]
    assert australia is not None
    assert australia["situacao"] == "sem_informacao"
    assert australia["rotulo_original"] is None


def test_as_malvinas_nunca_exibem_rg_no_painel_nem_no_globo(
    sessao: Session, relogio: "RelogioFalso", gravar_visto: "GravadorDeVisto"
) -> None:
    executar(sessao, DADOS, AGORA)
    gravar_visto("AR", aceita_rg=True)  # a Argentina aceita o RG
    http = cliente(sessao, relogio)

    # sem linha própria: sem informação, e não a isenção com RG da Argentina
    sem_linha = http.get("/api/v1/paises/FK").json()["visto"]
    assert sem_linha["situacao"] == "sem_informacao"
    assert sem_linha["aceita_rg"] is False
    assert sem_linha["territorio_nome"] == "Ilhas Malvinas"  # a seção ainda diz de quem é

    # com linha própria, vale a linha dela
    gravar_visto("FK", rotulo="Visa not required", aceita_rg=False)
    com_linha = http.get("/api/v1/paises/FK").json()["visto"]
    assert (com_linha["situacao"], com_linha["aceita_rg"]) == ("isento", False)

    globo = {t["codigo"]: t for t in http.get("/api/v1/vistos").json()["territorios"]}
    assert globo["FK"]["aceita_rg"] is False
    assert globo["AR"]["aceita_rg"] is True


def test_so_kosovo_e_malvinas_trazem_territorio_nome(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    coletar_vistos(html_da_wikipedia)
    http = cliente(sessao, relogio)
    codigos = [t["codigo"] for t in http.get("/api/v1/mapa").json()["territorios"]]

    com_nome = {}
    for codigo in codigos:
        visto = http.get(f"/api/v1/paises/{codigo}").json()["visto"]
        if visto is not None and visto["territorio_nome"] is not None:
            com_nome[codigo] = visto["territorio_nome"]

    assert com_nome == {"XK": "Kosovo", "FK": "Ilhas Malvinas"}
