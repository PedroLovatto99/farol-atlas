"""Configuração por variáveis de ambiente (pydantic-settings)."""

import pytest
from pydantic import ValidationError

from farol.infra import Configuracoes

URL = "postgresql+psycopg://farol:senha-secreta@postgres:5432/farol"


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove do ambiente tudo o que a configuração lê, para cada teste começar do zero."""
    for nome in (
        "DATABASE_URL",
        "DATABASE_URL_TESTE",
        "CORS_ORIGENS",
        "API_DOCS_HABILITADA",
        "CONTATO_COLETA",
        "PAUSA_SEGUNDOS",
        "LIMITE_HORAS_PARTIDA",
        "LLM_CLASSIFICADOR",
        "LLM_TRADUTOR",
        "GOOGLE_API_KEY",
        "OLLAMA_BASE_URL",
        "DIRETORIO_DADOS",
        "AMBIENTE",
        "PROXY_CONFIAVEL",
        "LIMITE_PEDIDOS_POR_MINUTO",
        "LIMITE_RAJADA",
        "CACHE_TTL_SEGUNDOS",
        "CACHE_VERSAO_SEGUNDOS",
        "CACHE_MAX_AGE_NAVEGADOR_SEGUNDOS",
        "COLETAS_AUTOMATICAS",
        "DIRETORIO_LOGS",
    ):
        monkeypatch.delenv(nome, raising=False)


def criar() -> Configuracoes:
    """Lê só o ambiente do teste (nada do .env do desenvolvedor)."""
    return Configuracoes(_env_file=None)


def test_database_url_e_obrigatoria() -> None:
    with pytest.raises(ValidationError):
        criar()


def test_cors_origens_vira_lista(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("CORS_ORIGENS", "http://localhost:5173, https://farol.exemplo.com")
    configuracao = criar()
    assert configuracao.cors_origens == ["http://localhost:5173", "https://farol.exemplo.com"]


def test_cors_origens_vazio_nao_aceita_ninguem(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    assert criar().cors_origens == []


def test_docs_da_api_desligadas_por_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    assert criar().api_docs_habilitada is False


def test_docs_da_api_ligadas_por_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("API_DOCS_HABILITADA", "true")
    assert criar().api_docs_habilitada is True


def test_valores_padrao_da_coleta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    configuracao = criar()
    assert configuracao.pausa_segundos == 2.0
    assert configuracao.limite_horas_partida == 20
    assert configuracao.llm_classificador == "google_genai:gemini-3.6-flash"


def test_segredos_nunca_aparecem_no_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-super-secreta")
    configuracao = criar()
    texto = f"{configuracao!r} {configuracao!s}"
    assert "senha-secreta" not in texto
    assert "chave-super-secreta" not in texto
    assert configuracao.database_url.get_secret_value() == URL


def test_tradutor_sem_variavel_usa_o_modelo_do_classificador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    configuracao = criar()
    assert configuracao.llm_tradutor == configuracao.llm_classificador

    monkeypatch.setenv("LLM_CLASSIFICADOR", "ollama:llama3")
    assert criar().llm_tradutor == "ollama:llama3"


def test_tradutor_vazio_no_env_tambem_usa_o_do_classificador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("LLM_CLASSIFICADOR", "ollama:llama3")
    monkeypatch.setenv("LLM_TRADUTOR", "   ")
    assert criar().llm_tradutor == "ollama:llama3"


def test_tradutor_com_variavel_vale_a_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("LLM_CLASSIFICADOR", "ollama:llama3")
    monkeypatch.setenv("LLM_TRADUTOR", "google_genai:gemini-3.6-flash")
    configuracao = criar()
    assert configuracao.llm_tradutor == "google_genai:gemini-3.6-flash"
    assert configuracao.llm_classificador == "ollama:llama3"


# --------------------------------------------------------------------------- produção e limites
def _producao(monkeypatch: pytest.MonkeyPatch, **ambiente: str) -> None:
    """Um ambiente de produção completo; `ambiente` troca ou acrescenta variáveis."""
    padrao = {
        "DATABASE_URL": URL,
        "AMBIENTE": "producao",
        "CORS_ORIGENS": "https://farol.vercel.app",
        "PROXY_CONFIAVEL": "172.30.0.0/24",
        "COLETAS_AUTOMATICAS": "true",
    }
    for nome, valor in {**padrao, **ambiente}.items():
        monkeypatch.setenv(nome, valor)


def test_producao_completa_e_aceita(monkeypatch: pytest.MonkeyPatch) -> None:
    _producao(monkeypatch)
    configuracao = criar()
    assert configuracao.ambiente == "producao"
    assert configuracao.coletas_ligadas is True
    assert [str(rede) for rede in configuracao.redes_confiaveis] == ["172.30.0.0/24"]


def test_producao_exige_coletas_automaticas_definidas(monkeypatch: pytest.MonkeyPatch) -> None:
    _producao(monkeypatch)
    monkeypatch.delenv("COLETAS_AUTOMATICAS")
    with pytest.raises(ValidationError, match="COLETAS_AUTOMATICAS"):
        criar()


def test_producao_aceita_coletas_desligadas_se_forem_definidas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _producao(monkeypatch, COLETAS_AUTOMATICAS="false")
    assert criar().coletas_ligadas is False


@pytest.mark.parametrize(
    "origens", ["", "http://farol.vercel.app", "*", "https://a.app, http://localhost:5173"]
)
def test_producao_so_aceita_origens_https(monkeypatch: pytest.MonkeyPatch, origens: str) -> None:
    _producao(monkeypatch, CORS_ORIGENS=origens)
    with pytest.raises(ValidationError, match="CORS_ORIGENS"):
        criar()


def test_producao_exige_a_rede_do_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    _producao(monkeypatch)
    monkeypatch.delenv("PROXY_CONFIAVEL")
    with pytest.raises(ValidationError, match="PROXY_CONFIAVEL"):
        criar()


def test_rede_do_proxy_invalida_e_recusada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("PROXY_CONFIAVEL", "isto-nao-e-rede")
    with pytest.raises(ValidationError, match="PROXY_CONFIAVEL"):
        criar()


def test_varias_redes_do_proxy_separadas_por_virgula(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("PROXY_CONFIAVEL", "172.30.0.0/24, fd00::/8")
    assert len(criar().redes_confiaveis) == 2


def test_desenvolvimento_nao_exige_nada_alem_do_banco(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    configuracao = criar()
    assert configuracao.ambiente == "desenvolvimento"
    assert configuracao.proxy_confiavel == []


def test_coletas_automaticas_ficam_desligadas_se_nada_for_dito(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    assert criar().coletas_ligadas is False


def test_coletas_automaticas_ligadas_por_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("COLETAS_AUTOMATICAS", "true")
    assert criar().coletas_ligadas is True


def test_limites_e_cache_tem_os_padroes_combinados(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    configuracao = criar()
    assert configuracao.limite_pedidos_por_minuto == 120
    assert configuracao.limite_rajada == 40
    assert configuracao.cache_ttl_segundos == 300
    assert configuracao.cache_versao_segundos == 15
    assert configuracao.cache_max_age_navegador_segundos == 60


def test_limites_vem_do_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("LIMITE_PEDIDOS_POR_MINUTO", "30")
    monkeypatch.setenv("LIMITE_RAJADA", "10")
    configuracao = criar()
    assert (configuracao.limite_pedidos_por_minuto, configuracao.limite_rajada) == (30, 10)
