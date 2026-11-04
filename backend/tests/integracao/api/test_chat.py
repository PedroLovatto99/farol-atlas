"""POST /api/v1/chat: paridade com o painel, limite por IP, CORS, cache e nada logado."""

import logging
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from farol.api.app import criar_app, sessao_da_requisicao
from farol.api.composicao import FonteDoPainelDaApi
from farol.api.dependencias import relogio_da_requisicao, servico_do_chat
from farol.chat import PalpiteDoModelo, Resposta, ServicoDoChat, TipoDeResposta, Trecho
from farol.chat import servico as modulo_do_servico
from farol.chat.entendimento import Apelidos
from farol.dominio import (
    Alerta,
    CategoriaDeVisto,
    Classificacao,
    ExecucaoColeta,
    MotivoOutraSituacao,
    NivelAlerta,
    NivelTerritorio,
    StatusClassificacao,
    TipoExecucao,
)
from farol.dominio.seed import executar
from farol.infra import FUSO_DE_BRASILIA, Configuracoes

if TYPE_CHECKING:
    from tests.conftest import ColetorDeVistos, GravadorDeVisto, RelogioFalso

DADOS = Path(__file__).resolve().parents[4] / "dados"
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
ROTA = "/api/v1/chat"
ORIGEM = "http://localhost:5173"
MARCADOR = "MARCADOR-DA-PERGUNTA"

ROTULOS_DE_NIVEL = {"evitar": "Evite viagens não essenciais", "nao_viajar": "Não viaje"}
ROTULOS_DE_VISTO = {
    "isento": "Isento de visto",
    "visto_na_chegada": "Visto na chegada",
    "autorizacao_eletronica": "Autorização ou visto eletrônico",
    "visto_exigido": "Visto exigido",
    "outra_situacao": "Outra situação",
    "sem_informacao": "Sem informação de visto",
}


class Tempo:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora


def criar(
    sessao: Session,
    relogio: "RelogioFalso",
    tempo: Tempo | None = None,
    **campos: Any,
) -> FastAPI:
    configuracao: dict[str, Any] = {"cache_ttl_segundos": 0, "limite_pedidos_por_minuto": 0}
    app = criar_app(
        Configuracoes(
            _env_file=None,
            database_url=SecretStr("postgresql+psycopg://x:y@nao-existe/z"),
            **{**configuracao, **campos},
        ),
        relogio_monotonico=tempo or Tempo(),
    )

    def fornecer_sessao() -> Iterator[Session]:
        yield sessao

    app.dependency_overrides[sessao_da_requisicao] = fornecer_sessao
    app.dependency_overrides[relogio_da_requisicao] = lambda: relogio
    return app


def cliente(
    sessao: Session, relogio: "RelogioFalso", tempo: Tempo | None = None, **campos: Any
) -> TestClient:
    return TestClient(criar(sessao, relogio, tempo, **campos), raise_server_exceptions=False)


def coleta_completa(sessao: Session, instante: datetime = AGORA) -> ExecucaoColeta:
    execucao = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS, iniciada_em=instante, finalizada_em=instante, completa=True
    )
    sessao.add(execucao)
    sessao.flush()
    return execucao


def alerta_de(
    sessao: Session,
    execucao: ExecucaoColeta,
    numero: int,
    codigo: str | None,
    nivel: NivelAlerta | None = None,
    regioes: list[dict[str, str]] | None = None,
    titulo: str | None = None,
) -> None:
    """Um alerta confirmado; com `codigo` None fica pendente (sem classificação)."""
    hash_do_alerta = f"{numero:064d}"
    titulo = titulo or f"Alerta {numero}"
    alerta = Alerta(
        url=f"https://www.gov.br/mre/alerta-{numero}",
        titulo=titulo,
        publicado_em=AGORA - timedelta(days=numero),
        modificado_em=AGORA - timedelta(hours=numero),
        primeira_coleta_em=AGORA,
        ultima_coleta_em=AGORA,
        hash=hash_do_alerta,
        confirmado_execucao_id=execucao.id,
        confirmado_hash=hash_do_alerta,
        confirmado_titulo=titulo,
        confirmado_data_ref=AGORA - timedelta(hours=numero),
    )
    sessao.add(alerta)
    sessao.flush()
    if codigo is None:
        return
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
            nivel_pais=nivel,
            regioes=regioes or [],
        )
    )
    sessao.flush()


def perguntar(http: TestClient, pergunta: str) -> dict[str, Any]:
    resposta = http.post(ROTA, json={"pergunta": pergunta})
    assert resposta.status_code == 200, resposta.text
    corpo: dict[str, Any] = resposta.json()
    return corpo


def texto_de(corpo: Mapping[str, Any]) -> str:
    return "\n".join("".join(t["texto"] for t in p) for p in corpo["paragrafos"])


def urls_de(corpo: Mapping[str, Any]) -> set[str]:
    return {t["url"] for p in corpo["paragrafos"] for t in p if t["url"] is not None}


def data(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(FUSO_DE_BRASILIA).strftime("%d/%m/%Y")


# --------------------------------------------------------------------------- paridade
def conferir_paridade(http: TestClient, codigo: str, termo: str) -> None:
    """Cada dado da resposta é igual ao de `GET /paises/{codigo}` e de `/mapa` (SC-001)."""
    pais = http.get(f"/api/v1/paises/{codigo}").json()
    mapa = http.get("/api/v1/mapa").json()
    corpo = perguntar(http, f"como está o alerta e o visto de {termo}?")
    assert (corpo["tipo"], corpo["codigo"]) == ("alerta_e_visto", codigo), termo
    texto, urls = texto_de(corpo), urls_de(corpo)

    # alerta
    assert pais["nome"] in texto
    nivel = pais["nivel"]
    if nivel in ROTULOS_DE_NIVEL:
        assert f'(nível "{ROTULOS_DE_NIVEL[nivel]}")' in texto
    elif nivel == "nao_verificado":
        assert "não foi verificado" in texto
    elif pais["regiao_unica_do_alerta"]:
        assert '"Alerta só para parte do país"' in texto
    else:
        assert "Não há alerta de viagem do Itamaraty" in texto
    for regiao in pais["regioes"]:
        assert f'{regiao["nome"]} ("{ROTULOS_DE_NIVEL[regiao["nivel"]]}")' in texto
    for alerta in pais["alertas"]:
        mostrado = alerta["pendente"] if nivel == "nao_verificado" else alerta["define_nivel"]
        if mostrado:
            assert alerta["titulo"] in texto
            assert alerta["url"] in urls
        if alerta["define_nivel"] and nivel != "nao_verificado":
            assert f"publicado em {data(alerta['publicado_em'])}" in texto
            if alerta["modificado_em"]:
                assert f"modificado em {data(alerta['modificado_em'])}" in texto
    if pais["observacao"]:
        assert pais["observacao"] in texto
    if mapa["atualizado_em"]:
        assert (
            f"Portal Consular do Itamaraty, atualizado em {data(mapa['atualizado_em'])}." in texto
        )
    assert ("Dados desatualizados" in texto) is mapa["desatualizado"]

    # visto
    visto = pais["visto"]
    assert (visto["territorio_nome"] or pais["nome"]) in texto
    assert f'Categoria: "{ROTULOS_DE_VISTO[visto["situacao"]]}"' in texto
    if visto["rotulo_original"]:
        assert f"Na fonte: {visto['rotulo_original']}" in texto
    assert ("Varia conforme o motivo da viagem" in texto) is visto["varia_conforme_motivo"]
    if visto["permanencia"] and visto["permanencia"]["texto"]:
        assert f"Permanência: {visto['permanencia']['texto']}" in texto
    if visto["origem"] == "soberano":
        assert f"Vale a entrada do soberano: {visto['soberano_nome']}." in texto
    for observacao in visto["observacoes"]:
        assert (observacao["traducao"] or observacao["texto_original"]) in texto
    assert visto["fonte"]["nome"] in texto
    assert visto["fonte"]["url"] in urls
    if visto["dado_de"]:
        assert f"dado de {data(visto['dado_de'])}." in texto
    assert ("podem estar desatualizados" in texto) is visto["desatualizado"]


def test_paridade_por_nivel_e_por_categoria_de_visto(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    execucao = coleta_completa(sessao)
    alerta_de(sessao, execucao, 1, "US", NivelAlerta.EVITAR)
    alerta_de(sessao, execucao, 2, "SY", NivelAlerta.NAO_VIAJAR)
    alerta_de(
        sessao,
        execucao,
        3,
        "CO",
        None,
        [{"nome": "Fronteira norte", "nivel": "nao_viajar"}],
    )
    alerta_de(
        sessao, execucao, 4, "UA", NivelAlerta.EVITAR, [{"nome": "Leste", "nivel": "nao_viajar"}]
    )
    alerta_de(sessao, execucao, 5, None, titulo="Alerta consular sobre a Bolívia")
    coletar_vistos(html_da_wikipedia)
    http = cliente(sessao, relogio)

    territorios = http.get("/api/v1/mapa").json()["territorios"]
    nomes = {t["codigo"]: t["nome"] for t in territorios}
    primeiro_de: dict[str, str] = {}
    for item in http.get("/api/v1/vistos").json()["territorios"]:
        if item["codigo"] != "BR" and len(item["codigo"]) == 2:
            primeiro_de.setdefault(item["situacao"], item["codigo"])
    assert {"isento", "visto_exigido", "visto_na_chegada"} <= set(primeiro_de)

    amostra = {"US", "SY", "CO", "UA", "BO", "JP", "AR", *primeiro_de.values()}  # AR: RG
    amostra.discard("MF")  # São Martim é ambíguo de propósito
    amostra.discard("SX")
    for codigo in sorted(amostra):
        conferir_paridade(http, codigo, nomes[codigo].split(" (")[0])

    assert http.get("/api/v1/paises/BO").json()["nivel"] == "nao_verificado"
    assert http.get("/api/v1/paises/CO").json()["regiao_unica_do_alerta"] is True
    assert http.get("/api/v1/paises/JP").json()["nivel"] == "sem_alerta"
    assert "Confira o alerta original: Alerta consular sobre a Bolívia" in texto_de(
        perguntar(http, "alerta da Bolívia")
    )


@pytest.mark.parametrize(
    ("codigo", "termo"),
    [("XK", "Kosovo"), ("FK", "Malvinas"), ("GF", "Guiana Francesa"), ("HK", "Hong Kong")],
)
def test_paridade_de_kosovo_malvinas_e_dependencias(
    sessao: Session,
    relogio: "RelogioFalso",
    coletar_vistos: "ColetorDeVistos",
    html_da_wikipedia: str,
    codigo: str,
    termo: str,
) -> None:
    executar(sessao, DADOS, AGORA)
    coleta_completa(sessao)
    coletar_vistos(html_da_wikipedia)
    conferir_paridade(cliente(sessao, relogio), codigo, termo)


@pytest.mark.parametrize(("codigo", "termo"), [("XK", "Kosovo"), ("FK", "Malvinas")])
def test_kosovo_e_malvinas_abrem_o_alerta_com_a_nota_do_painel(
    sessao: Session, relogio: "RelogioFalso", codigo: str, termo: str
) -> None:
    executar(sessao, DADOS, AGORA)
    coleta_completa(sessao)
    http = cliente(sessao, relogio)
    pais = http.get(f"/api/v1/paises/{codigo}").json()
    assert pais["observacao_no_topo"] is True
    primeiro = perguntar(http, f"alerta {termo}")["paragrafos"][0]
    assert "".join(t["texto"] for t in primeiro) == pais["observacao"]


def test_a_serbia_e_a_argentina_nao_viram_ambiguas(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)
    http = cliente(sessao, relogio)
    assert perguntar(http, "visto para a Sérvia")["codigo"] == "RS"
    assert perguntar(http, "visto para a Argentina")["codigo"] == "AR"


@pytest.mark.parametrize(
    ("categoria", "motivo"),
    [
        (CategoriaDeVisto.OUTRA_SITUACAO, MotivoOutraSituacao.ROTULO_DESCONHECIDO),
        (CategoriaDeVisto.AUTORIZACAO_ELETRONICA, None),
    ],
)
def test_paridade_de_categoria_gravada_com_traducao(
    sessao: Session,
    relogio: "RelogioFalso",
    gravar_visto: "GravadorDeVisto",
    categoria: CategoriaDeVisto,
    motivo: MotivoOutraSituacao | None,
) -> None:
    executar(sessao, DADOS, AGORA)
    coleta_completa(sessao)
    gravar_visto(
        "PT", categoria=categoria, motivo_outra=motivo, observacoes=[("Original", "Traduzida")]
    )
    conferir_paridade(cliente(sessao, relogio), "PT", "Portugal")


def test_paridade_do_rg(
    sessao: Session, relogio: "RelogioFalso", gravar_visto: "GravadorDeVisto"
) -> None:
    executar(sessao, DADOS, AGORA)
    coleta_completa(sessao)
    gravar_visto("CL", aceita_rg=True)
    http = cliente(sessao, relogio)
    conferir_paridade(http, "CL", "Chile")
    assert "a entrada pode ser feita com o RG" in texto_de(perguntar(http, "visto Chile"))


def test_sem_nenhuma_coleta(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    http = cliente(sessao, relogio)
    conferir_paridade(http, "JP", "Japão")
    texto = texto_de(perguntar(http, "e o Japão?"))
    assert "Ainda não obtivemos os dados do Itamaraty" in texto
    assert "Sem informação de visto para o Japão." in texto


def test_dados_desatualizados(
    sessao: Session, relogio: "RelogioFalso", gravar_visto: "GravadorDeVisto"
) -> None:
    executar(sessao, DADOS, AGORA)
    coleta_completa(sessao)
    gravar_visto("JP")
    relogio.avancar(days=15)
    http = cliente(sessao, relogio)
    conferir_paridade(http, "JP", "Japão")
    texto = texto_de(perguntar(http, "e o Japão?"))
    assert "Dados desatualizados" in texto
    assert "podem estar desatualizados" in texto


# --------------------------------------------------------------------------- perguntas
def test_sem_llm_chat_responde_pelo_codigo(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    corpo = perguntar(cliente(sessao, relogio, llm_chat=""), "visto Japão")
    assert (corpo["tipo"], corpo["codigo"]) == ("visto", "JP")


def test_verbo_de_viagem_responde_pelo_codigo(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    corpo = perguntar(cliente(sessao, relogio, llm_chat=""), "quero conhecer Tailândia")
    assert (corpo["tipo"], corpo["codigo"]) == ("alerta_e_visto", "TH")


@pytest.mark.parametrize(
    ("pergunta", "tipo"),
    [
        ("visto para o Congo", "qual_dos_paises"),
        ("preciso de visto?", "pedir_pais"),
        ("visto para a França e a Itália", "um_pais_por_vez"),
        ("visto para o Brasil", "brasil"),
        ("qual a capital do Japão?", "fora_do_assunto"),
        ("xyz?", "reformular"),
    ],
)
def test_mensagens_fixas(
    sessao: Session, relogio: "RelogioFalso", pergunta: str, tipo: str
) -> None:
    executar(sessao, DADOS, AGORA)
    corpo = perguntar(cliente(sessao, relogio), pergunta)
    assert (corpo["tipo"], corpo["codigo"]) == (tipo, None)


def test_congo_usa_os_nomes_do_site(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    assert texto_de(perguntar(cliente(sessao, relogio), "e o Congo?")) == (
        "Qual deles você quer saber: Rep. do Congo ou Rep. Dem. do Congo? "
        "Pergunte de novo com o nome do país."
    )


def test_o_brasil_como_origem_responde_o_destino(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    assert perguntar(cliente(sessao, relogio), "saindo do Brasil para o Chile")["codigo"] == "CL"


# --------------------------------------------------------------------------- validação e limite
@pytest.mark.parametrize(
    "corpo",
    [
        {"pergunta": ""},
        {"pergunta": "    "},
        {"pergunta": "a" * 301},
        {},
        {"pergunta": "visto Japão", "extra": 1},
    ],
)
def test_pergunta_invalida_recebe_422_sem_gastar_ficha(
    sessao: Session, relogio: "RelogioFalso", corpo: dict[str, Any]
) -> None:
    executar(sessao, DADOS, AGORA)
    http = cliente(sessao, relogio, chat_perguntas_por_hora=1)
    for _ in range(3):
        resposta = http.post(ROTA, json=corpo)
        assert resposta.status_code == 422
        assert "detalhe" in resposta.json()
    assert http.post(ROTA, json={"pergunta": "visto Japão"}).status_code == 200


def test_espacos_nas_pontas_nao_contam(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    pergunta = "  visto Japão" + " " * 300
    assert cliente(sessao, relogio).post(ROTA, json={"pergunta": pergunta}).status_code == 200


def test_a_21a_pergunta_seguida_recebe_429(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    tempo = Tempo()
    http = cliente(sessao, relogio, tempo)
    for _ in range(20):
        assert http.post(ROTA, json={"pergunta": "visto Japão"}).status_code == 200

    resposta = http.post(ROTA, json={"pergunta": "visto Japão"})

    assert resposta.status_code == 429
    assert resposta.headers["retry-after"] == "180"
    assert resposta.json() == {
        "detalhe": "Você chegou ao limite de 20 perguntas por hora. Tente de novo em 3 min."
    }

    tempo.agora += 180
    assert http.post(ROTA, json={"pergunta": "visto Japão"}).status_code == 200


def test_a_chave_do_limite_e_o_ip_que_o_ip_real_trocou(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    executar(sessao, DADOS, AGORA)
    app = criar(sessao, relogio, chat_perguntas_por_hora=1, proxy_confiavel=["172.30.0.0/24"])
    http = TestClient(app, client=("172.30.0.2", 40000))
    corpo = {"pergunta": "visto Japão"}
    primeiro = {"X-Forwarded-For": "203.0.113.1"}
    segundo = {"X-Forwarded-For": "203.0.113.2"}
    assert http.post(ROTA, json=corpo, headers=primeiro).status_code == 200
    assert http.post(ROTA, json=corpo, headers=primeiro).status_code == 429
    assert http.post(ROTA, json=corpo, headers=segundo).status_code == 200


# --------------------------------------------------------------------------- CORS e cache
def preflight(http: TestClient, caminho: str, metodo: str) -> Any:
    return http.options(
        caminho,
        headers={
            "Origin": ORIGEM,
            "Access-Control-Request-Method": metodo,
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_preflight_de_post_e_aceito_no_chat(sessao: Session, relogio: "RelogioFalso") -> None:
    resposta = preflight(cliente(sessao, relogio, cors_origens=[ORIGEM]), ROTA, "POST")
    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == ORIGEM
    assert "POST" in resposta.headers["access-control-allow-methods"]
    assert "content-type" in resposta.headers["access-control-allow-headers"].lower()


def test_preflight_de_post_e_recusado_no_mapa(sessao: Session, relogio: "RelogioFalso") -> None:
    resposta = preflight(cliente(sessao, relogio, cors_origens=[ORIGEM]), "/api/v1/mapa", "POST")
    assert resposta.status_code == 400
    assert "POST" not in resposta.headers.get("access-control-allow-methods", "")


def test_a_resposta_do_chat_sai_com_cors(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    http = cliente(sessao, relogio, cors_origens=[ORIGEM])
    resposta = http.post(ROTA, json={"pergunta": "visto Japão"}, headers={"Origin": ORIGEM})
    assert resposta.headers["access-control-allow-origin"] == ORIGEM


def test_o_429_do_chat_sai_com_cors(sessao: Session, relogio: "RelogioFalso") -> None:
    executar(sessao, DADOS, AGORA)
    http = cliente(sessao, relogio, cors_origens=[ORIGEM], chat_perguntas_por_hora=1)
    http.post(ROTA, json={"pergunta": "visto Japão"})
    resposta = http.post(ROTA, json={"pergunta": "visto Japão"}, headers={"Origin": ORIGEM})
    assert resposta.status_code == 429
    assert resposta.headers["access-control-allow-origin"] == ORIGEM


class ServicoFalso:
    def __init__(self) -> None:
        self.chamadas = 0

    def responder(self, pergunta: str) -> Resposta:
        self.chamadas += 1
        return Resposta(TipoDeResposta.REFORMULAR, None, ((Trecho("oi"),),))


def test_post_nao_passa_pelo_cache(sessao: Session, relogio: "RelogioFalso") -> None:
    app = criar(sessao, relogio, cache_ttl_segundos=300)
    servico = ServicoFalso()
    app.dependency_overrides[servico_do_chat] = lambda: servico
    http = TestClient(app)
    respostas = [http.post(ROTA, json={"pergunta": "visto Japão"}) for _ in range(2)]
    assert servico.chamadas == 2
    assert all("cache-control" not in r.headers for r in respostas)


# --------------------------------------------------------------------------- nada logado
class ModeloQueFalha:
    def entender(self, pergunta: str, territorios: Mapping[str, str]) -> PalpiteDoModelo | None:
        raise RuntimeError(f"falhou com {pergunta}")


def test_a_pergunta_nao_aparece_nos_logs(
    sessao: Session, relogio: "RelogioFalso", caplog: pytest.LogCaptureFixture
) -> None:
    executar(sessao, DADOS, AGORA)
    app = criar(sessao, relogio)
    app.state.modelo_do_chat = ModeloQueFalha()
    logging.getLogger().addHandler(caplog.handler)  # `criar_app` trocou os handlers da raiz
    caplog.set_level(logging.DEBUG)
    http = TestClient(app, raise_server_exceptions=False)

    assert perguntar(http, f"visto Japão {MARCADOR}")["tipo"] == "visto"
    assert perguntar(http, f"{MARCADOR} xyz")["tipo"] == "reformular"  # passa pelo modelo

    assert caplog.records  # o log do modelo foi capturado: a conferência não é vazia
    tudo = caplog.text + str([getattr(r, "dados", "") for r in caplog.records])
    assert MARCADOR not in tudo
    assert "RuntimeError" in tudo


# --------------------------------------------------------------------------- conexões
def test_nenhuma_conexao_fica_presa_durante_a_chamada_ao_modelo(
    engine_teste: Engine, relogio: "RelogioFalso", monkeypatch: pytest.MonkeyPatch
) -> None:
    """O modelo leva até 5 s: segurar a conexão esgotaria o pool e travaria `/saude`."""
    monkeypatch.setattr(modulo_do_servico, "carregar_apelidos", lambda _: Apelidos({}, {}))
    presas: list[int] = []

    class ModeloEspiao:
        def entender(self, pergunta: str, territorios: Mapping[str, str]) -> PalpiteDoModelo | None:
            presas.append(engine_teste.pool.checkedout())  # type: ignore[attr-defined]
            return None

    with Session(engine_teste, expire_on_commit=False) as sessao_real:
        fonte = FonteDoPainelDaApi(sessao_real, relogio)
        resposta = ServicoDoChat(fonte, ModeloEspiao()).responder("xyz?")

    assert presas == [0]
    assert resposta.tipo is TipoDeResposta.REFORMULAR
