"""`RecuperadorDeTrechos`: os melhores trechos de uma pergunta, filtrados por país e por vigor."""

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy.orm import Session
from tests.falsos_chat import (
    AGORA,
    EmbeddadorFalso,
    RelogioFixo,
    carregar_alertas,
    execucao_completa,
    gravar_alerta,
    ler_alertas_json,
    semear_territorios,
    vigor_do_arquivo,
)

from farol.chat import RecuperadorDeTrechos, indexar_pendentes
from farol.dominio import Alerta
from farol.mapa import ProcuradorDeTerritorios, alertas_que_definem_nivel

if TYPE_CHECKING:
    from tests.conftest import ContadorDeConsultas

TEXTOS = {a["id"]: a["texto"] for a in ler_alertas_json()}


@pytest.fixture
def ids(sessao: Session) -> dict[str, int]:
    return carregar_alertas(sessao)


@pytest.fixture
def embeddador() -> EmbeddadorFalso:
    return EmbeddadorFalso()


@pytest.fixture
def indexado(sessao: Session, ids: dict[str, int], embeddador: EmbeddadorFalso) -> Session:
    indexar_pendentes(
        sessao,
        embeddador,
        vigor_do_arquivo(ids),
        modelo=embeddador.modelo,
        dimensoes=embeddador.dimensoes,
        citados=ProcuradorDeTerritorios(sessao).codigos_citados,
        relogio=RelogioFixo(),
    )
    return sessao


def _recuperador(
    sessao: Session, embeddador: EmbeddadorFalso, **opcoes: Any
) -> RecuperadorDeTrechos:
    return RecuperadorDeTrechos(
        sessao, embeddador, modelo=embeddador.modelo, dimensoes=embeddador.dimensoes, **opcoes
    )


def _fatia(sessao: Session, alerta_id: int, inicio: int, fim: int) -> str:
    alerta = sessao.get(Alerta, alerta_id)
    assert alerta is not None and alerta.texto is not None
    return alerta.texto[inicio:fim]


def test_devolve_os_quatro_melhores_e_o_trecho_certo_vem_primeiro(
    indexado: Session, embeddador: EmbeddadorFalso, ids: dict[str, int]
) -> None:
    achados = _recuperador(indexado, embeddador).recuperar(
        "Quais são os telefones dos plantões consulares das embaixadas em Teerã e Tel Aviv?"
    )

    assert len(achados) == 4
    primeiro = achados[0]
    assert primeiro.alerta_id == ids["A-02"]
    texto = _fatia(indexado, primeiro.alerta_id, primeiro.inicio, primeiro.fim)
    assert "Embaixada em Teerã" in texto
    distancias = [a.distancia for a in achados if a.distancia is not None]
    assert len(distancias) == 4 and distancias == sorted(distancias)


def test_filtra_pelo_pais(
    indexado: Session, embeddador: EmbeddadorFalso, ids: dict[str, int]
) -> None:
    """Só os alertas que citam o Líbano (o A-02 e o A-05), mesmo que outro case melhor."""
    achados = _recuperador(indexado, embeddador).recuperar(
        "Situação de segurança na Ucrânia e orientações aos brasileiros", paises=["LB"]
    )

    assert achados
    assert {a.alerta_id for a in achados} <= {ids["A-02"], ids["A-05"]}


def test_sem_pais_busca_em_todos_os_alertas(
    indexado: Session, embeddador: EmbeddadorFalso, ids: dict[str, int]
) -> None:
    achados = _recuperador(indexado, embeddador).recuperar(
        "ataques frequentes na Ucrânia e abrigos designados pelas autoridades locais"
    )

    ucrania = {ids["A-09"], ids["A-10"], ids["A-17"]}
    assert {a.alerta_id for a in achados} & ucrania


def test_inclui_o_alerta_que_rege_o_nivel_quando_ha_similaridade_minima(
    sessao: Session, embeddador: EmbeddadorFalso
) -> None:
    """A pergunta casa com o alerta anterior, mas o que rege o nível da Bolívia é o novo."""
    semear_territorios(sessao)
    execucao = execucao_completa(sessao)
    paragrafo_1 = " ".join(f"bloqueio{n} protesto{n} estrada{n} greve{n}" for n in range(30)) + "."
    paragrafo_2 = " ".join(f"caminhoneiros{n} pedagio{n} combustivel{n}" for n in range(30)) + "."
    anterior = gravar_alerta(
        sessao,
        execucao,
        url="https://x/anterior",
        titulo="Bolívia, bloqueios",
        texto=f"{paragrafo_1} {paragrafo_2}",
        html_corpo=f"<div><p>{paragrafo_1}</p><p>{paragrafo_2}</p></div>",
        publicado_em=AGORA - timedelta(days=9),
        niveis=[{"territorio": "BO", "nivel_pais": "evitar", "regioes": []}],
    )
    vigente = gravar_alerta(
        sessao,
        execucao,
        url="https://x/vigente",
        titulo="Bolívia, normalizada",
        texto="A circulação nas rodovias foi restabelecida: bloqueio0 protesto3 estrada5 greve7.",
        publicado_em=AGORA,
        niveis=[{"territorio": "BO", "nivel_pais": "normalizada", "regioes": []}],
    )
    indexar_pendentes(
        sessao,
        embeddador,
        alertas_que_definem_nivel(sessao),
        modelo=embeddador.modelo,
        dimensoes=embeddador.dimensoes,
        relogio=RelogioFixo(),
    )
    pergunta = paragrafo_1

    sem_vigor = _recuperador(sessao, embeddador, limite=2, distancia_maxima_do_vigor=0.0)
    com_vigor = _recuperador(sessao, embeddador, limite=2, distancia_maxima_do_vigor=1.0)
    so_o_anterior = sem_vigor.recuperar(pergunta, paises=["BO"], so_em_vigor=False)
    com_o_que_rege = com_vigor.recuperar(pergunta, paises=["BO"], so_em_vigor=False)
    por_padrao = sem_vigor.recuperar(pergunta, paises=["BO"])

    assert {a.alerta_id for a in so_o_anterior} == {anterior.id}
    assert not any(a.em_vigor for a in so_o_anterior)
    assert len(com_o_que_rege) == 2  # o limite continua valendo
    assert {a.alerta_id: a.em_vigor for a in com_o_que_rege} == {
        anterior.id: False,
        vigente.id: True,
    }
    assert com_o_que_rege[0].alerta_id == anterior.id  # o mais parecido segue primeiro
    assert {a.alerta_id for a in por_padrao} == {vigente.id}  # por padrão, só o que vale


PERGUNTA_IRA = "o que o Itamaraty recomenda para quem está no Irã? crise no Oriente Médio"


@pytest.mark.parametrize("falhar_na_pergunta", [False, True], ids=["vetorial", "textual"])
@pytest.mark.parametrize("paises", [["IR"], None], ids=["com-pais", "sem-pais"])
def test_alerta_anterior_nao_ocupa_vaga_numa_pergunta_normal(
    indexado: Session,
    embeddador: EmbeddadorFalso,
    ids: dict[str, int],
    falhar_na_pergunta: bool,
    paises: list[str] | None,
) -> None:
    """O A-05 ("Crise no Oriente Médio") cita o Irã, mas não rege o nível de ninguém."""
    embeddador.falhar_na_pergunta = falhar_na_pergunta

    achados = _recuperador(indexado, embeddador).recuperar(PERGUNTA_IRA, paises)

    assert achados
    assert ids["A-05"] not in {a.alerta_id for a in achados}
    assert all(a.em_vigor for a in achados)
    anteriores = _recuperador(indexado, embeddador).recuperar(
        PERGUNTA_IRA, paises, so_em_vigor=False
    )
    assert ids["A-05"] in {a.alerta_id for a in anteriores}  # os anteriores só a pedido


AVISOS_GERAIS = {a["id"] for a in ler_alertas_json() if not a["niveis"]}


def test_com_pais_entram_os_que_o_regem_e_os_avisos_gerais_que_o_citam(
    indexado: Session, embeddador: EmbeddadorFalso, ids: dict[str, int]
) -> None:
    vigor = vigor_do_arquivo(ids)
    gerais = {ids[g] for g in AVISOS_GERAIS}
    for falhar in (False, True):
        embeddador.falhar_na_pergunta = falhar
        achados = _recuperador(indexado, embeddador).recuperar(PERGUNTA_IRA, ["IR"])
        assert achados
        for a in achados:
            rege_o_ira = "IR" in vigor.get(a.alerta_id, ())
            assert rege_o_ira or (a.alerta_id in gerais and a.aviso_geral)


@pytest.mark.parametrize("falhar_na_pergunta", [False, True], ids=["vetorial", "textual"])
@pytest.mark.parametrize(
    ("pergunta", "paises", "esperados"),
    [
        ("aliciamento nas Filipinas", ["PH"], {"A-14"}),
        ("aliciamento nas Filipinas", None, {"A-14"}),
        ("golpe em nome do consulado nos EUA", ["US"], {"A-03", "A-06"}),
        ("golpe em nome do consulado nos EUA", None, {"A-03", "A-06"}),
    ],
)
def test_aviso_geral_e_encontrado(
    indexado: Session,
    embeddador: EmbeddadorFalso,
    ids: dict[str, int],
    falhar_na_pergunta: bool,
    pergunta: str,
    paises: list[str] | None,
    esperados: set[str],
) -> None:
    """Aviso geral (fraude, aliciamento) não define nível, mas está em vigor e entra na busca."""
    embeddador.falhar_na_pergunta = falhar_na_pergunta

    achados = _recuperador(indexado, embeddador).recuperar(pergunta, paises)

    encontrados = {a.alerta_id for a in achados}
    assert encontrados & {ids[e] for e in esperados}
    assert all(a.em_vigor for a in achados)


def test_aviso_geral_nao_entra_em_pergunta_de_pais_que_ele_nao_cita(
    indexado: Session, embeddador: EmbeddadorFalso, ids: dict[str, int]
) -> None:
    achados = _recuperador(indexado, embeddador).recuperar("aliciamento nas Filipinas", ["IR"])

    assert ids["A-14"] not in {a.alerta_id for a in achados}


def test_busca_por_texto_ignora_acentos(
    indexado: Session, embeddador: EmbeddadorFalso, ids: dict[str, int]
) -> None:
    embeddador.falhar_na_pergunta = True

    sem_acento = _recuperador(indexado, embeddador).recuperar("cisjordania", paises=["PS"])
    com_acento = _recuperador(indexado, embeddador).recuperar("Cisjordânia", paises=["PS"])

    assert sem_acento and [a.alerta_id for a in sem_acento] == [a.alerta_id for a in com_acento]
    assert any("Cisjordânia" in _fatia(indexado, a.alerta_id, a.inicio, a.fim) for a in sem_acento)


def test_cai_na_busca_por_texto_quando_o_embedding_da_pergunta_falha(
    indexado: Session, embeddador: EmbeddadorFalso, ids: dict[str, int]
) -> None:
    embeddador.falhar_na_pergunta = True

    achados = _recuperador(indexado, embeddador).recuperar(
        "evitar viagens não essenciais Cisjordânia", paises=["PS"]
    )

    assert achados
    assert ids["A-02"] in {a.alerta_id for a in achados}
    assert all(a.origem == "textual" for a in achados)
    assert any("Cisjordânia" in _fatia(indexado, a.alerta_id, a.inicio, a.fim) for a in achados)


def test_alerta_sem_vetor_do_modelo_configurado_entra_pela_busca_por_texto(
    indexado: Session, embeddador: EmbeddadorFalso, ids: dict[str, int]
) -> None:
    """Troca de modelo no meio do caminho: o índice só tem o modelo antigo."""
    novo = EmbeddadorFalso(dimensoes=32, modelo="falso:v2")

    achados = _recuperador(indexado, novo).recuperar("Filipinas aliciamento contratos de trabalho")

    assert achados
    assert all(a.origem == "textual" for a in achados)
    assert ids["A-14"] in {a.alerta_id for a in achados}


def test_pergunta_sem_nada_parecido_nao_inventa_trechos_por_texto(
    indexado: Session, embeddador: EmbeddadorFalso
) -> None:
    embeddador.falhar_na_pergunta = True
    assert _recuperador(indexado, embeddador).recuperar("zzzxxyy qqwweerr") == []


def test_numero_fixo_de_consultas_por_pergunta(
    indexado: Session, embeddador: EmbeddadorFalso, contar_consultas: "ContadorDeConsultas"
) -> None:
    recuperador = _recuperador(indexado, embeddador)
    with contar_consultas as c:
        recuperador.recuperar("O que o alerta diz sobre o Líbano?", paises=["LB"])
    assert c.total <= 4
    with contar_consultas as c:
        recuperador.recuperar("Orientações para trabalho na Índia")
    assert c.total <= 4
