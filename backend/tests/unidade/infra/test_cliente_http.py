"""Cliente educado: robots.txt por host, identificação, pausa e parada ao ser bloqueado.

Nenhum teste acessa a internet: a sessão HTTP é falsa.
"""

from dataclasses import dataclass, field

import pytest
import requests

from farol.infra import ClienteEducado

ROBOTS_LIBERADO = "User-agent: *\nDisallow:\n"
ROBOTS_BLOQUEIA_ALERTAS = "User-agent: *\nDisallow: /privado/\n"
ROBOTS_BLOQUEIA_TUDO = "User-agent: *\nDisallow: /\n"
PAGINA = "<html><body><p>conteúdo real</p></body></html>"
VERIFICACAO = "<html>Please wait while we are testing whether you are a human</html>"


@dataclass
class RespostaFalsa:
    status_code: int = 200
    text: str = PAGINA
    encoding: str | None = "utf-8"
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class SessaoFalsa:
    respostas: dict[str, RespostaFalsa | Exception]
    headers: dict[str, str] = field(default_factory=dict)
    chamadas: list[str] = field(default_factory=list)

    def get(self, url: str, *, timeout: float, allow_redirects: bool = True) -> RespostaFalsa:
        assert allow_redirects is False  # o cliente segue os desvios, um a um, conferindo o robots
        self.chamadas.append(url)
        resposta = self.respostas.get(url, RespostaFalsa(status_code=404, text=""))
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def criar(
    respostas: dict[str, RespostaFalsa | Exception],
    *,
    contato: str = "https://github.com/exemplo",
    pausa: float = 2.0,
) -> tuple[ClienteEducado, SessaoFalsa, list[float]]:
    sessao = SessaoFalsa(respostas)
    pausas: list[float] = []
    cliente = ClienteEducado(contato, pausa_segundos=pausa, sessao=sessao, dormir=pausas.append)
    return cliente, sessao, pausas


# --------------------------------------------------------------------------- identificação
def test_user_agent_identifica_o_projeto_e_o_contato() -> None:
    cliente, sessao, _ = criar({})
    assert "FarolAtlas" in cliente.user_agent
    assert "https://github.com/exemplo" in cliente.user_agent
    assert cliente.user_agent == (
        f"FarolAtlas/0.1 (https://github.com/exemplo; projeto pessoal) "
        f"python-requests/{requests.__version__}"
    )
    assert sessao.headers["User-Agent"] == cliente.user_agent


@pytest.mark.parametrize("contato", ["", "   "])
def test_exige_um_contato(contato: str) -> None:
    with pytest.raises(ValueError, match="contato"):
        ClienteEducado(contato, sessao=SessaoFalsa({}), dormir=lambda _: None)


# --------------------------------------------------------------------------- robots.txt
def test_baixa_a_pagina_depois_de_consultar_o_robots() -> None:
    cliente, sessao, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": RespostaFalsa(),
        }
    )
    pagina = cliente.baixar("https://www.gov.br/a")
    assert pagina.ok
    assert pagina.html == PAGINA
    assert pagina.motivo is None
    assert sessao.chamadas == ["https://www.gov.br/robots.txt", "https://www.gov.br/a"]


def test_consulta_o_robots_uma_vez_por_host() -> None:
    cliente, sessao, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": RespostaFalsa(),
            "https://www.gov.br/b": RespostaFalsa(),
            "https://outro.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://outro.gov.br/c": RespostaFalsa(),
        }
    )
    for url in ("https://www.gov.br/a", "https://www.gov.br/b", "https://outro.gov.br/c"):
        assert cliente.baixar(url).ok
    robots = [c for c in sessao.chamadas if c.endswith("/robots.txt")]
    assert robots == ["https://www.gov.br/robots.txt", "https://outro.gov.br/robots.txt"]


def test_nao_baixa_o_que_o_robots_proibe() -> None:
    cliente, sessao, _ = criar(
        {"https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_BLOQUEIA_ALERTAS)}
    )
    pagina = cliente.baixar("https://www.gov.br/privado/x")
    assert not pagina.ok
    assert pagina.motivo == "proibida pelo robots.txt"
    assert "https://www.gov.br/privado/x" not in sessao.chamadas
    assert cliente.interrompido_por is None  # só esta página; as outras seguem


def test_robots_inexistente_libera_tudo() -> None:
    cliente, _, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(status_code=404, text=""),
            "https://www.gov.br/a": RespostaFalsa(),
        }
    )
    assert cliente.baixar("https://www.gov.br/a").ok


def test_robots_que_nao_da_para_ler_nao_libera_a_pagina() -> None:
    cliente, sessao, _ = criar(
        {"https://www.gov.br/robots.txt": requests.ConnectionError("sem rede")}
    )
    pagina = cliente.baixar("https://www.gov.br/a")
    assert not pagina.ok
    assert pagina.motivo == "robots.txt inacessível"
    assert "https://www.gov.br/a" not in sessao.chamadas


# --------------------------------------------------------------------------- pausa
def test_pausa_depois_de_cada_requisicao() -> None:
    cliente, sessao, pausas = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": RespostaFalsa(),
            "https://www.gov.br/b": RespostaFalsa(),
        },
        pausa=3.5,
    )
    cliente.baixar("https://www.gov.br/a")
    cliente.baixar("https://www.gov.br/b")
    assert len(pausas) == len(sessao.chamadas) == 3
    assert set(pausas) == {3.5}


def test_a_pausa_e_configuravel() -> None:
    cliente, _, pausas = criar(
        {"https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO)}, pausa=0.0
    )
    cliente.baixar("https://www.gov.br/a")
    assert set(pausas) == {0.0}


# --------------------------------------------------------------------------- bloqueio
@pytest.mark.parametrize(
    ("resposta", "motivo"),
    [
        (RespostaFalsa(status_code=403, text="proibido"), "bloqueado (HTTP 403)"),
        (RespostaFalsa(status_code=429, text="muitas requisições"), "bloqueado (HTTP 429)"),
        (RespostaFalsa(text=VERIFICACAO), "caiu na verificação humana"),
        (RespostaFalsa(status_code=503, text=VERIFICACAO), "caiu na verificação humana"),
    ],
    ids=["403", "429", "verificacao-humana", "verificacao-com-503"],
)
def test_bloqueio_interrompe_e_nunca_insiste(resposta: RespostaFalsa, motivo: str) -> None:
    cliente, sessao, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": resposta,
            "https://www.gov.br/b": RespostaFalsa(),
        }
    )
    primeira = cliente.baixar("https://www.gov.br/a")
    assert not primeira.ok
    assert primeira.motivo == motivo
    assert cliente.interrompido_por == motivo

    chamadas_antes = len(sessao.chamadas)
    segunda = cliente.baixar("https://www.gov.br/b")
    assert not segunda.ok
    assert segunda.motivo == motivo
    assert len(sessao.chamadas) == chamadas_antes  # nenhuma requisição nova


def test_bloqueio_no_robots_interrompe() -> None:
    cliente, sessao, _ = criar({"https://www.gov.br/robots.txt": RespostaFalsa(status_code=429)})
    pagina = cliente.baixar("https://www.gov.br/a")
    assert pagina.motivo == "bloqueado (HTTP 429)"
    assert cliente.interrompido_por == "bloqueado (HTTP 429)"
    assert sessao.chamadas == ["https://www.gov.br/robots.txt"]


# --------------------------------------------------------------------------- falhas de uma página
def test_erro_http_comum_so_falha_aquela_pagina() -> None:
    cliente, _, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": RespostaFalsa(status_code=500, text="erro"),
            "https://www.gov.br/b": RespostaFalsa(),
        }
    )
    ruim = cliente.baixar("https://www.gov.br/a")
    assert not ruim.ok
    assert ruim.motivo == "HTTP 500"
    assert cliente.interrompido_por is None
    assert cliente.baixar("https://www.gov.br/b").ok


def test_erro_de_conexao_so_falha_aquela_pagina() -> None:
    cliente, _, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": requests.Timeout("lento"),
            "https://www.gov.br/b": RespostaFalsa(),
        }
    )
    ruim = cliente.baixar("https://www.gov.br/a")
    assert not ruim.ok
    assert ruim.motivo == "erro de conexão: Timeout"
    assert cliente.interrompido_por is None
    assert cliente.baixar("https://www.gov.br/b").ok


# --------------------------------------------------------------------------- redirecionamentos
def desvio(destino: str, status: int = 301) -> RespostaFalsa:
    return RespostaFalsa(status_code=status, text="", headers={"Location": destino})


def test_segue_o_redirecionamento_e_informa_a_url_final() -> None:
    cliente, sessao, _ = criar(
        {
            "https://velho.itamaraty.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://velho.itamaraty.gov.br/pt-br/": desvio("https://www.gov.br/mre/pt-br/posto"),
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/mre/pt-br/posto": RespostaFalsa(),
        }
    )
    pagina = cliente.baixar("https://velho.itamaraty.gov.br/pt-br/")
    assert pagina.ok
    assert pagina.html == PAGINA
    assert pagina.url == "https://velho.itamaraty.gov.br/pt-br/"
    assert pagina.url_final == "https://www.gov.br/mre/pt-br/posto"
    assert sessao.chamadas == [
        "https://velho.itamaraty.gov.br/robots.txt",
        "https://velho.itamaraty.gov.br/pt-br/",
        "https://www.gov.br/robots.txt",
        "https://www.gov.br/mre/pt-br/posto",
    ]


def test_sem_redirecionamento_a_url_final_e_a_propria_url() -> None:
    cliente, _, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": RespostaFalsa(),
        }
    )
    assert cliente.baixar("https://www.gov.br/a").url_final == "https://www.gov.br/a"


def test_destino_relativo_e_resolvido_a_partir_da_url_atual() -> None:
    cliente, _, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/mre/a": desvio("/mre/b", status=302),
            "https://www.gov.br/mre/b": RespostaFalsa(),
        }
    )
    assert cliente.baixar("https://www.gov.br/mre/a").url_final == "https://www.gov.br/mre/b"


def test_o_destino_do_redirecionamento_tambem_obedece_ao_robots() -> None:
    cliente, sessao, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": desvio("https://fechado.gov.br/x"),
            "https://fechado.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_BLOQUEIA_TUDO),
        }
    )
    pagina = cliente.baixar("https://www.gov.br/a")
    assert not pagina.ok
    assert pagina.motivo == "proibida pelo robots.txt"
    assert "https://fechado.gov.br/x" not in sessao.chamadas
    assert cliente.interrompido_por is None


def test_redirecionamentos_demais_param_em_vez_de_girar_para_sempre() -> None:
    respostas: dict[str, RespostaFalsa | Exception] = {
        "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
        "https://www.gov.br/a": desvio("https://www.gov.br/b"),
        "https://www.gov.br/b": desvio("https://www.gov.br/a"),
    }
    cliente, sessao, _ = criar(respostas)
    pagina = cliente.baixar("https://www.gov.br/a")
    assert not pagina.ok
    assert pagina.motivo == "redirecionamentos demais"
    assert len(sessao.chamadas) <= 8
    assert cliente.interrompido_por is None


def test_redirecionamento_sem_destino_falha_so_aquela_pagina() -> None:
    cliente, _, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": RespostaFalsa(status_code=301, text=""),
        }
    )
    pagina = cliente.baixar("https://www.gov.br/a")
    assert not pagina.ok
    assert pagina.motivo == "HTTP 301"


def test_pausa_depois_de_cada_passo_do_redirecionamento() -> None:
    cliente, sessao, pausas = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": desvio("https://www.gov.br/b"),
            "https://www.gov.br/b": RespostaFalsa(),
        },
        pausa=2.0,
    )
    cliente.baixar("https://www.gov.br/a")
    assert len(pausas) == len(sessao.chamadas) == 3


def test_bloqueio_no_meio_do_caminho_interrompe_tudo() -> None:
    cliente, _, _ = criar(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "https://www.gov.br/a": desvio("https://www.gov.br/b"),
            "https://www.gov.br/b": RespostaFalsa(status_code=429, text="muitas requisições"),
        }
    )
    pagina = cliente.baixar("https://www.gov.br/a")
    assert pagina.motivo == "bloqueado (HTTP 429)"
    assert cliente.interrompido_por == "bloqueado (HTTP 429)"


def test_o_robots_txt_tambem_pode_redirecionar() -> None:
    cliente, _, _ = criar(
        {
            "http://velho.gov.br/robots.txt": desvio("https://velho.gov.br/robots.txt"),
            "https://velho.gov.br/robots.txt": RespostaFalsa(text=ROBOTS_LIBERADO),
            "http://velho.gov.br/a": RespostaFalsa(),
        }
    )
    assert cliente.baixar("http://velho.gov.br/a").ok
