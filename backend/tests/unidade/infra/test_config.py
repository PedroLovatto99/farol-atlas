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
        "CHAT_HABILITADO",
        "LLM_CHAT",
        "LLM_CHAT_ALTERNATIVO",
        "GOOGLE_API_KEY_CHAT",
        "EMBEDDINGS_MODELO",
        "EMBEDDINGS_DIMENSOES",
        "CHAT_LIMITE_POR_HORA_POR_IP",
        "CHAT_LIMITE_POR_DIA",
        "CHAT_TEMPO_MAXIMO_SEGUNDOS",
        "CHAT_PERGUNTA_MAX_CARACTERES",
        "CHAT_HISTORICO_MENSAGENS",
        "CHAT_TRECHOS_POR_PERGUNTA",
        "INDEXACAO_INTERVALO_MINUTOS",
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


# --------------------------------------------------------------------------- chat (003)
def test_padroes_do_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    configuracao = criar()
    assert configuracao.chat_habilitado is False  # só liga por decisão explícita (T133a)
    assert configuracao.llm_chat == configuracao.llm_classificador  # ausente = o do classificador
    assert configuracao.llm_chat_alternativo == ""
    assert configuracao.google_api_key_chat is None
    assert configuracao.embeddings_modelo == "google_genai:gemini-embedding-001"
    assert configuracao.embeddings_dimensoes == 768
    assert configuracao.chat_limite_por_hora_por_ip == 20
    assert configuracao.chat_limite_por_dia == 500
    assert configuracao.chat_tempo_maximo_segundos == 20
    assert configuracao.chat_pergunta_max_caracteres == 500
    assert configuracao.chat_historico_mensagens == 6
    assert configuracao.chat_trechos_por_pergunta == 4
    assert configuracao.indexacao_intervalo_minutos == 5


def test_llm_chat_vem_da_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("LLM_CHAT", "google_genai:modelo-do-chat")
    monkeypatch.setenv("LLM_CHAT_ALTERNATIVO", "google_genai:modelo-reserva")
    configuracao = criar()
    assert configuracao.llm_chat == "google_genai:modelo-do-chat"
    assert configuracao.llm_chat_alternativo == "google_genai:modelo-reserva"


def test_chave_do_chat_nunca_aparece_no_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("GOOGLE_API_KEY_CHAT", "chave-do-chat-secreta")
    configuracao = criar()
    assert configuracao.google_api_key_chat is not None
    assert configuracao.google_api_key_chat.get_secret_value() == "chave-do-chat-secreta"
    assert "chave-do-chat-secreta" not in repr(configuracao)
    assert "chave-do-chat-secreta" not in str(configuracao)


@pytest.mark.parametrize("variavel", ["CHAT_LIMITE_POR_HORA_POR_IP", "CHAT_LIMITE_POR_DIA"])
@pytest.mark.parametrize("valor", ["0", "-1"])
def test_producao_com_chat_ligado_exige_limites_positivos(
    monkeypatch: pytest.MonkeyPatch, variavel: str, valor: str
) -> None:
    _producao(monkeypatch, CHAT_HABILITADO="true", GOOGLE_API_KEY_CHAT="chave", **{variavel: valor})
    with pytest.raises(ValidationError, match=variavel):
        criar()


def test_producao_com_chat_ligado_e_limites_padrao_e_aceita(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _producao(monkeypatch, CHAT_HABILITADO="true", GOOGLE_API_KEY_CHAT="chave")
    assert criar().chat_habilitado is True


@pytest.mark.parametrize(
    "ambiente",
    [
        {},  # LLM_CHAT vazio = o modelo do classificador, que é do Google
        {"LLM_CHAT": "google_genai:modelo-do-chat"},
        {"LLM_CHAT": "ollama:llama3", "LLM_CHAT_ALTERNATIVO": "google_genai:reserva"},
        {"LLM_CHAT": "ollama:llama3"},  # o embedding padrão é do Google
    ],
)
def test_producao_com_chat_ligado_exige_a_chave_propria_do_chat(
    monkeypatch: pytest.MonkeyPatch, ambiente: dict[str, str]
) -> None:
    """A chave da coleta (GOOGLE_API_KEY) não serve: o chat nunca cai nela (FR-028)."""
    _producao(monkeypatch, CHAT_HABILITADO="true", GOOGLE_API_KEY="chave-da-coleta", **ambiente)
    with pytest.raises(ValidationError, match="GOOGLE_API_KEY_CHAT"):
        criar()


def test_producao_sem_google_no_chat_nao_exige_a_chave_do_chat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _producao(
        monkeypatch,
        CHAT_HABILITADO="true",
        LLM_CHAT="ollama:llama3",
        EMBEDDINGS_MODELO="ollama:nomic-embed-text",
    )
    assert criar().chat_disponivel is True


def test_desenvolvimento_sem_chave_do_chat_deixa_o_chat_indisponivel_com_motivo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A partida segue (só o chat fica de fora) e o motivo diz o que falta."""
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("CHAT_HABILITADO", "true")
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-da-coleta")
    configuracao = criar()
    assert configuracao.chat_disponivel is False
    assert configuracao.motivo_chat_indisponivel is not None
    assert "GOOGLE_API_KEY_CHAT" in configuracao.motivo_chat_indisponivel
    assert "chave-da-coleta" not in configuracao.motivo_chat_indisponivel


def test_chat_com_a_chave_propria_esta_disponivel_e_desligado_nao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("GOOGLE_API_KEY_CHAT", "chave")
    assert criar().chat_disponivel is False  # chave sem CHAT_HABILITADO: segue desligado
    monkeypatch.setenv("CHAT_HABILITADO", "true")
    configuracao = criar()
    assert configuracao.chat_disponivel is True
    assert configuracao.motivo_chat_indisponivel is None


@pytest.mark.parametrize("ambiente", [{"CHAT_HABILITADO": "false"}, {}])
def test_producao_com_chat_desligado_nao_exige_limites(
    monkeypatch: pytest.MonkeyPatch, ambiente: dict[str, str]
) -> None:
    _producao(monkeypatch, CHAT_LIMITE_POR_HORA_POR_IP="0", CHAT_LIMITE_POR_DIA="0", **ambiente)
    assert criar().chat_habilitado is False


def test_desenvolvimento_com_chat_ligado_nao_exige_limites(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("CHAT_HABILITADO", "true")
    monkeypatch.setenv("CHAT_LIMITE_POR_DIA", "0")
    assert criar().chat_limite_por_dia == 0
