"""Regras do docker-compose.prod.yml, do Caddyfile e do que sobe numa VM ARM (Ampere)."""

import ipaddress
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[4]
SERVICOS_ESPERADOS = {"caddy", "api", "worker", "migracao", "postgres"}
RESTART_AUTOMATICO = ["caddy", "api", "worker", "postgres"]


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    conteudo: dict[str, Any] = yaml.safe_load(
        (RAIZ / "docker-compose.prod.yml").read_text(encoding="utf-8")
    )
    return conteudo


@pytest.fixture(scope="module")
def servicos(compose: dict[str, Any]) -> dict[str, dict[str, Any]]:
    servicos: dict[str, dict[str, Any]] = compose["services"]
    return servicos


@pytest.fixture(scope="module")
def caddyfile() -> str:
    return (RAIZ / "deploy" / "Caddyfile").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- serviços e portas
def test_tem_os_servicos_pedidos_e_nenhum_frontend(servicos: dict[str, dict[str, Any]]) -> None:
    assert set(servicos) == SERVICOS_ESPERADOS


def test_so_o_caddy_publica_portas_e_sao_a_80_e_a_443(
    servicos: dict[str, dict[str, Any]],
) -> None:
    for nome, servico in servicos.items():
        publicadas = [str(p) for p in servico.get("ports", [])]
        if nome == "caddy":
            assert sorted(publicadas) == ["443:443", "80:80"]
        else:
            assert publicadas == [], f"{nome} não pode publicar portas: {publicadas}"


def test_o_postgres_nao_publica_porta_nenhuma(servicos: dict[str, dict[str, Any]]) -> None:
    assert "ports" not in servicos["postgres"]


def test_a_api_so_expoe_a_porta_para_a_rede_interna(servicos: dict[str, dict[str, Any]]) -> None:
    assert "ports" not in servicos["api"]
    assert [str(p) for p in servicos["api"]["expose"]] == ["8000"]


@pytest.mark.parametrize("nome", RESTART_AUTOMATICO)
def test_reinicia_sozinho(servicos: dict[str, dict[str, Any]], nome: str) -> None:
    assert servicos[nome]["restart"] == "unless-stopped"


def test_a_migracao_roda_uma_vez(servicos: dict[str, dict[str, Any]]) -> None:
    assert servicos["migracao"]["restart"] == "no"


@pytest.mark.parametrize("nome", ["caddy", "api", "worker", "postgres"])
def test_tem_healthcheck(servicos: dict[str, dict[str, Any]], nome: str) -> None:
    assert servicos[nome]["healthcheck"]["test"]


@pytest.mark.parametrize("nome", sorted(SERVICOS_ESPERADOS))
def test_gira_os_logs_do_docker(servicos: dict[str, dict[str, Any]], nome: str) -> None:
    registro = servicos[nome]["logging"]
    assert registro["driver"] == "json-file"
    assert registro["options"]["max-size"]
    assert int(registro["options"]["max-file"]) >= 2


# --------------------------------------------------------------------------- volumes
def test_o_banco_e_os_certificados_ficam_em_volumes_nomeados(
    compose: dict[str, Any], servicos: dict[str, dict[str, Any]]
) -> None:
    assert {"dados-postgres", "caddy-dados", "caddy-config", "logs-worker"} <= set(
        compose["volumes"]
    )
    assert "dados-postgres:/var/lib/postgresql" in servicos["postgres"]["volumes"]
    assert (
        "caddy-dados:/data" in servicos["caddy"]["volumes"]
    )  # onde o Caddy guarda os certificados
    assert "logs-worker:/app/logs" in servicos["worker"]["volumes"]


def test_o_postgres_nao_usa_tmpfs(servicos: dict[str, dict[str, Any]]) -> None:
    assert "tmpfs" not in servicos["postgres"]


# --------------------------------------------------------------------------- API e proxy
def test_a_api_roda_com_um_processo_e_sem_confiar_no_proxy_do_uvicorn(
    servicos: dict[str, dict[str, Any]],
) -> None:
    comando = servicos["api"]["command"]
    assert comando[comando.index("--workers") + 1] == "1"
    assert "--no-proxy-headers" in comando
    assert "--reload" not in comando


def test_a_api_confia_so_no_ip_fixo_do_caddy(
    compose: dict[str, Any], servicos: dict[str, dict[str, Any]]
) -> None:
    sub_rede = ipaddress.IPv4Network(compose["networks"]["publica"]["ipam"]["config"][0]["subnet"])
    ip_do_caddy = servicos["caddy"]["networks"]["publica"]["ipv4_address"]
    assert ipaddress.IPv4Address(ip_do_caddy) in sub_rede
    # um endereço só (/32), não a rede inteira
    assert servicos["api"]["environment"]["PROXY_CONFIAVEL"] == f"{ip_do_caddy}/32"
    # só o caddy e a própria API estão nessa rede
    na_publica = {n for n, s in servicos.items() if "publica" in (s.get("networks") or [])}
    assert na_publica == {"caddy", "api"}


def test_o_ip_fixo_do_caddy_fica_fora_da_faixa_dinamica_da_rede(
    compose: dict[str, Any], servicos: dict[str, dict[str, Any]]
) -> None:
    """Senão a API, que sobe antes do Caddy, pode receber o IP reservado a ele (achado no teste de
    fumaça: "Address already in use")."""
    config = compose["networks"]["publica"]["ipam"]["config"][0]
    sub_rede = ipaddress.IPv4Network(config["subnet"])
    dinamica = ipaddress.IPv4Network(config["ip_range"])
    fixo = ipaddress.IPv4Address(servicos["caddy"]["networks"]["publica"]["ipv4_address"])
    assert dinamica.subnet_of(sub_rede)
    assert fixo not in dinamica
    assert fixo in sub_rede


def test_o_banco_esta_so_na_rede_interna(servicos: dict[str, dict[str, Any]]) -> None:
    assert servicos["postgres"]["networks"] == ["interna"]


def test_producao_e_coletas_sao_definidas_pelo_compose(
    servicos: dict[str, dict[str, Any]],
) -> None:
    assert servicos["api"]["environment"]["AMBIENTE"] == "producao"
    assert servicos["worker"]["environment"]["COLETAS_AUTOMATICAS"].startswith(
        "${COLETAS_AUTOMATICAS:?"
    )


def test_a_documentacao_interativa_fica_desligada(servicos: dict[str, dict[str, Any]]) -> None:
    assert servicos["api"]["environment"]["API_DOCS_HABILITADA"] == "false"


def test_o_worker_grava_log_em_arquivo_no_volume(servicos: dict[str, dict[str, Any]]) -> None:
    assert servicos["worker"]["environment"]["DIRETORIO_LOGS"] == "/app/logs"


def test_nenhum_segredo_esta_escrito_no_compose() -> None:
    texto = (RAIZ / "docker-compose.prod.yml").read_text(encoding="utf-8")
    for linha in texto.splitlines():
        if re.search(r"(PASSWORD|API_KEY|SECRET)\s*:", linha):
            assert "${" in linha, f"valor fixo numa linha de segredo: {linha.strip()}"


# --------------------------------------------------------------------------- Caddyfile
def test_caddyfile_usa_o_dominio_da_variavel(caddyfile: str) -> None:
    assert "{$DOMINIO} {" in caddyfile


def test_caddyfile_manda_para_a_api(caddyfile: str) -> None:
    assert "reverse_proxy api:8000" in caddyfile


def test_caddyfile_substitui_o_x_forwarded_for_do_visitante(caddyfile: str) -> None:
    assert "header_up X-Forwarded-For {remote_host}" in caddyfile


def test_caddyfile_limita_tempos_e_corpo(caddyfile: str) -> None:
    for diretiva in ("read_header", "read_body", "max_size 1KB"):
        assert diretiva in caddyfile


def test_caddyfile_espera_a_api_voltar_antes_de_devolver_503(caddyfile: str) -> None:
    """Durante o reinício da API num deploy, o Caddy segura o pedido alguns segundos."""
    for diretiva in (
        "health_interval 5s",
        "health_timeout 2s",
        "health_passes 1",
        "health_fails 2",
        "lb_try_duration 10s",
        "lb_try_interval 250ms",
    ):
        assert diretiva in caddyfile
    assert "health_interval 30s" not in caddyfile


def test_caddyfile_comprime(caddyfile: str) -> None:
    assert "encode zstd gzip" in caddyfile


def test_caddyfile_manda_os_cabecalhos_de_seguranca(caddyfile: str) -> None:
    assert 'Strict-Transport-Security "max-age=31536000"' in caddyfile
    assert 'X-Content-Type-Options "nosniff"' in caddyfile
    assert "Referrer-Policy" in caddyfile
    assert "default-src 'none'; frame-ancestors 'none'" in caddyfile


def test_hsts_sem_preload_nem_subdominios(caddyfile: str) -> None:
    hsts = next(linha for linha in caddyfile.splitlines() if "Strict-Transport-Security" in linha)
    assert "preload" not in hsts
    assert "includeSubDomains" not in hsts


# --------------------------------------------------------------------------- arm64
IMAGENS_MULTIARQUITETURA = {
    "caddy:2",  # imagem oficial, publicada para linux/arm64
    "postgres:18",  # idem
}


def test_imagens_do_compose_sao_oficiais_multiarquitetura(
    servicos: dict[str, dict[str, Any]],
) -> None:
    de_terceiros = {s["image"] for s in servicos.values() if "build" not in s}
    assert de_terceiros == IMAGENS_MULTIARQUITETURA


def test_dockerfile_do_backend_parte_de_imagem_multiarquitetura() -> None:
    dockerfile = (RAIZ / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^FROM python:3\.13-slim\s*$", dockerfile, re.MULTILINE)
    assert "--platform" not in dockerfile  # nada preso a amd64


def _dependencias_de_producao(lock: dict[str, Any]) -> set[str]:
    pacotes = {p["name"]: p for p in lock["package"]}
    pendentes = [d["name"] for d in pacotes["farol"].get("dependencies", [])]
    vistos: set[str] = set()
    while pendentes:
        nome = pendentes.pop()
        if nome in vistos:
            continue
        vistos.add(nome)
        pendentes.extend(d["name"] for d in pacotes[nome].get("dependencies", []))
    return vistos


def test_toda_dependencia_de_producao_tem_wheel_para_linux_arm64() -> None:
    """Sem wheel para aarch64 (ou puro Python), o `uv sync` da VM tentaria compilar do código."""
    lock = tomllib.loads((RAIZ / "backend" / "uv.lock").read_text(encoding="utf-8"))
    pacotes = {p["name"]: p for p in lock["package"]}
    sem_wheel_arm = []
    for nome in sorted(_dependencias_de_producao(lock)):
        arquivos = [Path(w["url"]).name for w in pacotes[nome].get("wheels", [])]
        puro = any(a.endswith("-none-any.whl") for a in arquivos)
        arm = any("aarch64" in a and ("manylinux" in a or "musllinux" in a) for a in arquivos)
        if arquivos and not (puro or arm):
            sem_wheel_arm.append(nome)
        if not arquivos:
            sem_wheel_arm.append(f"{nome} (só código-fonte)")
    assert sem_wheel_arm == []
