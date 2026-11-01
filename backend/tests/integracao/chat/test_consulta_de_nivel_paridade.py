"""`ConsultaDeNivel` e `ResolvedorDePaises` (de `farol.api.chat`) dizem o mesmo que o painel.

As consultas do chat não reescrevem regra: chamam `montar_painel` e só convertem. Aqui o painel é o
`GET /api/v1/paises/{codigo}`, e o chat tem de devolver o mesmo para países de cada situação.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session
from tests.falsos_chat import carregar_alertas, semear_territorios

from farol.api.app import criar_app, sessao_da_requisicao
from farol.api.chat import ConsultaDeNivelDoSite, ResolvedorDePaisesDoSite
from farol.chat.protocolos import ConsultaDeNivel, ResolvedorDePaises
from farol.infra import Configuracoes


@pytest.fixture
def cliente(sessao: Session) -> Iterator[TestClient]:
    app = criar_app(
        Configuracoes(
            database_url=SecretStr("postgresql+psycopg://x:y@nao-existe/z"),
            cache_ttl_segundos=0,
            limite_pedidos_por_minuto=0,
        )
    )
    app.dependency_overrides[sessao_da_requisicao] = lambda: sessao
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------------------------ nível
@pytest.mark.parametrize(
    "codigo",
    [
        "IR",  # com alerta (não viajar)
        "LB",  # nível por região
        "PS",  # as regiões cobrem o país
        "BO",  # alerta normalizado: sem alerta
        "UA",  # evitar
        "BR",  # o Brasil
        "GL",  # dependência: vale o alerta do soberano, se houver
        "NZ",  # sem nenhum alerta
    ],
)
def test_nivel_igual_ao_do_painel(sessao: Session, cliente: TestClient, codigo: str) -> None:
    carregar_alertas(sessao)
    consulta = ConsultaDeNivelDoSite(sessao)
    assert isinstance(consulta, ConsultaDeNivel)

    pais = cliente.get(f"/api/v1/paises/{codigo}").json()
    consultado = consulta.consultar(codigo)

    assert consultado.codigo == pais["codigo"] and consultado.nome == pais["nome"]
    assert consultado.nivel == pais["nivel"]
    assert list(consultado.regioes) == [r["nome"] for r in pais["regioes"]]
    assert consultado.so_regional == pais["regiao_unica_do_alerta"]
    assert consultado.observacao == pais["observacao"]
    assert consultado.dados_obtidos is True
    regente = [a for a in pais["alertas"] if a["define_nivel"]]
    if regente:
        assert consultado.alerta_que_rege is not None
        assert consultado.alerta_que_rege.url == regente[0]["url"]
        assert consultado.alerta_que_rege.titulo == regente[0]["titulo"]
        assert consultado.alerta_que_rege.id > 0
    else:
        assert consultado.alerta_que_rege is None


def test_o_alerta_que_rege_o_ira_e_o_mais_recente_do_oriente_medio(sessao: Session) -> None:
    ids = carregar_alertas(sessao)
    consultado = ConsultaDeNivelDoSite(sessao).consultar("IR")
    assert consultado.nivel == "nao_viajar"
    assert consultado.alerta_que_rege is not None
    assert consultado.alerta_que_rege.id == ids["A-02"]  # e não o "Crise no Oriente Médio"


def test_sem_coleta_o_nivel_e_nao_verificado_e_avisa_que_nao_ha_dados(sessao: Session) -> None:
    semear_territorios(sessao)
    consultado = ConsultaDeNivelDoSite(sessao).consultar("IR")
    assert consultado.nivel == "nao_verificado"
    assert consultado.dados_obtidos is False
    assert consultado.atualizado_em is None


def test_territorio_desconhecido_levanta_erro_do_mapa(sessao: Session) -> None:
    from farol.mapa import TerritorioNaoEncontrado

    semear_territorios(sessao)
    with pytest.raises(TerritorioNaoEncontrado):
        ConsultaDeNivelDoSite(sessao).consultar("ZZ")


# ------------------------------------------------------------------------------ países
@pytest.fixture
def resolvedor(sessao: Session) -> ResolvedorDePaisesDoSite:
    semear_territorios(sessao)
    resolvedor = ResolvedorDePaisesDoSite(sessao)
    assert isinstance(resolvedor, ResolvedorDePaises)
    return resolvedor


def _codigos(resolvedor: ResolvedorDePaisesDoSite, texto: str) -> list[str]:
    return sorted(p.codigo for p in resolvedor.resolver(texto).encontrados)


def test_acha_o_pais_sem_acento_e_sem_diferenca_de_maiuscula(
    resolvedor: ResolvedorDePaisesDoSite,
) -> None:
    for texto in ("O que o Itamaraty recomenda para o Irã?", "IRÃ", "viagem ao ira agora"):
        assert _codigos(resolvedor, texto) == ["IR"]


def test_palavra_inteira_nao_confunde_nomes_parecidos(
    resolvedor: ResolvedorDePaisesDoSite,
) -> None:
    assert _codigos(resolvedor, "O Iraque e a Irlanda") == ["IE", "IQ"]
    assert "IR" not in _codigos(resolvedor, "Iraque")


def test_dois_paises_na_mesma_pergunta(resolvedor: ResolvedorDePaisesDoSite) -> None:
    assert _codigos(resolvedor, "Líbano e Palestina") == ["LB", "PS"]


def test_dependencia_traz_o_soberano_no_valor_devolvido(
    resolvedor: ResolvedorDePaisesDoSite,
) -> None:
    [groenlandia] = resolvedor.resolver("Groenlândia").encontrados
    assert (groenlandia.codigo, groenlandia.soberano) == ("GL", "DK")


def test_nome_mais_longo_vence_o_mais_curto(resolvedor: ResolvedorDePaisesDoSite) -> None:
    assert _codigos(resolvedor, "Papua Nova Guiné") == ["PG"]
    assert _codigos(resolvedor, "Guiné-Bissau") == ["GW"]
    assert _codigos(resolvedor, "Guiné Equatorial") == ["GQ"]


@pytest.mark.parametrize(
    ("texto", "candidatos"),
    [
        ("Como está o Congo?", {"CD", "CG"}),
        ("Visto para a Guiné", {"GN", "GQ", "GW"}),
        ("E a Coreia?", {"KP", "KR"}),
        ("Vou às Ilhas Virgens", {"VG", "VI"}),
    ],
)
def test_nome_ambiguo_devolve_os_candidatos(
    resolvedor: ResolvedorDePaisesDoSite, texto: str, candidatos: set[str]
) -> None:
    resultado = resolvedor.resolver(texto)
    assert resultado.encontrados == ()
    assert {c.codigo for grupo in resultado.ambiguos for c in grupo} == candidatos


def test_nome_ambiguo_nunca_vira_um_pais_mesmo_se_for_termo_de_busca(sessao: Session) -> None:
    from sqlalchemy import update

    from farol.dominio import Territorio

    semear_territorios(sessao)
    sessao.execute(
        update(Territorio).where(Territorio.codigo == "CG").values(termos_busca=["Congo"])
    )
    resultado = ResolvedorDePaisesDoSite(sessao).resolver("Irã e Congo")
    assert [p.codigo for p in resultado.encontrados] == ["IR"]
    assert {c.codigo for grupo in resultado.ambiguos for c in grupo} == {"CD", "CG"}


def test_texto_sem_pais(resolvedor: ResolvedorDePaisesDoSite) -> None:
    resultado = resolvedor.resolver("Posso levar remédios na bagagem?")
    assert resultado.encontrados == () and resultado.ambiguos == ()


def test_area_neutra_nao_e_pais(sessao: Session) -> None:
    from sqlalchemy import select

    from farol.dominio import Territorio, TipoTerritorio

    semear_territorios(sessao)
    neutras = list(
        sessao.scalars(select(Territorio).where(Territorio.tipo == TipoTerritorio.NEUTRO))
    )
    resolvedor = ResolvedorDePaisesDoSite(sessao)
    for area in neutras:
        assert area.codigo not in _codigos(resolvedor, area.nome_pt)


def test_uma_consulta_so_ao_banco(sessao: Session, contar_consultas) -> None:  # type: ignore[no-untyped-def]
    semear_territorios(sessao)
    with contar_consultas as c:
        resolvedor = ResolvedorDePaisesDoSite(sessao)
        resolvedor.resolver("Irã")
        resolvedor.resolver("Líbano")
    assert c.total == 1
