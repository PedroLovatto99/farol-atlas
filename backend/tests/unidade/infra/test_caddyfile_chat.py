"""Caddyfile de produção: a rota do chat tem corpo maior, fluxo sem retenção e nada de compressão.

Tudo o que muda na borda vale só para `POST /api/v1/chat` (contracts/caddy-cors-limites.md): o
resto da API continua com corpo de até 1 KB e compressão. A sintaxe é conferida de verdade pelo
`caddy validate` (no CI e no percurso manual); aqui ficam as regras.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def caddyfile() -> str:
    return (RAIZ / "deploy" / "Caddyfile").read_text(encoding="utf-8")


def _sem_comentarios(texto: str) -> str:
    return "\n".join(linha.split("#", 1)[0] for linha in texto.splitlines())


def bloco(texto: str, abertura: str) -> str:
    """O conteúdo entre as chaves do bloco que começa em `abertura` (chaves balanceadas)."""
    texto = _sem_comentarios(texto)
    achado = re.search(re.escape(abertura) + r"\s*\{", texto)
    assert achado, f"bloco não encontrado: {abertura!r}"
    profundidade, inicio = 1, achado.end()
    for posicao in range(inicio, len(texto)):
        if texto[posicao] == "{" and texto[posicao - 1] != "$":
            profundidade += 1
        elif texto[posicao] == "}":
            profundidade -= 1
            if profundidade == 0:
                return texto[inicio:posicao]
    raise AssertionError(f"bloco sem fim: {abertura!r}")


def test_a_rota_do_chat_tem_um_handle_proprio(caddyfile: str) -> None:
    chat = bloco(caddyfile, "handle /api/v1/chat")
    assert re.search(r"request_body\s*\{\s*max_size 16KB\s*\}", chat)
    assert "flush_interval -1" in chat  # cada evento sai na hora
    assert "encode" not in chat  # sem compressão: o fluxo não é retido
    assert "import api" in chat


def test_o_resto_continua_com_1kb_e_compressao(caddyfile: str) -> None:
    site = bloco(caddyfile, "{$DOMINIO}")
    resto = bloco(site, "handle")  # o `handle` sem caminho: tudo o que não é o chat
    assert re.search(r"request_body\s*\{\s*max_size 1KB\s*\}", resto)
    assert "encode zstd gzip" in resto
    assert "flush_interval" not in resto


def test_compressao_e_limite_de_corpo_nao_valem_mais_para_o_site_inteiro(caddyfile: str) -> None:
    site = _sem_comentarios(bloco(caddyfile, "{$DOMINIO}"))
    fora_dos_handles = re.sub(r"handle[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", "", site)
    assert "encode" not in fora_dos_handles
    assert "request_body" not in fora_dos_handles


def test_o_proxy_comum_fica_num_snippet_com_ip_saude_e_espera(caddyfile: str) -> None:
    snippet = bloco(caddyfile, "(api)")
    for diretiva in (
        "reverse_proxy api:8000",
        "header_up X-Forwarded-For {remote_host}",
        "header_up -X-Real-IP",
        "health_uri /api/v1/saude",
        "lb_try_duration 10s",
    ):
        assert diretiva in snippet


def test_os_cabecalhos_de_seguranca_valem_para_todas_as_respostas(caddyfile: str) -> None:
    site = bloco(caddyfile, "{$DOMINIO}")
    cabecalhos = bloco(site, "header")
    assert 'Strict-Transport-Security "max-age=31536000"' in cabecalhos
    assert 'X-Content-Type-Options "nosniff"' in cabecalhos
    assert "default-src 'none'; frame-ancestors 'none'" in cabecalhos


def test_a_escrita_continua_acima_dos_20_s_do_chat(caddyfile: str) -> None:
    assert re.search(r"write 30s", caddyfile)
