"""Limite de pedidos por IP: balde de fichas, 429 com Retry-After e o /saude de fora."""

import ipaddress

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

from farol.api.ip_real import IpReal
from farol.api.limite import LIMPEZA_A_CADA, BaldeDeFichas, LimiteDePedidos


class Tempo:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/mapa")
    def mapa() -> dict[str, int]:
        return {"ok": 1}

    @app.get("/api/v1/saude")
    def saude() -> dict[str, str]:
        return {"banco": "ok"}

    return app


def _cliente(
    tempo: Tempo,
    *,
    por_minuto: int = 120,
    rajada: int = 40,
    origem: str = "198.51.100.7",
    envolver: ASGIApp | None = None,
) -> TestClient:
    limitado = LimiteDePedidos(
        envolver or _app(), por_minuto=por_minuto, rajada=rajada, relogio=tempo
    )
    return TestClient(limitado, client=(origem, 40000))


# --------------------------------------------------------------------------- balde
def test_a_rajada_passa_e_o_pedido_seguinte_espera() -> None:
    tempo = Tempo()
    balde = BaldeDeFichas(120, 40, tempo)
    assert all(balde.tentar("a") is None for _ in range(40))
    assert balde.tentar("a") == 1  # 2 fichas por segundo: falta meio segundo, arredonda para 1


def test_as_fichas_voltam_com_o_tempo() -> None:
    tempo = Tempo()
    balde = BaldeDeFichas(120, 40, tempo)
    for _ in range(40):
        balde.tentar("a")
    tempo.agora += 1  # 2 fichas
    assert balde.tentar("a") is None
    assert balde.tentar("a") is None
    assert balde.tentar("a") is not None


def test_o_balde_nunca_passa_da_rajada() -> None:
    tempo = Tempo()
    balde = BaldeDeFichas(120, 5, tempo)
    balde.tentar("a")
    tempo.agora += 3600
    passaram = sum(balde.tentar("a") is None for _ in range(20))
    assert passaram == 5


def test_cada_ip_tem_o_seu_balde() -> None:
    balde = BaldeDeFichas(60, 1, Tempo())
    assert balde.tentar("a") is None
    assert balde.tentar("a") is not None
    assert balde.tentar("b") is None


def test_retry_after_e_o_tempo_ate_a_proxima_ficha() -> None:
    balde = BaldeDeFichas(6, 1, Tempo())  # uma ficha a cada 10 s
    balde.tentar("a")
    assert balde.tentar("a") == 10


def test_baldes_parados_sao_esquecidos() -> None:
    tempo = Tempo()
    balde = BaldeDeFichas(60, 2, tempo)
    for n in range(LIMPEZA_A_CADA - 1):
        balde.tentar(f"ip-{n}")
    tempo.agora += 3600  # todos estariam cheios de novo
    balde.tentar("o-ultimo")  # dispara a limpeza
    assert balde.tamanho == 1


# --------------------------------------------------------------------------- middleware
def test_passada_a_rajada_responde_429_com_retry_after() -> None:
    cliente = _cliente(Tempo(), por_minuto=60, rajada=3)
    assert [cliente.get("/api/v1/mapa").status_code for _ in range(3)] == [200, 200, 200]
    resposta = cliente.get("/api/v1/mapa")
    assert resposta.status_code == 429
    assert resposta.headers["retry-after"] == "1"
    assert resposta.headers["content-type"] == "application/json"
    assert "Muitos pedidos" in resposta.json()["detalhe"]


def test_depois_da_espera_volta_a_atender() -> None:
    tempo = Tempo()
    cliente = _cliente(tempo, por_minuto=60, rajada=1)
    cliente.get("/api/v1/mapa")
    assert cliente.get("/api/v1/mapa").status_code == 429
    tempo.agora += 1
    assert cliente.get("/api/v1/mapa").status_code == 200


def test_saude_nunca_e_limitada() -> None:
    cliente = _cliente(Tempo(), por_minuto=60, rajada=1)
    cliente.get("/api/v1/mapa")
    assert cliente.get("/api/v1/mapa").status_code == 429
    assert all(cliente.get("/api/v1/saude").status_code == 200 for _ in range(10))


def test_o_saude_nao_gasta_fichas() -> None:
    cliente = _cliente(Tempo(), por_minuto=60, rajada=1)
    for _ in range(10):
        cliente.get("/api/v1/saude")
    assert cliente.get("/api/v1/mapa").status_code == 200


def test_forjar_o_x_forwarded_for_nao_escapa_do_limite() -> None:
    """Quem não é o proxy muda o cabeçalho a cada pedido e continua no mesmo balde."""
    tempo = Tempo()
    redes = [ipaddress.ip_network("172.30.0.0/24")]
    app = IpReal(LimiteDePedidos(_app(), por_minuto=60, rajada=2, relogio=tempo), redes)
    cliente = TestClient(app, client=("198.51.100.7", 40000))
    codigos = [
        cliente.get("/api/v1/mapa", headers={"X-Forwarded-For": f"10.0.0.{n}"}).status_code
        for n in range(4)
    ]
    assert codigos == [200, 200, 429, 429]


def test_visitantes_atras_do_caddy_tem_baldes_separados() -> None:
    tempo = Tempo()
    redes = [ipaddress.ip_network("172.30.0.0/24")]
    app = IpReal(LimiteDePedidos(_app(), por_minuto=60, rajada=1, relogio=tempo), redes)
    cliente = TestClient(app, client=("172.30.0.2", 40000))
    primeiro = {"X-Forwarded-For": "203.0.113.1"}
    segundo = {"X-Forwarded-For": "203.0.113.2"}
    assert cliente.get("/api/v1/mapa", headers=primeiro).status_code == 200
    assert cliente.get("/api/v1/mapa", headers=primeiro).status_code == 429
    assert cliente.get("/api/v1/mapa", headers=segundo).status_code == 200
