"""Indexador: mantém o índice de trechos em dia com os alertas (idempotente, sem custo à toa)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.falsos_chat import (
    AGORA,
    EmbeddadorFalso,
    RelogioFixo,
    carregar_alertas,
    hash_do_texto,
    ler_alertas_json,
    vigor_do_arquivo,
)

from farol.chat import (
    ResumoDaIndexacao,
    ResumoDaReindexacao,
    consultar_situacao,
    indexar_pendentes,
    reindexar,
)
from farol.dominio import Alerta, Classificacao, TrechoAlertaRepositorio

TOTAL_DE_ALERTAS = len(ler_alertas_json())


@pytest.fixture
def ids(sessao: Session) -> dict[str, int]:
    return carregar_alertas(sessao)


def _indexar(
    sessao: Session,
    embeddador: EmbeddadorFalso,
    vigor: dict[int, frozenset[str]] | None = None,
    *,
    tudo: bool = False,
) -> ResumoDaIndexacao:
    return indexar_pendentes(
        sessao,
        embeddador,
        vigor or {},
        modelo=embeddador.modelo,
        dimensoes=embeddador.dimensoes,
        tudo=tudo,
        relogio=RelogioFixo(),
    )


def _reindexar(
    sessao: Session,
    embeddador: EmbeddadorFalso,
    vigor: dict[int, frozenset[str]] | None = None,
    *,
    manter_antigos: bool = False,
) -> ResumoDaReindexacao:
    return reindexar(
        sessao,
        embeddador,
        vigor or {},
        modelo=embeddador.modelo,
        dimensoes=embeddador.dimensoes,
        manter_antigos=manter_antigos,
        relogio=RelogioFixo(),
    )


def _contar(sessao: Session, onde: str = "true") -> int:
    return int(
        sessao.execute(text(f"select count(*) from trecho_alerta where {onde}")).scalar_one()
    )


# ------------------------------------------------------------------------------ primeira passada
def test_primeira_passada_indexa_todos_os_alertas_elegiveis(
    sessao: Session, ids: dict[str, int]
) -> None:
    embeddador = EmbeddadorFalso()

    resumo = _indexar(sessao, embeddador, vigor_do_arquivo(ids))

    assert resumo.novos == TOTAL_DE_ALERTAS
    assert resumo.atualizados == resumo.inalterados == resumo.apagados == resumo.falhas == 0
    assert resumo.trechos == _contar(sessao) == embeddador.textos_vetorizados
    assert _contar(sessao) > TOTAL_DE_ALERTAS  # alertas longos viram mais de um trecho


def test_o_trecho_gravado_e_a_fatia_do_texto_do_alerta(
    sessao: Session, ids: dict[str, int]
) -> None:
    embeddador = EmbeddadorFalso()
    _indexar(sessao, embeddador, vigor_do_arquivo(ids))

    gravados = TrechoAlertaRepositorio(sessao).trechos_gravados(
        embeddador.modelo, embeddador.dimensoes
    )
    texto_de = {a.id: a.texto or "" for a in sessao.query(Alerta)}
    vetorizados = {t for lote in embeddador.lotes_de_documentos for t in lote}

    for alerta_id, trechos in gravados.items():
        for trecho in trechos:
            assert texto_de[alerta_id][trecho.inicio : trecho.fim] in vetorizados


def test_grava_paises_da_classificacao_e_o_vigor_recebido(
    sessao: Session, ids: dict[str, int]
) -> None:
    embeddador = EmbeddadorFalso()
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, embeddador, vigor)

    gravados = TrechoAlertaRepositorio(sessao).trechos_gravados(
        embeddador.modelo, embeddador.dimensoes
    )
    oriente = gravados[ids["A-02"]]
    fraude = gravados[ids["A-03"]]  # alerta que não é de viagem: sem países

    assert {t.paises for t in oriente} == {
        ("AE", "BH", "IL", "IQ", "IR", "JO", "KW", "LB", "PS", "QA", "SA", "SY", "YE")
    }
    assert {t.em_vigor_para for t in oriente} == {tuple(sorted(vigor[ids["A-02"]]))}
    assert {t.paises for t in fraude} == {()}
    assert {t.em_vigor_para for t in fraude} == {()}
    anterior = gravados[ids["A-05"]]  # "Crise no Oriente Médio", superado pelo A-02
    assert {t.em_vigor_para for t in anterior} == {()}


# ------------------------------------------------------------------------------ idempotência
def test_segunda_passada_nao_vetoriza_nada(sessao: Session, ids: dict[str, int]) -> None:
    embeddador = EmbeddadorFalso()
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, embeddador, vigor)
    lotes = len(embeddador.lotes_de_documentos)
    antes = _contar(sessao)

    resumo = _indexar(sessao, embeddador, vigor)

    assert len(embeddador.lotes_de_documentos) == lotes
    assert resumo.inalterados == TOTAL_DE_ALERTAS
    assert resumo.novos == resumo.atualizados == resumo.metadados == resumo.trechos == 0
    assert _contar(sessao) == antes


def test_passada_sem_mudancas_nao_conta_como_escrita(sessao: Session, ids: dict[str, int]) -> None:
    """Escrever sobe a versão dos dados e esvazia o cache do site: a cada 5 minutos, nem pensar."""
    embeddador = EmbeddadorFalso()
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, embeddador, vigor)
    sessao.info.pop("escreveu", None)

    _indexar(sessao, embeddador, vigor)

    assert "escreveu" not in sessao.info


def test_passada_que_indexa_conta_como_escrita(sessao: Session, ids: dict[str, int]) -> None:
    sessao.info.pop("escreveu", None)
    _indexar(sessao, EmbeddadorFalso(), vigor_do_arquivo(ids))
    assert sessao.info.get("escreveu") is True


def test_so_o_alerta_de_hash_mudado_e_refeito(sessao: Session, ids: dict[str, int]) -> None:
    embeddador = EmbeddadorFalso()
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, embeddador, vigor)
    lotes = len(embeddador.lotes_de_documentos)

    alerta = sessao.get(Alerta, ids["A-09"])
    assert alerta is not None
    alerta.texto = "A situação de segurança na Ucrânia mudou. Siga as orientações da embaixada."
    alerta.html_corpo = f"<div><p>{alerta.texto}</p></div>"
    alerta.hash = alerta.confirmado_hash = hash_do_texto(alerta.texto)
    sessao.add(
        Classificacao(
            alerta_id=alerta.id,
            alerta_hash=alerta.hash,
            status=alerta.classificacoes[0].status,
            e_alerta_de_viagem=True,
            modelo="falso",
            classificado_em=AGORA,
        )
    )
    sessao.flush()

    resumo = _indexar(sessao, embeddador, vigor)

    assert resumo.atualizados == 1
    assert resumo.inalterados == TOTAL_DE_ALERTAS - 1
    assert len(embeddador.lotes_de_documentos) == lotes + 1
    assert embeddador.lotes_de_documentos[-1] == [alerta.texto]
    # o trecho do conteúdo antigo não ficou para trás
    assert _contar(sessao, f"alerta_id = {alerta.id} and alerta_hash <> '{alerta.hash}'") == 0


def test_vigor_mudou_atualiza_sem_vetorizar(sessao: Session, ids: dict[str, int]) -> None:
    embeddador = EmbeddadorFalso()
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, embeddador, vigor)
    lotes = len(embeddador.lotes_de_documentos)

    # o A-05 passa a reger o nível de Israel (por exemplo, o A-02 foi removido da lista)
    novo_vigor = {**vigor, ids["A-05"]: frozenset({"IL"})}
    resumo = _indexar(sessao, embeddador, novo_vigor)

    assert len(embeddador.lotes_de_documentos) == lotes
    assert resumo.metadados == 1
    assert resumo.inalterados == TOTAL_DE_ALERTAS - 1
    gravados = TrechoAlertaRepositorio(sessao).trechos_gravados(
        embeddador.modelo, embeddador.dimensoes
    )
    assert {t.em_vigor_para for t in gravados[ids["A-05"]]} == {("IL",)}


def test_classificacao_refeita_com_o_mesmo_hash_atualiza_paises_sem_vetorizar(
    sessao: Session, ids: dict[str, int]
) -> None:
    """É o que `reclassificar` faz: mesma linha, `classificado_em` novo, outros países."""
    embeddador = EmbeddadorFalso()
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, embeddador, vigor)
    lotes = len(embeddador.lotes_de_documentos)
    classificacao = sessao.get(Alerta, ids["A-01"]).classificacoes[0]  # type: ignore[union-attr]
    classificacao.classificado_em = AGORA + timedelta(minutes=1)
    classificacao.niveis[0].territorio_codigo = "PE"  # antes BO
    sessao.flush()

    resumo = _indexar(sessao, embeddador, vigor)

    assert len(embeddador.lotes_de_documentos) == lotes
    assert resumo.metadados == 1
    gravados = TrechoAlertaRepositorio(sessao).trechos_gravados(
        embeddador.modelo, embeddador.dimensoes
    )
    assert {t.paises for t in gravados[ids["A-01"]]} == {("PE",)}
    assert TrechoAlertaRepositorio(sessao).alertas_a_indexar(embeddador.modelo, 256) == []


def test_tudo_refaz_todos_os_trechos(sessao: Session, ids: dict[str, int]) -> None:
    embeddador = EmbeddadorFalso()
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, embeddador, vigor)
    antes = _contar(sessao)
    vetorizados = embeddador.textos_vetorizados

    resumo = _indexar(sessao, embeddador, vigor, tudo=True)

    assert resumo.atualizados == TOTAL_DE_ALERTAS and resumo.novos == 0
    assert embeddador.textos_vetorizados == 2 * vetorizados
    assert _contar(sessao) == antes


# ------------------------------------------------------------------------------ saída da lista
def test_alerta_removido_tem_os_trechos_apagados_e_some_da_consulta_antes_da_passada(
    sessao: Session, ids: dict[str, int]
) -> None:
    embeddador = EmbeddadorFalso()
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, embeddador, vigor)
    repo = TrechoAlertaRepositorio(sessao)
    pergunta = embeddador.vetorizar_pergunta("Israel Irã Líbano Palestina nível de alerta")
    alvo = ids["A-02"]
    assert alvo in {
        t.alerta_id
        for t in repo.recuperar_por_similaridade(
            pergunta, modelo=embeddador.modelo, dimensoes=embeddador.dimensoes, limite=30
        )
    }

    sessao.get(Alerta, alvo).removido_em = datetime(2026, 11, 1, tzinfo=UTC)  # type: ignore[union-attr]
    sessao.flush()
    # antes da passada: as linhas ainda existem, mas a consulta já não devolve o alerta
    assert _contar(sessao, f"alerta_id = {alvo}") > 0
    achados = repo.recuperar_por_similaridade(
        pergunta, modelo=embeddador.modelo, dimensoes=embeddador.dimensoes, limite=30
    )
    assert alvo not in {t.alerta_id for t in achados}

    resumo = _indexar(sessao, embeddador, vigor)

    assert resumo.apagados == 1
    assert _contar(sessao, f"alerta_id = {alvo}") == 0
    assert resumo.inalterados == TOTAL_DE_ALERTAS - 1


def test_alerta_sem_classificacao_valida_perde_os_trechos(
    sessao: Session, ids: dict[str, int]
) -> None:
    embeddador = EmbeddadorFalso()
    _indexar(sessao, embeddador, vigor_do_arquivo(ids))
    alerta = sessao.get(Alerta, ids["A-12"])
    assert alerta is not None
    alerta.confirmado_hash = "c" * 64  # o conteúdo novo ainda não foi classificado
    sessao.flush()

    resumo = _indexar(sessao, embeddador, vigor_do_arquivo(ids))

    assert resumo.apagados == 1
    assert _contar(sessao, f"alerta_id = {alerta.id}") == 0


# ------------------------------------------------------------------------------ falhas
def test_falha_num_alerta_nao_derruba_os_outros(sessao: Session, ids: dict[str, int]) -> None:
    embeddador = EmbeddadorFalso()
    embeddador.falhar_quando = lambda texto: "Bolívia" in texto

    resumo = _indexar(sessao, embeddador, vigor_do_arquivo(ids))

    assert resumo.falhas == 1  # só o A-01 fala da Bolívia
    assert resumo.novos == TOTAL_DE_ALERTAS - 1
    assert _contar(sessao, f"alerta_id = {ids['A-01']}") == 0

    embeddador.falhar_quando = None  # o ciclo seguinte tenta de novo
    resumo = _indexar(sessao, embeddador, vigor_do_arquivo(ids))
    assert resumo.novos == 1 and resumo.falhas == 0
    assert _contar(sessao, f"alerta_id = {ids['A-01']}") > 0


def test_falha_ao_refazer_nao_apaga_os_trechos_bons(sessao: Session, ids: dict[str, int]) -> None:
    embeddador = EmbeddadorFalso()
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, embeddador, vigor)
    antes = _contar(sessao, f"alerta_id = {ids['A-02']}")
    embeddador.falhar_quando = lambda texto: "Oriente Médio" in texto

    resumo = _indexar(sessao, embeddador, vigor, tudo=True)

    assert resumo.falhas >= 1
    assert _contar(sessao, f"alerta_id = {ids['A-02']}") == antes  # os antigos continuam


def test_resposta_com_numero_de_vetores_errado_conta_como_falha(
    sessao: Session, ids: dict[str, int]
) -> None:
    class Torto(EmbeddadorFalso):
        def vetorizar_documentos(self, textos):  # type: ignore[no-untyped-def]
            return super().vetorizar_documentos(textos)[:-1]

    resumo = _indexar(sessao, Torto(), vigor_do_arquivo(ids))

    assert resumo.falhas == TOTAL_DE_ALERTAS and _contar(sessao) == 0


def test_resposta_com_dimensao_errada_conta_como_falha(
    sessao: Session, ids: dict[str, int]
) -> None:
    class DimensaoErrada(EmbeddadorFalso):
        def vetorizar_documentos(self, textos):  # type: ignore[no-untyped-def]
            return [v[:-1] for v in super().vetorizar_documentos(textos)]

    resumo = _indexar(sessao, DimensaoErrada(), vigor_do_arquivo(ids))

    assert resumo.falhas == TOTAL_DE_ALERTAS and _contar(sessao) == 0


# ------------------------------------------------------------------------------ troca de modelo
def test_passada_com_outro_modelo_grava_ao_lado_do_antigo(
    sessao: Session, ids: dict[str, int]
) -> None:
    antigo = EmbeddadorFalso(dimensoes=16, modelo="falso:v1")
    novo = EmbeddadorFalso(dimensoes=32, modelo="falso:v2")
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, antigo, vigor)
    trechos_antigos = _contar(sessao)

    resumo = _indexar(sessao, novo, vigor)

    assert resumo.novos == TOTAL_DE_ALERTAS  # para o modelo novo, nenhum alerta estava indexado
    assert _contar(sessao, "modelo_embedding = 'falso:v1'") == trechos_antigos  # nada apagado
    assert _contar(sessao, "modelo_embedding = 'falso:v2'") == resumo.trechos


def test_reindexar_so_apaga_os_antigos_de_um_alerta_depois_de_ele_ficar_completo(
    sessao: Session, ids: dict[str, int]
) -> None:
    antigo = EmbeddadorFalso(dimensoes=16, modelo="falso:v1")
    novo = EmbeddadorFalso(dimensoes=32, modelo="falso:v2")
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, antigo, vigor)
    antigos_do_a01 = _contar(sessao, f"alerta_id = {ids['A-01']}")
    trechos_antigos = _contar(sessao)
    novo.falhar_quando = lambda texto: "Bolívia" in texto  # o A-01 vai falhar

    resumo = _reindexar(sessao, novo, vigor)

    assert resumo.falhas == 1
    assert resumo.refeitos == TOTAL_DE_ALERTAS - 1
    # o alerta que falhou conserva os vetores antigos; os outros só têm os novos
    assert _contar(sessao, f"alerta_id = {ids['A-01']} and modelo_embedding = 'falso:v1'") > 0
    assert _contar(sessao, f"alerta_id = {ids['A-01']} and modelo_embedding = 'falso:v2'") == 0
    assert _contar(sessao, f"alerta_id = {ids['A-02']} and modelo_embedding = 'falso:v1'") == 0
    assert _contar(sessao, f"alerta_id = {ids['A-02']} and modelo_embedding = 'falso:v2'") > 0
    assert resumo.vetores_antigos_apagados == trechos_antigos - antigos_do_a01


def test_reindexar_completo_apaga_todos_os_antigos_e_e_idempotente(
    sessao: Session, ids: dict[str, int]
) -> None:
    antigo = EmbeddadorFalso(dimensoes=16, modelo="falso:v1")
    novo = EmbeddadorFalso(dimensoes=32, modelo="falso:v2")
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, antigo, vigor)
    trechos_antigos = _contar(sessao)

    resumo = _reindexar(sessao, novo, vigor)

    assert resumo.falhas == 0 and resumo.refeitos == TOTAL_DE_ALERTAS
    assert resumo.vetores_antigos_apagados == trechos_antigos
    assert _contar(sessao, "modelo_embedding = 'falso:v1'") == 0
    assert resumo.trechos_novos == _contar(sessao)

    lotes = len(novo.lotes_de_documentos)
    de_novo = _reindexar(sessao, novo, vigor)
    assert len(novo.lotes_de_documentos) == lotes
    assert de_novo.refeitos == de_novo.vetores_antigos_apagados == de_novo.trechos_novos == 0


def test_reindexar_conta_o_andamento_alerta_por_alerta(
    sessao: Session, ids: dict[str, int]
) -> None:
    antigo = EmbeddadorFalso(dimensoes=16, modelo="falso:v1")
    novo = EmbeddadorFalso(dimensoes=32, modelo="falso:v2")
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, antigo, vigor)
    novo.falhar_quando = lambda texto: "Bolívia" in texto
    passos: list[tuple[int, int, int, str]] = []

    reindexar(
        sessao,
        novo,
        vigor,
        modelo=novo.modelo,
        dimensoes=novo.dimensoes,
        relogio=RelogioFixo(),
        andamento=lambda *passo: passos.append(passo),
    )

    assert [p[0] for p in passos] == list(range(1, TOTAL_DE_ALERTAS + 1))
    assert {p[1] for p in passos} == {TOTAL_DE_ALERTAS}
    assert {p[2]: p[3] for p in passos}[ids["A-01"]] == "falhou"
    assert [p[3] for p in passos].count("refeito") == TOTAL_DE_ALERTAS - 1


def test_reindexar_manter_antigos_nao_apaga_nada(sessao: Session, ids: dict[str, int]) -> None:
    antigo = EmbeddadorFalso(dimensoes=16, modelo="falso:v1")
    novo = EmbeddadorFalso(dimensoes=32, modelo="falso:v2")
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, antigo, vigor)
    trechos_antigos = _contar(sessao)

    resumo = _reindexar(sessao, novo, vigor, manter_antigos=True)

    assert resumo.vetores_antigos_apagados == 0
    assert _contar(sessao, "modelo_embedding = 'falso:v1'") == trechos_antigos
    assert _contar(sessao, "modelo_embedding = 'falso:v2'") == resumo.trechos_novos
    segunda = _reindexar(sessao, novo, vigor, manter_antigos=True)
    assert segunda.refeitos == 0 and segunda.vetores_antigos_apagados == 0


def test_dois_modelos_de_dimensoes_diferentes_nao_atrapalham_a_busca(
    sessao: Session, ids: dict[str, int]
) -> None:
    antigo = EmbeddadorFalso(dimensoes=16, modelo="falso:v1")
    novo = EmbeddadorFalso(dimensoes=32, modelo="falso:v2")
    vigor = vigor_do_arquivo(ids)
    _indexar(sessao, antigo, vigor)
    _reindexar(sessao, novo, vigor, manter_antigos=True)
    repo = TrechoAlertaRepositorio(sessao)

    com_novo = repo.recuperar_por_similaridade(
        novo.vetorizar_pergunta("Israel"), modelo="falso:v2", dimensoes=32, limite=3
    )
    com_antigo = repo.recuperar_por_similaridade(
        antigo.vetorizar_pergunta("Israel"), modelo="falso:v1", dimensoes=16, limite=3
    )

    assert len(com_novo) == len(com_antigo) == 3


# ------------------------------------------------------------------------------ status
def test_situacao_em_dia_e_com_pendencia(sessao: Session, ids: dict[str, int]) -> None:
    embeddador = EmbeddadorFalso()
    situacao = consultar_situacao(sessao, modelo=embeddador.modelo, dimensoes=embeddador.dimensoes)
    assert situacao.elegiveis == TOTAL_DE_ALERTAS and situacao.indexados == 0
    assert not situacao.em_dia

    _indexar(sessao, embeddador, vigor_do_arquivo(ids))
    situacao = consultar_situacao(sessao, modelo=embeddador.modelo, dimensoes=embeddador.dimensoes)
    assert situacao.indexados == TOTAL_DE_ALERTAS and situacao.em_dia
    assert situacao.avisos == ()
    assert [(m.modelo, m.dimensoes) for m in situacao.modelos] == [(embeddador.modelo, 256)]


def test_situacao_avisa_quando_o_indice_e_de_outro_modelo_ou_dimensao(
    sessao: Session, ids: dict[str, int]
) -> None:
    _indexar(sessao, EmbeddadorFalso(dimensoes=16, modelo="falso:v1"), vigor_do_arquivo(ids))

    outro_modelo = consultar_situacao(sessao, modelo="falso:v2", dimensoes=16)
    outra_dimensao = consultar_situacao(sessao, modelo="falso:v1", dimensoes=32)

    for situacao in (outro_modelo, outra_dimensao):
        assert not situacao.em_dia and situacao.indexados == 0
        assert any("reindexar" in aviso for aviso in situacao.avisos)
    assert "falso:v1" in outro_modelo.avisos[0]
