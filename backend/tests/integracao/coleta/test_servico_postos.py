"""Serviço de coleta de postos: tabela de repartições, subpáginas de contato e gravação.

Os testes usam páginas reais salvas do gov.br (`tests/fixtures/govbr/`) e um gov.br falso: nenhuma
requisição sai pela rede. A coleta é de melhor esforço, então o que não existe fica nulo.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from farol.coleta import ServicoDeColetaDePostos
from farol.dominio import ExecucaoColeta, Posto, Territorio, TipoExecucao, TipoPosto, TipoTerritorio
from farol.infra import ClienteEducado, Pagina

if TYPE_CHECKING:
    from tests.conftest import GovBrFalso, RelogioFalso

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "govbr"
URL_DA_TABELA = "https://www.gov.br/mre/reparticoes"

PRETORIA = "https://www.gov.br/mre/pt-br/embaixada-pretoria"
MILAO = "https://www.gov.br/mre/pt-br/consulado-milao"
AMA = "https://www.gov.br/mre/pt-br/embaixada-ama"
LINK_PRETORIA = "http://pretoria.itamaraty.gov.br/pt-br/"
LINK_MILAO = "http://milao.itamaraty.gov.br/pt-br/"
LINK_AMA = "http://ama.itamaraty.gov.br/pt-br/"
LINK_CARTUM = "http://cartum.itamaraty.gov.br/pt-br/"

ID_PRETORIA, ID_MILAO, ID_AMA, ID_CARTUM = 31, 182, 130, 33


def ler(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


def pagina(url: str, html: str, final: str | None = None) -> Pagina:
    return Pagina(url, 200, html, None, url_final=final)


def novo_posto(posto_id: int, codigo: str, cidade: str, tipo: TipoPosto) -> Posto:
    return Posto(
        id=posto_id,
        territorio_codigo=codigo,
        cidade=cidade,
        tipo=tipo,
        latitude=Decimal("1.00000"),
        longitude=Decimal("1.00000"),
    )


def montar_banco(sessao: Session) -> None:
    """Quatro países e quatro postos, que aparecem na tabela real de repartições."""
    sessao.add_all(
        [
            Territorio(codigo="ZA", nome_pt="África do Sul", tipo=TipoTerritorio.PAIS),
            Territorio(codigo="IT", nome_pt="Itália", tipo=TipoTerritorio.PAIS),
            Territorio(codigo="JO", nome_pt="Jordânia", tipo=TipoTerritorio.PAIS),
            Territorio(codigo="SD", nome_pt="Sudão", tipo=TipoTerritorio.PAIS),
        ]
    )
    sessao.flush()
    sessao.add_all(
        [
            novo_posto(ID_PRETORIA, "ZA", "Pretória", TipoPosto.EMBAIXADA),
            novo_posto(ID_MILAO, "IT", "Milão", TipoPosto.CONSULADO_GERAL),
            novo_posto(ID_AMA, "JO", "Amã", TipoPosto.EMBAIXADA),
            novo_posto(ID_CARTUM, "SD", "Cartum", TipoPosto.EMBAIXADA),
        ]
    )
    sessao.flush()


def publicar_tabela_e_postos(govbr: "GovBrFalso") -> None:
    """A tabela real e as páginas reais dos postos, com os redirecionamentos do gov.br."""
    p = govbr.paginas
    p[URL_DA_TABELA] = pagina(URL_DA_TABELA, ler("reparticoes.html"))
    p[LINK_PRETORIA] = pagina(LINK_PRETORIA, ler("pretoria_inicio.html"), PRETORIA)
    p[f"{PRETORIA}/fale-conosco-1"] = pagina(
        f"{PRETORIA}/fale-conosco-1", ler("pretoria_fale_conosco.html")
    )
    p[f"{PRETORIA}/assistencia-a-brasileiros"] = pagina(
        f"{PRETORIA}/assistencia-a-brasileiros",
        "<html><body><p>Sem contato aqui.</p></body></html>",
    )
    p[LINK_MILAO] = pagina(LINK_MILAO, ler("posto_2.html"), MILAO)
    p[f"{MILAO}/emergencias"] = pagina(f"{MILAO}/emergencias", ler("milao_emergencias.html"))
    p[f"{MILAO}/fale-conosco-1"] = pagina(f"{MILAO}/fale-conosco-1", ler("milao_fale_conosco.html"))
    p[LINK_AMA] = pagina(LINK_AMA, ler("posto_1.html"), AMA)
    p[LINK_CARTUM] = pagina(
        LINK_CARTUM, ler("posto_1.html"), "https://www.gov.br/mre/pt-br/embaixada-cartum"
    )


def servico(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> ServicoDeColetaDePostos:
    return ServicoDeColetaDePostos(sessao, govbr, relogio, url_da_tabela=URL_DA_TABELA)


def posto(sessao: Session, posto_id: int) -> Posto:
    return sessao.scalars(select(Posto).where(Posto.id == posto_id)).one()


def execucoes(sessao: Session) -> list[ExecucaoColeta]:
    return list(sessao.scalars(select(ExecucaoColeta).order_by(ExecucaoColeta.id)))


@pytest.fixture
def cenario(sessao: Session, govbr: "GovBrFalso") -> "GovBrFalso":
    montar_banco(sessao)
    publicar_tabela_e_postos(govbr)
    return govbr


# --------------------------------------------------------------------------- coleta completa
def test_segue_os_links_do_posto_e_registra_a_pagina_final_do_gov_br(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    servico(sessao, cenario, relogio).coletar()

    # os links da tabela estão em itamaraty.gov.br e redirecionam para www.gov.br
    assert posto(sessao, ID_PRETORIA).url_gov_br == PRETORIA
    assert posto(sessao, ID_MILAO).url_gov_br == MILAO
    assert posto(sessao, ID_AMA).url_gov_br == AMA
    assert posto(sessao, ID_CARTUM).url_gov_br == "https://www.gov.br/mre/pt-br/embaixada-cartum"


def test_grava_endereco_telefone_data_e_fonte_juntos(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    servico(sessao, cenario, relogio).coletar()

    pretoria = posto(sessao, ID_PRETORIA)
    assert pretoria.endereco is not None
    assert pretoria.endereco.startswith("152 Dallas Avenue")
    assert pretoria.telefone_plantao is None  # a página não traz telefone de plantão
    assert pretoria.contato_coletado_em == relogio.agora()
    assert pretoria.contato_fonte_url == f"{PRETORIA}/fale-conosco-1"

    milao = posto(sessao, ID_MILAO)
    assert milao.telefone_plantao == "+39 335 727 8117"
    assert milao.endereco is None  # nenhuma página do consulado traz o endereço de rua
    assert milao.contato_coletado_em == relogio.agora()
    assert milao.contato_fonte_url == f"{MILAO}/emergencias"


def test_campos_nao_encontrados_ficam_nulos_e_sem_data_nem_fonte(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    servico(sessao, cenario, relogio).coletar()
    for posto_id in (ID_AMA, ID_CARTUM):
        sem_contato = posto(sessao, posto_id)
        assert sem_contato.endereco is None
        assert sem_contato.telefone_plantao is None
        assert sem_contato.contato_coletado_em is None
        assert sem_contato.contato_fonte_url is None


def test_relatorio_de_cobertura_na_execucao(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    resultado = servico(sessao, cenario, relogio).coletar()

    [execucao] = execucoes(sessao)
    assert execucao.tipo is TipoExecucao.POSTOS
    assert execucao.completa is True
    assert execucao.motivo_interrupcao is None
    assert execucao.finalizada_em is not None
    assert execucao.paginas_esperadas == 4  # os quatro postos da tabela que existem no banco
    assert execucao.paginas_lidas == 4
    assert execucao.postos_com_endereco == 1
    assert execucao.postos_com_telefone == 1
    assert resultado.execucao_id == execucao.id
    assert resultado.completa
    assert (resultado.postos_com_endereco, resultado.postos_com_telefone) == (1, 1)


def test_so_baixa_as_paginas_dos_postos_que_existem_no_banco(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    servico(sessao, cenario, relogio).coletar()
    iniciais = {p for p in cenario.pedidos if p.endswith("itamaraty.gov.br/pt-br/")}
    assert iniciais == {LINK_PRETORIA, LINK_MILAO, LINK_AMA, LINK_CARTUM}


def test_visita_poucas_subpaginas_e_para_quando_ja_achou_tudo(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    servico(sessao, cenario, relogio).coletar()
    assert not [p for p in cenario.pedidos if "quem-somos" in p or "horarios" in p]
    assert cenario.pedidos.count(f"{MILAO}/emergencias") == 1
    assert len(cenario.pedidos) <= 1 + 4 + 2 * 3  # tabela, quatro postos, até três subpáginas


def test_o_endereco_e_o_telefone_de_paginas_diferentes_citam_a_pagina_inicial_como_fonte(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    sessao.add(Territorio(codigo="PE", nome_pt="Peru", tipo=TipoTerritorio.PAIS))
    sessao.flush()
    sessao.add(novo_posto(1, "PE", "Lima", TipoPosto.EMBAIXADA))
    sessao.flush()
    base = "https://www.gov.br/mre/pt-br/embaixada-lima"
    govbr.paginas[URL_DA_TABELA] = pagina(
        URL_DA_TABELA,
        "<table><tr><td>Onde</td><td>Onde obter</td></tr><tr>"
        '<td><a href="/pais/peru">Peru</a></td>'
        '<td><a href="http://lima.itamaraty.gov.br/pt-br/">Lima</a></td></tr></table>',
    )
    govbr.paginas["http://lima.itamaraty.gov.br/pt-br/"] = pagina(
        "http://lima.itamaraty.gov.br/pt-br/",
        f'<a href="{base}/emergencias">Emergências</a>'
        f'<a href="{base}/fale-conosco">Fale Conosco</a>',
        base,
    )
    govbr.paginas[f"{base}/emergencias"] = pagina(
        f"{base}/emergencias",
        '<div id="content-core"><p>Plantão Consular: +51 999 888 777</p></div>',
    )
    govbr.paginas[f"{base}/fale-conosco"] = pagina(
        f"{base}/fale-conosco",
        '<div id="content-core"><pre>Endereço</pre><p>Av. do Sol, 10<br/>Lima</p></div>',
    )

    servico(sessao, govbr, relogio).coletar()

    lima = posto(sessao, 1)
    assert lima.telefone_plantao == "+51 999 888 777"
    assert lima.endereco == "Av. do Sol, 10, Lima"
    assert lima.contato_fonte_url == base  # as duas informações vieram de páginas diferentes


# --------------------------------------------------------------------------- uma página por link
def test_link_repetido_na_tabela_e_baixado_uma_vez(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    sessao.add_all(
        [
            Territorio(codigo="BE", nome_pt="Bélgica", tipo=TipoTerritorio.PAIS),
            Territorio(codigo="LU", nome_pt="Luxemburgo", tipo=TipoTerritorio.PAIS),
        ]
    )
    sessao.flush()
    sessao.add_all(
        [
            novo_posto(19, "BE", "Bruxelas", TipoPosto.EMBAIXADA),
            novo_posto(20, "BE", "Bruxelas", TipoPosto.CONSULADO_GERAL),
        ]
    )
    sessao.flush()
    link = "http://cgbruxelas.itamaraty.gov.br/pt-br/"
    linha = (
        '<tr><td><a href="/pais/{0}">{1}</a></td><td><a href="' + link + '">Bruxelas</a></td></tr>'
    )
    govbr.paginas[URL_DA_TABELA] = pagina(
        URL_DA_TABELA,
        "<table><tr><td>Onde</td><td>Onde obter</td></tr>"
        + linha.format("belgica", "Bélgica")
        + linha.format("luxemburgo", "Luxemburgo")
        + "</table>",
    )
    govbr.paginas[link] = pagina(link, "<html></html>", "https://www.gov.br/mre/pt-br/cg-bruxelas")

    servico(sessao, govbr, relogio).coletar()

    assert govbr.pedidos.count(link) == 1
    assert posto(sessao, 20).url_gov_br == "https://www.gov.br/mre/pt-br/cg-bruxelas"  # o consulado
    assert posto(sessao, 19).url_gov_br is None  # a embaixada não tem link na tabela


# --------------------------------------------------------------------------- nova coleta
def test_nova_coleta_sem_achar_nada_nao_apaga_o_contato_que_ja_existe(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    servico(sessao, cenario, relogio).coletar()
    antes = posto(sessao, ID_MILAO).telefone_plantao
    primeira_data = relogio.agora()
    assert antes is not None

    relogio.avancar(days=30)
    cenario.paginas[f"{MILAO}/emergencias"] = pagina(
        f"{MILAO}/emergencias", "<html><body>Página reformada, sem contato.</body></html>"
    )
    servico(sessao, cenario, relogio).coletar()

    milao = posto(sessao, ID_MILAO)
    assert milao.telefone_plantao == antes
    assert milao.contato_coletado_em == primeira_data  # a data continua sendo a de quando foi lido


def test_nova_coleta_substitui_o_contato_inteiro_com_a_nova_data_e_fonte(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    servico(sessao, cenario, relogio).coletar()

    relogio.avancar(days=30)
    cenario.paginas[f"{MILAO}/emergencias"] = pagina(
        f"{MILAO}/emergencias",
        '<div id="content-core"><p>Plantão Consular: +39 111 222 3333</p></div>',
    )
    servico(sessao, cenario, relogio).coletar()

    milao = posto(sessao, ID_MILAO)
    assert milao.telefone_plantao == "+39 111 222 3333"
    assert milao.contato_coletado_em == relogio.agora()
    assert len(execucoes(sessao)) == 2


def test_achou_so_o_telefone_agora_o_endereco_antigo_nao_fica_com_a_data_nova(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    """Endereço, telefone, data e fonte andam juntos: o que não foi lido agora volta nulo."""
    servico(sessao, cenario, relogio).coletar()
    pretoria = posto(sessao, ID_PRETORIA)
    assert pretoria.endereco is not None

    relogio.avancar(days=30)
    cenario.paginas[f"{PRETORIA}/fale-conosco-1"] = pagina(
        f"{PRETORIA}/fale-conosco-1", "<html><body>sem endereço</body></html>"
    )
    cenario.paginas[f"{PRETORIA}/assistencia-a-brasileiros"] = pagina(
        f"{PRETORIA}/assistencia-a-brasileiros",
        '<div id="content-core"><p>Telefone do plantão: +27 82 555 1234</p></div>',
    )
    servico(sessao, cenario, relogio).coletar()

    pretoria = posto(sessao, ID_PRETORIA)
    assert pretoria.endereco is None
    assert pretoria.telefone_plantao == "+27 82 555 1234"
    assert pretoria.contato_coletado_em == relogio.agora()
    assert pretoria.contato_fonte_url == f"{PRETORIA}/assistencia-a-brasileiros"


# --------------------------------------------------------------------------- falhas
def test_pagina_de_um_posto_que_falha_nao_derruba_os_outros(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    cenario.falhar(LINK_PRETORIA, "HTTP 500")
    resultado = servico(sessao, cenario, relogio).coletar()

    assert posto(sessao, ID_MILAO).telefone_plantao == "+39 335 727 8117"
    assert posto(sessao, ID_PRETORIA).endereco is None
    assert posto(sessao, ID_PRETORIA).url_gov_br is None
    assert resultado.paginas_esperadas == 4
    assert resultado.paginas_lidas == 3
    assert resultado.completa  # 3 de 4 = 75%


def test_menos_de_70_por_cento_das_paginas_lidas_e_coleta_incompleta(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    cenario.falhar(LINK_PRETORIA, "HTTP 500")
    cenario.falhar(LINK_AMA, "HTTP 500")
    resultado = servico(sessao, cenario, relogio).coletar()

    assert not resultado.completa
    assert resultado.paginas_lidas == 2
    assert resultado.motivo_interrupcao == "só 2 de 4 páginas lidas (mínimo de 70%)"
    assert posto(sessao, ID_MILAO).telefone_plantao == "+39 335 727 8117"  # o que leu fica gravado


def test_bloqueio_interrompe_a_coleta_e_grava_o_motivo(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    cenario.falhar(LINK_MILAO, "bloqueado (HTTP 429)")
    resultado = servico(sessao, cenario, relogio).coletar()

    assert not resultado.completa
    assert resultado.motivo_interrupcao == "bloqueado (HTTP 429)"
    [execucao] = execucoes(sessao)
    assert execucao.completa is False
    assert execucao.motivo_interrupcao == "bloqueado (HTTP 429)"
    assert execucao.finalizada_em is not None
    # nunca insiste: nenhuma página pedida depois do bloqueio
    depois = cenario.pedidos[cenario.pedidos.index(LINK_MILAO) + 1 :]
    assert depois == []


def test_verificacao_humana_interrompe_e_o_que_ja_foi_lido_fica(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    cenario.falhar(f"{PRETORIA}/fale-conosco-1", "caiu na verificação humana")
    resultado = servico(sessao, cenario, relogio).coletar()

    assert not resultado.completa
    assert resultado.motivo_interrupcao == "caiu na verificação humana"
    assert posto(sessao, ID_PRETORIA).url_gov_br == PRETORIA
    assert posto(sessao, ID_PRETORIA).endereco is None


def test_tabela_que_nao_carrega_deixa_a_coleta_incompleta_e_nao_toca_nos_postos(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    cenario.falhar(URL_DA_TABELA, "HTTP 503")
    resultado = servico(sessao, cenario, relogio).coletar()

    assert not resultado.completa
    assert resultado.motivo_interrupcao == "não leu a tabela de repartições (HTTP 503)"
    assert resultado.paginas_esperadas == 0
    assert posto(sessao, ID_MILAO).url_gov_br is None
    assert cenario.pedidos == [URL_DA_TABELA]


def test_tabela_em_formato_inesperado_nao_e_coleta_completa(
    sessao: Session, cenario: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    cenario.paginas[URL_DA_TABELA] = pagina(URL_DA_TABELA, "<html><body>outra coisa</body></html>")
    resultado = servico(sessao, cenario, relogio).coletar()

    assert not resultado.completa
    assert resultado.motivo_interrupcao == "tabela de repartições em formato inesperado"


def test_tabela_sem_nenhum_posto_conhecido_nao_e_coleta_completa(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    # banco sem postos (seed ainda não rodou): nada a coletar, e isso não é sucesso
    govbr.paginas[URL_DA_TABELA] = pagina(URL_DA_TABELA, ler("reparticoes.html"))
    resultado = servico(sessao, govbr, relogio).coletar()
    assert not resultado.completa
    assert resultado.motivo_interrupcao == "nenhum posto do banco aparece na tabela de repartições"


# --------------------------------------------------------------------------- robots.txt por host
@dataclass
class RespostaFalsa:
    status_code: int = 200
    text: str = ""
    encoding: str | None = "utf-8"
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class SessaoFalsa:
    respostas: dict[str, RespostaFalsa | Exception]
    headers: dict[str, str] = field(default_factory=dict)
    chamadas: list[str] = field(default_factory=list)

    def get(self, url: str, *, timeout: float, allow_redirects: bool = True) -> RespostaFalsa:
        self.chamadas.append(url)
        resposta = self.respostas.get(url, RespostaFalsa(status_code=404))
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def test_robots_txt_e_consultado_por_host_e_respeitado_nas_subpaginas(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    montar_banco(sessao)
    livre = "User-agent: *\nDisallow:\n"
    sem_emergencias = "User-agent: *\nDisallow: /mre/pt-br/consulado-milao/emergencias\n"
    sessao_http = SessaoFalsa(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=sem_emergencias),
            "https://www.gov.br/mre/reparticoes": RespostaFalsa(text=ler("reparticoes.html")),
            "http://milao.itamaraty.gov.br/robots.txt": RespostaFalsa(text=livre),
            "http://milao.itamaraty.gov.br/pt-br/": RespostaFalsa(
                status_code=301, headers={"Location": MILAO}
            ),
            MILAO: RespostaFalsa(text=ler("posto_2.html")),
            f"{MILAO}/fale-conosco-1": RespostaFalsa(text=ler("milao_fale_conosco.html")),
            f"{MILAO}/emergencias": RespostaFalsa(text=ler("milao_emergencias.html")),
        }
    )
    cliente = ClienteEducado(
        "https://github.com/exemplo", sessao=sessao_http, dormir=lambda _: None
    )

    ServicoDeColetaDePostos(sessao, cliente, relogio, url_da_tabela=URL_DA_TABELA).coletar()

    robots = [c for c in sessao_http.chamadas if c.endswith("/robots.txt")]
    # um por host, uma vez só (os outros postos do banco têm cada um o seu host)
    assert sorted(set(robots)) == sorted(robots)
    assert "http://milao.itamaraty.gov.br/robots.txt" in robots
    assert robots.count("https://www.gov.br/robots.txt") == 1
    assert f"{MILAO}/emergencias" not in sessao_http.chamadas  # proibida pelo robots.txt do host
    assert f"{MILAO}/fale-conosco-1" in sessao_http.chamadas
    assert posto(sessao, ID_MILAO).url_gov_br == MILAO
    assert posto(sessao, ID_MILAO).telefone_plantao is None  # a única página com o número é vetada


def test_erro_de_conexao_na_pagina_de_um_posto_nao_derruba_a_coleta(
    sessao: Session, relogio: "RelogioFalso"
) -> None:
    montar_banco(sessao)
    livre = "User-agent: *\nDisallow:\n"
    sessao_http = SessaoFalsa(
        {
            "https://www.gov.br/robots.txt": RespostaFalsa(text=livre),
            "https://www.gov.br/mre/reparticoes": RespostaFalsa(text=ler("reparticoes.html")),
            "http://milao.itamaraty.gov.br/robots.txt": RespostaFalsa(text=livre),
            "http://milao.itamaraty.gov.br/pt-br/": requests.Timeout("lento"),
        }
    )
    cliente = ClienteEducado(
        "https://github.com/exemplo", sessao=sessao_http, dormir=lambda _: None
    )

    resultado = ServicoDeColetaDePostos(
        sessao, cliente, relogio, url_da_tabela=URL_DA_TABELA
    ).coletar()

    assert resultado.paginas_lidas == 0
    assert not resultado.completa
    assert cliente.interrompido_por is None
