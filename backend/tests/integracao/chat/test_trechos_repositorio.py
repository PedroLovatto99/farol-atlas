"""`TrechoAlertaRepositorio`: gravar trechos e recuperar por similaridade e por texto.

A consulta só compara vetores do modelo e da dimensão configurados, só devolve trechos de conteúdo
em vigor (o `JOIN` com o alerta) e filtra por país e por vigor.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.falsos_chat import AGORA, execucao_completa, gravar_alerta, semear_territorios

from farol.dominio import Alerta, NovoTrecho, TrechoAlertaRepositorio

if TYPE_CHECKING:
    from tests.conftest import ContadorDeConsultas

A = "teste:modelo-a"
B = "teste:modelo-b"
TEXTO = (
    "A situação em Israel exige atenção redobrada dos viajantes. "  # 0..59
    "Evite multidões e protestos durante a permanência no país. "
    "Procure a embaixada em caso de emergência consular."
)


def _alerta(sessao: Session, n: int = 1, *, texto: str = TEXTO, **extra: Any) -> Alerta:
    semear_territorios(sessao)
    return gravar_alerta(
        sessao,
        execucao_completa(sessao),
        url=f"https://www.gov.br/mre/a{n}",
        titulo=f"Alerta {n}",
        texto=texto,
        **extra,
    )


def _gravar(
    sessao: Session,
    alerta: Alerta,
    vetores: list[list[float]],
    *,
    modelo: str = A,
    paises: list[str] | None = None,
    em_vigor_para: list[str] | None = None,
) -> None:
    classificacao_id = _classificacao(sessao, alerta)
    fatias = [(0, 60), (60, 119), (119, len(alerta.texto or ""))]
    TrechoAlertaRepositorio(sessao).substituir_trechos(
        alerta.id,
        alerta.confirmado_hash or "",
        [
            NovoTrecho(posicao=i, inicio=fatias[i][0], fim=fatias[i][1], embedding=v)
            for i, v in enumerate(vetores)
        ],
        modelo=modelo,
        dimensoes=len(vetores[0]),
        classificacao_id=classificacao_id,
        paises=paises or ["IL"],
        em_vigor_para=em_vigor_para or [],
        agora=AGORA,
    )


def _classificacao(sessao: Session, alerta: Alerta) -> int:
    sessao.refresh(alerta)
    return alerta.classificacoes[0].id


def _repo(sessao: Session) -> TrechoAlertaRepositorio:
    return TrechoAlertaRepositorio(sessao)


def test_devolve_os_mais_proximos_primeiro_e_respeita_o_limite(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.7, 0.7, 0.0]])

    achados = _repo(sessao).recuperar_por_similaridade(
        [1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=2
    )

    assert [a.posicao for a in achados] == [0, 2]
    assert achados[0].distancia == pytest.approx(0.0, abs=1e-6)
    assert 0.0 < achados[1].distancia < 1.0
    assert (achados[0].inicio, achados[0].fim) == (0, 60)


def test_so_compara_o_modelo_e_a_dimensao_configurados(sessao: Session) -> None:
    """Dois modelos, dimensões 3 e 4, no mesmo banco: nenhum erro de comparação."""
    alerta = _alerta(sessao)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0]], modelo=A)
    _gravar(sessao, alerta, [[0.0, 0.0, 0.0, 1.0]], modelo=B)

    com_a = _repo(sessao).recuperar_por_similaridade(
        [1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5
    )
    com_b = _repo(sessao).recuperar_por_similaridade(
        [0.0, 0.0, 0.0, 1.0], modelo=B, dimensoes=4, limite=5
    )
    outra_dimensao = _repo(sessao).recuperar_por_similaridade(
        [1.0, 0.0], modelo=A, dimensoes=2, limite=5
    )

    assert len(com_a) == 1 and com_a[0].distancia == pytest.approx(0.0, abs=1e-6)
    assert len(com_b) == 1 and com_b[0].distancia == pytest.approx(0.0, abs=1e-6)
    assert outra_dimensao == []


def test_o_vetor_da_pergunta_precisa_ter_a_dimensao_configurada(sessao: Session) -> None:
    with pytest.raises(ValueError, match="dimens"):
        _repo(sessao).recuperar_por_similaridade([1.0, 0.0], modelo=A, dimensoes=3, limite=1)


def test_alerta_removido_nao_e_devolvido(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0]])
    alerta.removido_em = datetime(2026, 11, 1, tzinfo=UTC)
    sessao.flush()

    assert (
        _repo(sessao).recuperar_por_similaridade([1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5)
        == []
    )


def test_conteudo_antigo_nao_e_devolvido_mesmo_antes_da_passada(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0]])
    alerta.confirmado_hash = "b" * 64  # o conteúdo confirmado mudou; o varredor ainda não rodou
    sessao.flush()

    assert (
        _repo(sessao).recuperar_por_similaridade([1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5)
        == []
    )
    assert _repo(sessao).recuperar_por_texto("Israel", modelo=A, dimensoes=3, limite=5) == []


def test_alerta_sem_confirmacao_nao_e_devolvido(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0]])
    alerta.confirmado_execucao_id = None
    sessao.flush()

    assert (
        _repo(sessao).recuperar_por_similaridade([1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5)
        == []
    )


def test_filtra_por_pais(sessao: Session) -> None:
    israel = _alerta(sessao, 1)
    bolivia = gravar_alerta(
        sessao,
        execucao_completa(sessao),
        url="https://www.gov.br/mre/bo",
        titulo="Bolívia",
        texto=TEXTO,
    )
    _gravar(sessao, israel, [[1.0, 0.0, 0.0]], paises=["IL", "JO"])
    _gravar(sessao, bolivia, [[1.0, 0.0, 0.0]], paises=["BO"])
    repo = _repo(sessao)

    so_il = repo.recuperar_por_similaridade(
        [1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5, paises=["IL"]
    )
    jo_ou_bo = repo.recuperar_por_similaridade(
        [1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5, paises=["JO", "BO"]
    )
    todos = repo.recuperar_por_similaridade([1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5)

    assert {t.alerta_id for t in so_il} == {israel.id}
    assert {t.alerta_id for t in jo_ou_bo} == {israel.id, bolivia.id}
    assert {t.alerta_id for t in todos} == {israel.id, bolivia.id}


def test_filtra_por_vigor_e_marca_o_trecho_em_vigor(sessao: Session) -> None:
    novo = _alerta(sessao, 1)
    anterior = gravar_alerta(
        sessao,
        execucao_completa(sessao),
        url="https://www.gov.br/mre/velho",
        titulo="Velho",
        texto=TEXTO,
    )
    _gravar(sessao, novo, [[1.0, 0.0, 0.0]], paises=["IL"], em_vigor_para=["IL"])
    _gravar(sessao, anterior, [[1.0, 0.0, 0.0]], paises=["IL"], em_vigor_para=[])
    repo = _repo(sessao)

    todos = repo.recuperar_por_similaridade(
        [1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5, paises=["IL"]
    )
    em_vigor = repo.recuperar_por_similaridade(
        [1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5, paises=["IL"], so_em_vigor=True
    )

    assert {t.alerta_id: t.em_vigor for t in todos} == {novo.id: True, anterior.id: False}
    assert [t.alerta_id for t in em_vigor] == [novo.id]


def test_vigor_de_outro_pais_nao_conta(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0]], paises=["IL", "JO"], em_vigor_para=["JO"])

    achados = _repo(sessao).recuperar_por_similaridade(
        [1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=5, paises=["IL"], so_em_vigor=True
    )

    assert achados == []


def test_busca_por_texto_ordena_por_ts_rank_e_usa_so_a_fatia_do_trecho(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    repo = _repo(sessao)

    achados = repo.recuperar_por_texto("embaixada emergência", modelo=A, dimensoes=3, limite=5)
    sem_ocorrencia = repo.recuperar_por_texto("Bolívia", modelo=A, dimensoes=3, limite=5)
    # "multidões" só aparece na segunda fatia, "Israel" só na primeira
    segunda = repo.recuperar_por_texto("multidões", modelo=A, dimensoes=3, limite=5)
    primeira = repo.recuperar_por_texto("Israel", modelo=A, dimensoes=3, limite=5)

    assert [a.posicao for a in achados] == [2]
    assert sem_ocorrencia == []
    assert [a.posicao for a in segunda] == [1]
    assert [a.posicao for a in primeira] == [0]
    assert achados[0].pontuacao > 0


def test_alerta_sem_vetor_do_modelo_configurado_entra_pela_busca_por_texto(
    sessao: Session,
) -> None:
    """No meio de uma troca de modelo: o alerta só tem vetores do modelo antigo (outra dimensão)."""
    com_vetor = _alerta(sessao, 1)
    sem_vetor = gravar_alerta(
        sessao, execucao_completa(sessao), url="https://www.gov.br/mre/x", titulo="X", texto=TEXTO
    )
    _gravar(sessao, com_vetor, [[1.0, 0.0, 0.0]], modelo=B)
    _gravar(sessao, sem_vetor, [[1.0, 0.0, 0.0, 0.0]], modelo=A)
    repo = _repo(sessao)

    # configurado: modelo B, dimensão 3 → o alerta `sem_vetor` não tem vetor desse modelo
    assert repo.alertas_sem_vetor(B, 3) == [sem_vetor.id]
    achados = repo.recuperar_por_texto("Israel", modelo=B, dimensoes=3, limite=5)
    assert {a.alerta_id for a in achados} == {com_vetor.id, sem_vetor.id}
    so_os_sem_vetor = repo.recuperar_por_texto(
        "Israel", modelo=B, dimensoes=3, limite=5, so_alertas_sem_vetor=True
    )
    assert {a.alerta_id for a in so_os_sem_vetor} == {sem_vetor.id}
    # e nunca duplica o mesmo trecho quando dois modelos coexistem para o mesmo alerta
    assert len({(a.alerta_id, a.inicio, a.fim) for a in achados}) == len(achados)


def test_numero_fixo_de_consultas_por_busca(
    sessao: Session, contar_consultas: "ContadorDeConsultas"
) -> None:
    alertas = [_alerta(sessao, 1)]
    for n in range(2, 8):
        alertas.append(
            gravar_alerta(
                sessao,
                execucao_completa(sessao),
                url=f"https://www.gov.br/mre/a{n}",
                titulo=f"Alerta {n}",
                texto=TEXTO,
            )
        )
    for alerta in alertas:
        _gravar(sessao, alerta, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    repo = _repo(sessao)

    with contar_consultas as c:
        repo.recuperar_por_similaridade([1.0, 0.0, 0.0], modelo=A, dimensoes=3, limite=4)
    assert c.total == 1
    with contar_consultas as c:
        repo.recuperar_por_texto("Israel", modelo=A, dimensoes=3, limite=4)
    assert c.total == 1


def test_substituir_troca_os_trechos_do_alerta_e_devolve_o_que_gravou(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    _gravar(sessao, alerta, [[0.0, 1.0, 0.0]], paises=["JO"])  # troca: agora só um trecho

    gravados = _repo(sessao).trechos_gravados(A, 3)[alerta.id]

    assert [(t.posicao, t.paises) for t in gravados] == [(0, ("JO",))]
    n = sessao.execute(text("select count(*) from trecho_alerta")).scalar_one()
    assert n == 1


def test_apagar_de_outros_modelos_preserva_o_configurado(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0]], modelo=A)
    _gravar(sessao, alerta, [[1.0, 0.0, 0.0, 0.0]], modelo=B)
    repo = _repo(sessao)

    apagados = repo.apagar_de_outros_modelos(alerta.id, A, 3)

    assert apagados == 1
    assert [(m, d) for m, d, *_ in repo.resumo_do_indice()] == [(A, 3)]
