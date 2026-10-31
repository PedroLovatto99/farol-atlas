"""Cache de leitura: serve da memória, mas nunca dado de antes de uma escrita por mais de 15 s."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from farol.api.cache import CacheDeLeitura, VersaoMemorizada

TTL = 300
VERSAO_TTL = 15


class Tempo:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora


class Banco:
    """O contador de versão e o conteúdo que as rotas devolvem."""

    def __init__(self) -> None:
        self.versao = 1
        self.leituras_da_versao = 0
        self.falha = False
        self.chamadas = 0
        self.conteudo = "antigo"

    def ler_versao(self) -> int:
        self.leituras_da_versao += 1
        if self.falha:
            raise RuntimeError("banco fora do ar")
        return self.versao

    def escrever(self, conteudo: str) -> None:
        self.conteudo = conteudo
        self.versao += 1


def _montar(banco: Banco, tempo: Tempo) -> TestClient:
    app = FastAPI()

    @app.get("/api/v1/mapa")
    def mapa() -> dict[str, str]:
        banco.chamadas += 1
        return {"conteudo": banco.conteudo}

    @app.get("/api/v1/paises/{codigo}")
    def pais(codigo: str) -> dict[str, str]:
        banco.chamadas += 1
        if codigo == "ZZ":
            raise HTTPException(status_code=404, detail="Território não encontrado")
        return {"codigo": codigo, "conteudo": banco.conteudo}

    @app.get("/api/v1/saude")
    def saude() -> dict[str, str]:
        banco.chamadas += 1
        return {"banco": "ok"}

    @app.get("/api/v1/outra")
    def outra() -> dict[str, str]:
        banco.chamadas += 1
        return {"x": "y"}

    @app.post("/api/v1/mapa")
    def escrever() -> dict[str, str]:
        banco.chamadas += 1
        return {}

    app.add_middleware(
        CacheDeLeitura,
        versao=VersaoMemorizada(banco.ler_versao, VERSAO_TTL, tempo),
        ttl=TTL,
        max_age_do_navegador=60,
        relogio=tempo,
    )
    return TestClient(app)


def _cenario() -> tuple[TestClient, Banco, Tempo]:
    banco, tempo = Banco(), Tempo()
    return _montar(banco, tempo), banco, tempo


def test_o_segundo_pedido_sai_da_memoria() -> None:
    cliente, banco, _ = _cenario()
    primeira = cliente.get("/api/v1/mapa")
    segunda = cliente.get("/api/v1/mapa")
    assert banco.chamadas == 1
    assert primeira.json() == segunda.json() == {"conteudo": "antigo"}
    assert segunda.headers["content-type"] == "application/json"


def test_o_navegador_recebe_cache_control_em_acerto_e_em_erro_de_cache() -> None:
    cliente, _, _ = _cenario()
    assert cliente.get("/api/v1/mapa").headers["cache-control"] == "public, max-age=60"
    assert cliente.get("/api/v1/mapa").headers["cache-control"] == "public, max-age=60"


def test_cada_rota_e_cada_pais_tem_a_sua_entrada() -> None:
    cliente, banco, _ = _cenario()
    assert cliente.get("/api/v1/paises/US").json()["codigo"] == "US"
    assert cliente.get("/api/v1/paises/BR").json()["codigo"] == "BR"
    assert cliente.get("/api/v1/paises/US").json()["codigo"] == "US"
    assert banco.chamadas == 2


def test_escrita_nova_vale_depois_de_no_maximo_15_segundos() -> None:
    cliente, banco, tempo = _cenario()
    cliente.get("/api/v1/mapa")
    banco.escrever("novo")  # coleta, classificação ou comando do dono
    tempo.agora += VERSAO_TTL  # a versão é consultada de novo
    assert cliente.get("/api/v1/mapa").json() == {"conteudo": "novo"}


def test_dentro_dos_15_segundos_a_versao_nao_e_consultada_de_novo() -> None:
    cliente, banco, tempo = _cenario()
    cliente.get("/api/v1/mapa")
    banco.escrever("novo")
    tempo.agora += VERSAO_TTL - 1
    assert cliente.get("/api/v1/mapa").json() == {"conteudo": "antigo"}  # o limite máximo do atraso
    assert banco.leituras_da_versao == 1


def test_a_versao_e_consultada_uma_vez_por_intervalo_para_todas_as_rotas() -> None:
    cliente, banco, tempo = _cenario()
    for rota in ("/api/v1/mapa", "/api/v1/paises/US", "/api/v1/paises/BR", "/api/v1/mapa"):
        cliente.get(rota)
    assert banco.leituras_da_versao == 1
    tempo.agora += VERSAO_TTL
    cliente.get("/api/v1/mapa")
    assert banco.leituras_da_versao == 2


def test_versao_nova_descarta_todas_as_entradas() -> None:
    cliente, banco, tempo = _cenario()
    cliente.get("/api/v1/paises/US")
    cliente.get("/api/v1/paises/BR")
    banco.escrever("novo")
    tempo.agora += VERSAO_TTL
    cliente.get("/api/v1/paises/US")
    cliente.get("/api/v1/paises/BR")
    assert banco.chamadas == 4


def test_passado_o_ttl_refaz_mesmo_sem_escrita() -> None:
    cliente, banco, tempo = _cenario()
    cliente.get("/api/v1/mapa")
    tempo.agora += TTL - 1
    cliente.get("/api/v1/mapa")
    assert banco.chamadas == 1
    tempo.agora += 1
    cliente.get("/api/v1/mapa")
    assert banco.chamadas == 2


def test_erro_nao_e_guardado() -> None:
    cliente, banco, _ = _cenario()
    assert cliente.get("/api/v1/paises/ZZ").status_code == 404
    assert cliente.get("/api/v1/paises/ZZ").status_code == 404
    assert banco.chamadas == 2
    assert "cache-control" not in cliente.get("/api/v1/paises/ZZ").headers


def test_o_saude_nunca_e_guardado_e_o_navegador_nao_o_guarda() -> None:
    cliente, banco, _ = _cenario()
    cliente.get("/api/v1/saude")
    resposta = cliente.get("/api/v1/saude")
    assert banco.chamadas == 2
    assert resposta.headers["cache-control"] == "no-store"
    assert banco.leituras_da_versao == 0


def test_rotas_fora_da_lista_e_metodos_de_escrita_passam_direto() -> None:
    cliente, banco, _ = _cenario()
    cliente.get("/api/v1/outra")
    cliente.get("/api/v1/outra")
    cliente.post("/api/v1/mapa")
    cliente.post("/api/v1/mapa")
    assert banco.chamadas == 4
    assert "cache-control" not in cliente.get("/api/v1/outra").headers


def test_sem_conseguir_ler_a_versao_o_pedido_passa_sem_cache() -> None:
    cliente, banco, _ = _cenario()
    banco.falha = True
    primeira = cliente.get("/api/v1/mapa")
    cliente.get("/api/v1/mapa")
    assert primeira.status_code == 200
    assert banco.chamadas == 2
    assert "cache-control" not in primeira.headers


def test_depois_que_o_banco_volta_o_cache_volta() -> None:
    cliente, banco, tempo = _cenario()
    banco.falha = True
    cliente.get("/api/v1/mapa")
    banco.falha = False
    tempo.agora += VERSAO_TTL
    cliente.get("/api/v1/mapa")
    cliente.get("/api/v1/mapa")
    assert banco.chamadas == 2


def test_a_consulta_de_cada_pais_distinta_pela_query_string() -> None:
    cliente, banco, _ = _cenario()
    cliente.get("/api/v1/mapa?a=1")
    cliente.get("/api/v1/mapa?a=2")
    cliente.get("/api/v1/mapa?a=1")
    assert banco.chamadas == 2
