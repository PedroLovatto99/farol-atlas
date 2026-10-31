"""O app montado como em produção: CORS fechado, IP real, limite de pedidos e cache juntos."""

from typing import Any

from fastapi.testclient import TestClient
from pydantic import SecretStr

from farol.api.app import criar_app
from farol.infra import Configuracoes

VERCEL = "https://farol-atlas.vercel.app"
ROTA = "/api/v1/openapi.json"  # não precisa de banco
CADDY = "172.30.0.2"


class Tempo:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora


def _config(**campos: Any) -> Configuracoes:
    base: dict[str, Any] = {
        "database_url": SecretStr("postgresql+psycopg://x:y@banco-que-nao-existe/z"),
        "ambiente": "producao",
        "cors_origens": [VERCEL],
        "proxy_confiavel": ["172.30.0.0/24"],
        "coletas_automaticas": True,
    }
    base.update(campos)
    return Configuracoes(**base)


def _cliente(origem: str = "198.51.100.7", tempo: Tempo | None = None, **campos: Any) -> TestClient:
    app = criar_app(_config(**campos), relogio_monotonico=tempo or Tempo())
    return TestClient(app, client=(origem, 40000), raise_server_exceptions=False)


# --------------------------------------------------------------------------- CORS
def test_cors_aceita_so_o_endereco_da_vercel() -> None:
    cliente = _cliente()
    assert (
        cliente.get(ROTA, headers={"Origin": VERCEL}).headers["access-control-allow-origin"]
        == VERCEL
    )
    assert (
        "access-control-allow-origin"
        not in cliente.get(ROTA, headers={"Origin": "https://outro.vercel.app"}).headers
    )


def test_cors_sem_credenciais() -> None:
    resposta = _cliente().get(ROTA, headers={"Origin": VERCEL})
    assert "access-control-allow-credentials" not in resposta.headers


def test_cors_so_libera_get() -> None:
    resposta = _cliente().options(
        ROTA, headers={"Origin": VERCEL, "Access-Control-Request-Method": "GET"}
    )
    assert resposta.headers["access-control-allow-methods"] == "GET"
    recusa = _cliente().options(
        ROTA, headers={"Origin": VERCEL, "Access-Control-Request-Method": "DELETE"}
    )
    assert recusa.status_code == 400


# --------------------------------------------------------------------------- limite
def test_o_429_sai_com_os_cabecalhos_do_cors_para_o_navegador_conseguir_le_lo() -> None:
    cliente = _cliente(limite_pedidos_por_minuto=60, limite_rajada=1)
    cliente.get(ROTA, headers={"Origin": VERCEL})
    resposta = cliente.get(ROTA, headers={"Origin": VERCEL})
    assert resposta.status_code == 429
    assert resposta.headers["access-control-allow-origin"] == VERCEL
    assert resposta.headers["retry-after"] == "1"


def test_limite_zero_desliga() -> None:
    cliente = _cliente(limite_pedidos_por_minuto=0, limite_rajada=1)
    assert all(cliente.get(ROTA).status_code == 200 for _ in range(5))


def test_o_saude_nao_e_barrado_pelo_limite() -> None:
    cliente = _cliente(limite_pedidos_por_minuto=60, limite_rajada=1)
    cliente.get(ROTA)
    assert cliente.get(ROTA).status_code == 429
    # o banco do teste não existe: a rota falha por isso (500), mas o limite não a barra
    assert cliente.get("/api/v1/saude").status_code != 429


def test_padrao_de_120_por_minuto_com_rajada_de_40() -> None:
    cliente = _cliente()
    codigos = [cliente.get(ROTA).status_code for _ in range(41)]
    assert codigos[:40] == [200] * 40
    assert codigos[40] == 429


def test_atras_do_caddy_cada_visitante_tem_o_seu_limite() -> None:
    cliente = _cliente(origem=CADDY, limite_pedidos_por_minuto=60, limite_rajada=1)
    um = {"X-Forwarded-For": "203.0.113.1"}
    outro = {"X-Forwarded-For": "203.0.113.2"}
    assert cliente.get(ROTA, headers=um).status_code == 200
    assert cliente.get(ROTA, headers=um).status_code == 429
    assert cliente.get(ROTA, headers=outro).status_code == 200


def test_x_forwarded_for_forjado_por_quem_nao_e_o_caddy_nao_vale() -> None:
    cliente = _cliente(origem="198.51.100.7", limite_pedidos_por_minuto=60, limite_rajada=2)
    codigos = [
        cliente.get(ROTA, headers={"X-Forwarded-For": f"203.0.113.{n}"}).status_code
        for n in range(4)
    ]
    assert codigos == [200, 200, 429, 429]


def test_sem_proxy_configurado_o_cabecalho_nunca_vale() -> None:
    cliente = _cliente(
        origem=CADDY,
        ambiente="desenvolvimento",
        proxy_confiavel=[],
        limite_pedidos_por_minuto=60,
        limite_rajada=1,
    )
    assert cliente.get(ROTA, headers={"X-Forwarded-For": "203.0.113.1"}).status_code == 200
    assert cliente.get(ROTA, headers={"X-Forwarded-For": "203.0.113.2"}).status_code == 429


def test_o_limite_volta_com_o_tempo() -> None:
    tempo = Tempo()
    cliente = _cliente(tempo=tempo, limite_pedidos_por_minuto=60, limite_rajada=1)
    cliente.get(ROTA)
    assert cliente.get(ROTA).status_code == 429
    tempo.agora += 1
    assert cliente.get(ROTA).status_code == 200
