"""Modelos e restrições do banco da feature de vistos (002, data-model.md)."""

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from farol.dominio.enums import (
    CategoriaDeVisto,
    EstadoDaRetencao,
    EstadoDoItem,
    MotivoOutraSituacao,
    ResultadoDaColetaDeVistos,
    TipoDeItemParaRevisao,
    TipoTerritorio,
)
from farol.dominio.modelos import (
    ColetaVistos,
    ItemParaRevisao,
    MudancaRetida,
    RequisitoVisto,
    Territorio,
)

AGORA = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
HASH = "a" * 64
OUTRO_HASH = "b" * 64


def coleta(**campos: Any) -> ColetaVistos:
    base: dict[str, Any] = {
        "iniciada_em": AGORA,
        "finalizada_em": AGORA,
        "resultado": ResultadoDaColetaDeVistos.VALIDA,
    }
    base.update(campos)
    return ColetaVistos(**base)


def preparar(sessao: Session) -> ColetaVistos:
    """Dois territórios e uma coleta válida, já gravados."""
    sessao.add_all(
        [
            Territorio(codigo="AR", nome_pt="Argentina", tipo=TipoTerritorio.PAIS),
            Territorio(codigo="US", nome_pt="Estados Unidos", tipo=TipoTerritorio.PAIS),
        ]
    )
    primeira = coleta()
    sessao.add(primeira)
    sessao.flush()
    return primeira


def requisito(coleta_id: int, **campos: Any) -> RequisitoVisto:
    base: dict[str, Any] = {
        "territorio_codigo": "AR",
        "categoria": CategoriaDeVisto.ISENTO,
        "rotulo_original": "Freedom of movement",
        "linhas_fonte": [],
        "hash_fonte": HASH,
        "lido_em": AGORA,
        "coleta_id": coleta_id,
    }
    base.update(campos)
    return RequisitoVisto(**base)


def retida(coleta_id: int, **campos: Any) -> MudancaRetida:
    base: dict[str, Any] = {
        "territorio_codigo": "AR",
        "coleta_id": coleta_id,
        "estado": EstadoDaRetencao.PENDENTE,
        "hash_fonte_lido": HASH,
        "candidato": {},
        "categoria_exibida": CategoriaDeVisto.VISTO_EXIGIDO,
        "categoria_lida": CategoriaDeVisto.ISENTO,
        "aceita_rg_exibido": False,
        "aceita_rg_lido": True,
        "criada_em": AGORA,
    }
    base.update(campos)
    return MudancaRetida(**base)


def item(**campos: Any) -> ItemParaRevisao:
    base: dict[str, Any] = {
        "tipo": TipoDeItemParaRevisao.NOME,
        "valor": "narnia",
        "contexto": [],
        "primeira_vez_em": AGORA,
        "ultima_vez_em": AGORA,
        "estado": EstadoDoItem.PENDENTE,
    }
    base.update(campos)
    return ItemParaRevisao(**base)


# --------------------------------------------------------------------------- coleta_vistos
def test_coleta_valida_nao_exige_motivo(sessao: Session) -> None:
    sessao.add(coleta(motivo=None))
    sessao.flush()


@pytest.mark.parametrize(
    "resultado",
    [
        ResultadoDaColetaDeVistos.REJEITADA,
        ResultadoDaColetaDeVistos.ADIADA,
        ResultadoDaColetaDeVistos.FALHOU,
        ResultadoDaColetaDeVistos.BLOQUEADA,
    ],
)
@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_coleta_que_nao_e_valida_exige_motivo(
    sessao: Session, resultado: ResultadoDaColetaDeVistos, motivo: str | None
) -> None:
    sessao.add(coleta(resultado=resultado, motivo=motivo))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_coleta_que_nao_e_valida_com_motivo_e_aceita(sessao: Session) -> None:
    sessao.add(coleta(resultado=ResultadoDaColetaDeVistos.ADIADA, motivo="editada há 3 horas"))
    sessao.flush()


def test_contadores_da_coleta_comecam_em_zero(sessao: Session) -> None:
    nova = coleta()
    sessao.add(nova)
    sessao.flush()
    sessao.refresh(nova)
    assert (nova.linhas_lidas, nova.adiamentos_seguidos, nova.falhas_seguidas) == (0, 0, 0)
    assert (nova.aplicadas, nova.retidas) == (0, 0)


# --------------------------------------------------------------------------- requisito_visto
def test_requisito_isento_e_aceito(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id))
    sessao.flush()


def test_outra_situacao_exige_motivo(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id, categoria=CategoriaDeVisto.OUTRA_SITUACAO))
    with pytest.raises(IntegrityError):
        sessao.flush()


@pytest.mark.parametrize("motivo", list(MotivoOutraSituacao))
def test_outra_situacao_com_motivo_e_aceita(sessao: Session, motivo: MotivoOutraSituacao) -> None:
    primeira = preparar(sessao)
    sessao.add(
        requisito(primeira.id, categoria=CategoriaDeVisto.OUTRA_SITUACAO, motivo_outra=motivo)
    )
    sessao.flush()


def test_motivo_so_vale_para_outra_situacao(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id, motivo_outra=MotivoOutraSituacao.ROTULO_CONHECIDO))
    with pytest.raises(IntegrityError):
        sessao.flush()


@pytest.mark.parametrize("tipo", ["padronizada", "original"])
@pytest.mark.parametrize("texto", [None, "", "  "])
def test_permanencia_padronizada_ou_original_exige_texto(
    sessao: Session, tipo: str, texto: str | None
) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id, permanencia_tipo=tipo, permanencia_texto=texto))
    with pytest.raises(IntegrityError):
        sessao.flush()


@pytest.mark.parametrize("tipo", ["padronizada", "original"])
def test_permanencia_padronizada_ou_original_com_texto_e_aceita(sessao: Session, tipo: str) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id, permanencia_tipo=tipo, permanencia_texto="90 dias"))
    sessao.flush()


@pytest.mark.parametrize("tipo", ["nenhuma", "prazos_divergentes", "varia_conforme_motivo"])
def test_outros_tipos_de_permanencia_nao_levam_texto(sessao: Session, tipo: str) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id, permanencia_tipo=tipo, permanencia_texto="90 dias"))
    with pytest.raises(IntegrityError):
        sessao.flush()


@pytest.mark.parametrize("tipo", ["nenhuma", "prazos_divergentes", "varia_conforme_motivo"])
def test_outros_tipos_de_permanencia_sem_texto_sao_aceitos(sessao: Session, tipo: str) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id, permanencia_tipo=tipo, permanencia_texto=None))
    sessao.flush()


def test_tipo_de_permanencia_desconhecido_e_recusado(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id, permanencia_tipo="qualquer", permanencia_texto=None))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_requisito_tem_um_registro_por_territorio(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id))
    sessao.flush()
    sessao.add(requisito(primeira.id, hash_fonte=OUTRO_HASH))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_requisito_exige_territorio_e_coleta_existentes(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(requisito(primeira.id, territorio_codigo="XX"))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_valores_padrao_do_requisito(sessao: Session) -> None:
    primeira = preparar(sessao)
    novo = requisito(primeira.id)
    sessao.add(novo)
    sessao.flush()
    sessao.refresh(novo)
    assert novo.aceita_rg is False
    assert novo.varia_conforme_motivo is False
    assert novo.permanencia_tipo == "nenhuma"
    assert novo.permanencia_texto is None
    assert novo.observacoes == []


# --------------------------------------------------------------------------- mudanca_retida
def test_retencao_pendente_e_aceita(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(retida(primeira.id))
    sessao.flush()


def test_so_uma_retencao_pendente_por_territorio(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(retida(primeira.id))
    sessao.flush()
    sessao.add(retida(primeira.id, hash_fonte_lido=OUTRO_HASH))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_so_uma_retencao_rejeitada_por_territorio(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(retida(primeira.id, estado=EstadoDaRetencao.REJEITADA))
    sessao.flush()
    sessao.add(retida(primeira.id, estado=EstadoDaRetencao.REJEITADA, hash_fonte_lido=OUTRO_HASH))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_uma_pendente_e_uma_rejeitada_convivem_no_mesmo_territorio(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(retida(primeira.id, estado=EstadoDaRetencao.REJEITADA))
    sessao.add(retida(primeira.id, estado=EstadoDaRetencao.PENDENTE, hash_fonte_lido=OUTRO_HASH))
    sessao.flush()


def test_retencoes_pendentes_de_territorios_diferentes_convivem(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(retida(primeira.id, territorio_codigo="AR"))
    sessao.add(retida(primeira.id, territorio_codigo="US"))
    sessao.flush()


@pytest.mark.parametrize(
    "estado",
    [EstadoDaRetencao.CONFIRMADA, EstadoDaRetencao.REVERTIDA, EstadoDaRetencao.SUPERADA],
)
def test_retencoes_encerradas_podem_se_acumular(sessao: Session, estado: EstadoDaRetencao) -> None:
    primeira = preparar(sessao)
    sessao.add(retida(primeira.id, estado=estado, resolvida_em=AGORA))
    sessao.add(retida(primeira.id, estado=estado, resolvida_em=AGORA, hash_fonte_lido=OUTRO_HASH))
    sessao.flush()


def test_retencao_pode_ter_exibida_ou_lida_sem_informacao(sessao: Session) -> None:
    """Nulo = "sem informação": o país ainda não tinha registro, ou a linha saiu da fonte."""
    primeira = preparar(sessao)
    sessao.add(retida(primeira.id, categoria_exibida=None))
    sessao.flush()


# --------------------------------------------------------------------------- item_para_revisao
def test_item_pendente_e_aceito(sessao: Session) -> None:
    sessao.add(item())
    sessao.flush()


def test_tipo_e_valor_sao_unicos(sessao: Session) -> None:
    sessao.add(item())
    sessao.flush()
    sessao.add(item())
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_mesmo_valor_em_tipos_diferentes_convive(sessao: Session) -> None:
    sessao.add(item(tipo=TipoDeItemParaRevisao.NOME, valor="x"))
    sessao.add(item(tipo=TipoDeItemParaRevisao.ROTULO, valor="x"))
    sessao.flush()


def test_nome_pode_ser_ignorado_com_motivo(sessao: Session) -> None:
    sessao.add(item(estado=EstadoDoItem.IGNORADO, motivo_ignorar="não é um território"))
    sessao.flush()


@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_ignorar_exige_motivo_nao_vazio(sessao: Session, motivo: str | None) -> None:
    sessao.add(item(estado=EstadoDoItem.IGNORADO, motivo_ignorar=motivo))
    with pytest.raises(IntegrityError):
        sessao.flush()


@pytest.mark.parametrize("tipo", [TipoDeItemParaRevisao.ROTULO, TipoDeItemParaRevisao.REGRA])
def test_rotulo_e_regra_nao_podem_ser_ignorados(
    sessao: Session, tipo: TipoDeItemParaRevisao
) -> None:
    sessao.add(item(tipo=tipo, estado=EstadoDoItem.IGNORADO, motivo_ignorar="tanto faz"))
    with pytest.raises(IntegrityError):
        sessao.flush()


@pytest.mark.parametrize("tipo", [TipoDeItemParaRevisao.ROTULO, TipoDeItemParaRevisao.REGRA])
def test_rotulo_e_regra_podem_ficar_resolvidos(
    sessao: Session, tipo: TipoDeItemParaRevisao
) -> None:
    sessao.add(item(tipo=tipo, estado=EstadoDoItem.RESOLVIDO, resolvido_em=AGORA))
    sessao.flush()


# --------------------------------------------------------------------------- enums como texto
def test_enums_sao_gravados_como_texto(sessao: Session) -> None:
    primeira = preparar(sessao)
    sessao.add(
        requisito(
            primeira.id,
            categoria=CategoriaDeVisto.OUTRA_SITUACAO,
            motivo_outra=MotivoOutraSituacao.ROTULO_DESCONHECIDO,
        )
    )
    sessao.add(retida(primeira.id, estado=EstadoDaRetencao.PENDENTE))
    sessao.add(item(tipo=TipoDeItemParaRevisao.REGRA, valor="JM"))
    sessao.flush()

    def valores(consulta: str) -> list[tuple[Any, ...]]:
        return [tuple(linha) for linha in sessao.execute(text(consulta))]

    assert valores("select categoria, motivo_outra from requisito_visto") == [
        ("outra_situacao", "rotulo_desconhecido")
    ]
    assert valores("select estado, categoria_exibida, categoria_lida from mudanca_retida") == [
        ("pendente", "visto_exigido", "isento")
    ]
    assert valores("select tipo, estado from item_para_revisao") == [("regra", "pendente")]
    assert valores("select resultado from coleta_vistos") == [("valida",)]
    tipos = valores(
        "select data_type from information_schema.columns "
        "where table_name = 'requisito_visto' and column_name in ('categoria', 'motivo_outra')"
    )
    assert {tipo[0] for tipo in tipos} == {"character varying"}
