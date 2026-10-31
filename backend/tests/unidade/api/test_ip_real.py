"""IP real do visitante: o X-Forwarded-For só vale quando o pedido vem do proxy (Caddy)."""

import ipaddress

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from farol.api.ip_real import IpReal, ip_do_visitante

REDE_DO_CADDY = ipaddress.ip_network("172.30.0.0/24")
CADDY = "172.30.0.2"
VISITANTE = "203.0.113.9"
FORJADO = "6.6.6.6"


def _eco() -> Starlette:
    async def eco(requisicao: Request) -> PlainTextResponse:
        return PlainTextResponse(requisicao.client.host if requisicao.client else "sem cliente")

    return Starlette(routes=[Route("/", eco)])


def _cliente(origem: str, redes: list[ipaddress.IPv4Network] | None = None) -> TestClient:
    confiaveis = [REDE_DO_CADDY] if redes is None else redes
    return TestClient(IpReal(_eco(), confiaveis), client=(origem, 40000))


def test_do_caddy_usa_o_ip_do_cabecalho() -> None:
    resposta = _cliente(CADDY).get("/", headers={"X-Forwarded-For": VISITANTE})
    assert resposta.text == VISITANTE


def test_forjado_por_quem_nao_e_o_caddy_e_ignorado() -> None:
    resposta = _cliente("198.51.100.7").get("/", headers={"X-Forwarded-For": FORJADO})
    assert resposta.text == "198.51.100.7"


def test_sem_redes_confiaveis_o_cabecalho_nunca_vale() -> None:
    resposta = _cliente(CADDY, redes=[]).get("/", headers={"X-Forwarded-For": FORJADO})
    assert resposta.text == CADDY


def test_do_caddy_sem_cabecalho_fica_o_ip_do_caddy() -> None:
    assert _cliente(CADDY).get("/").text == CADDY


def test_cadeia_forjada_pela_esquerda_nao_engana() -> None:
    """O Caddy acrescenta o IP de quem o chamou à direita; o que está à esquerda é do visitante."""
    resposta = _cliente(CADDY).get("/", headers={"X-Forwarded-For": f"{FORJADO}, {VISITANTE}"})
    assert resposta.text == VISITANTE


def test_pula_proxies_confiaveis_na_cadeia() -> None:
    cadeia = f"{VISITANTE}, 172.30.0.7"
    assert _cliente(CADDY).get("/", headers={"X-Forwarded-For": cadeia}).text == VISITANTE


def test_cabecalho_malformado_fica_com_o_ip_do_par() -> None:
    resposta = _cliente(CADDY).get("/", headers={"X-Forwarded-For": "isto-nao-e-ip"})
    assert resposta.text == CADDY


def test_ipv6_do_visitante() -> None:
    resposta = _cliente(CADDY).get("/", headers={"X-Forwarded-For": "2001:db8::1"})
    assert resposta.text == "2001:db8::1"


@pytest.mark.parametrize("par", [None, "", "testclient", "nao-e-ip"])
def test_par_invalido_nao_derruba(par: str | None) -> None:
    assert ip_do_visitante(par, VISITANTE, [REDE_DO_CADDY]) == par
