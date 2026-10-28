"""Consolidação: linhas da fonte -> um candidato por código (rótulos combinados e duplicatas)."""

import hashlib
import json
from pathlib import Path

import yaml

from farol.dominio import CategoriaDeVisto, MotivoOutraSituacao
from farol.vistos.consolidacao import (
    NomeDesconhecido,
    RotuloDesconhecido,
    calcular_hash_da_fonte,
    consolidar,
)
from farol.vistos.dicionario import Dicionario, calcular_hash_observacao, carregar_dicionario
from farol.vistos.fonte import (
    TABELA_DE_TERRITORIOS,
    TABELA_NAO_RECONHECIDOS,
    TABELA_PRINCIPAL,
    LinhaDaFonte,
)
from farol.vistos.permanencia import Permanencia, TipoDePermanencia

ISENTO = CategoriaDeVisto.ISENTO
NA_CHEGADA = CategoriaDeVisto.VISTO_NA_CHEGADA
ELETRONICA = CategoriaDeVisto.AUTORIZACAO_ELETRONICA
EXIGIDO = CategoriaDeVisto.VISTO_EXIGIDO
OUTRA = CategoriaDeVisto.OUTRA_SITUACAO


def linha(
    nome: str,
    rotulo: str,
    permanencia: str = "",
    notas: str = "",
    *,
    tabela: str = TABELA_PRINCIPAL,
    grupo: str | None = None,
) -> LinhaDaFonte:
    return LinhaDaFonte(tabela, grupo, nome, rotulo, permanencia, notas)


# --------------------------------------------------------------------------- a fixture inteira
def test_um_candidato_por_codigo_do_mapa(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    resultado = consolidar(linhas_da_fonte, dicionario_real)
    assert resultado.paises_reconhecidos == 226  # 193 da principal + 33 dos territórios, 3 em SH
    assert len(resultado.candidatos) == 226
    assert all(codigo == candidato.codigo for codigo, candidato in resultado.candidatos.items())
    assert resultado.nomes_desconhecidos == ()
    assert resultado.rotulos_desconhecidos == ()
    assert len(resultado.ignoradas) == 21


def test_a_consolidacao_e_deterministica(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    assert consolidar(linhas_da_fonte, dicionario_real) == consolidar(
        linhas_da_fonte, dicionario_real
    )


def test_casos_da_fixture(dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]) -> None:
    candidatos = consolidar(linhas_da_fonte, dicionario_real).candidatos

    argentina = candidatos["AR"]
    assert argentina.categoria is ISENTO
    assert argentina.aceita_rg is True
    assert argentina.rotulo_original == "Freedom of Movement"
    assert argentina.permanencia == Permanencia(TipoDePermanencia.NENHUMA, None)  # coluna em branco
    assert candidatos["AL"].permanencia == Permanencia(TipoDePermanencia.PADRONIZADA, "90 dias")
    assert candidatos["VE"].permanencia == Permanencia(TipoDePermanencia.PADRONIZADA, "90 dias")

    assert candidatos["VE"].aceita_rg is False
    assert candidatos["GY"].aceita_rg is False
    assert {c for c, v in candidatos.items() if v.aceita_rg} == {
        "AR", "BO", "CL", "CO", "EC", "PY", "PE", "UY"
    }  # fmt: skip

    estados_unidos = candidatos["US"]
    assert estados_unidos.categoria is EXIGIDO
    assert estados_unidos.permanencia == Permanencia(TipoDePermanencia.NENHUMA, None)

    assert candidatos["AU"].categoria is EXIGIDO
    assert candidatos["OM"].categoria is ELETRONICA
    assert candidatos["OM"].rotulo_original == "Visa not required / eVisa"
    assert candidatos["OM"].permanencia == Permanencia(
        TipoDePermanencia.ORIGINAL, "14 days / 30 days"
    )
    assert candidatos["ET"].permanencia == Permanencia(TipoDePermanencia.ORIGINAL, "up to 90 days")
    assert candidatos["HK"].categoria is ISENTO
    assert candidatos["HK"].permanencia == Permanencia(TipoDePermanencia.NENHUMA, None)
    assert candidatos["HK"].observacoes[0].texto == "90 days"  # O3: o prazo vai para as notas
    assert candidatos["TW"].categoria is EXIGIDO
    assert candidatos["PR"].categoria is EXIGIDO


def test_santa_helena_ascensao_e_tristao_da_cunha_sao_um_candidato_so(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    candidato = consolidar(linhas_da_fonte, dicionario_real).candidatos["SH"]
    assert candidato.categoria is OUTRA
    assert candidato.motivo_outra is MotivoOutraSituacao.ROTULO_CONHECIDO
    assert candidato.rotulo_original == "Visa not required / eVisa / Permission required"
    assert [lin.nome for lin in candidato.linhas_fonte] == [
        "Saint Helena",
        "Ascension Island",
        "Tristan da Cunha",
    ]
    assert candidato.aceita_rg is False
    # a categoria vale o mesmo que a leitura do rótulo junto (contrato, regra 2)
    junto = dicionario_real.classificar_rotulo(candidato.rotulo_original)
    assert (junto.categoria, junto.motivo_outra) == (candidato.categoria, candidato.motivo_outra)


def test_jamaica_e_zambia_variam_conforme_o_motivo(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    candidatos = consolidar(linhas_da_fonte, dicionario_real).candidatos
    for codigo in ("JM", "ZM"):
        candidato = candidatos[codigo]
        assert candidato.varia_conforme_motivo is True
        assert candidato.permanencia == Permanencia(TipoDePermanencia.VARIA_CONFORME_MOTIVO, None)
        assert candidato.hash_observacao == dicionario_real.regras[codigo].hash_observacao
    assert candidatos["JM"].categoria is ISENTO  # a categoria continua sendo escolhida pelo FR-007

    albania = candidatos["AL"]
    assert albania.varia_conforme_motivo is False
    assert albania.hash_observacao is None
    assert albania.permanencia.tipo is TipoDePermanencia.PADRONIZADA


# --------------------------------------------------------------------------- várias linhas
def test_linhas_do_mesmo_codigo_valem_a_categoria_mais_exigente(
    dicionario_real: Dicionario,
) -> None:
    linhas = [
        linha("Albania", "Visa not required", "90 days"),
        linha("Albania", "Visa required", tabela=TABELA_DE_TERRITORIOS, grupo="X"),
    ]
    candidato = consolidar(linhas, dicionario_real).candidatos["AL"]
    assert candidato.categoria is EXIGIDO
    assert candidato.motivo_outra is None
    assert candidato.rotulo_original == "Visa not required / Visa required"
    assert candidato.linhas_fonte == tuple(linhas)


def test_outra_situacao_de_uma_linha_vence_as_outras(dicionario_real: Dicionario) -> None:
    linhas = [linha("Albania", "Visa required"), linha("Albania", "Permit required")]
    candidato = consolidar(linhas, dicionario_real).candidatos["AL"]
    assert candidato.categoria is OUTRA
    assert candidato.motivo_outra is MotivoOutraSituacao.ROTULO_CONHECIDO


def test_rotulo_combinado_dentro_de_uma_linha_e_de_varias(dicionario_real: Dicionario) -> None:
    linhas = [linha("Albania", "Visa not required / eVisa"), linha("Albania", "Visa on arrival")]
    candidato = consolidar(linhas, dicionario_real).candidatos["AL"]
    assert candidato.categoria is ELETRONICA
    assert candidato.rotulo_original == "Visa not required / eVisa / Visa on arrival"


def test_rotulo_desconhecido_em_uma_linha_leva_o_pais_a_outra_situacao(
    dicionario_real: Dicionario,
) -> None:
    linhas = [
        linha("Albania", "Visa not required"),
        linha("Albania", "Super Visa", tabela=TABELA_DE_TERRITORIOS, grupo="X"),
    ]
    resultado = consolidar(linhas, dicionario_real)
    candidato = resultado.candidatos["AL"]
    assert candidato.categoria is OUTRA  # nunca "isento"
    assert candidato.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert candidato.rotulo_original == "Visa not required / Super Visa"
    assert resultado.rotulos_desconhecidos == (
        RotuloDesconhecido("super visa", TABELA_DE_TERRITORIOS, "Albania"),
    )


def test_rotulo_desconhecido_dentro_de_um_combinado_vai_inteiro_para_revisao(
    dicionario_real: Dicionario,
) -> None:
    resultado = consolidar([linha("Albania", "Visa not required / Rótulo Novo")], dicionario_real)
    candidato = resultado.candidatos["AL"]
    assert candidato.categoria is OUTRA
    assert candidato.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert resultado.rotulos_desconhecidos == (
        RotuloDesconhecido("visa not required / rótulo novo", TABELA_PRINCIPAL, "Albania"),
    )


def test_rotulo_desconhecido_vence_outra_situacao_conhecida(dicionario_real: Dicionario) -> None:
    linhas = [linha("Albania", "Permit required"), linha("Albania", "Super Visa")]
    candidato = consolidar(linhas, dicionario_real).candidatos["AL"]
    assert candidato.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO


def test_o_rg_so_vale_para_uma_linha_isolada(dicionario_real: Dicionario) -> None:
    nota = "Entry is allowed with a valid ID card that is less than 10 years old."
    sozinha = consolidar([linha("Argentina", "Freedom of Movement", notas=nota)], dicionario_real)
    assert sozinha.candidatos["AR"].aceita_rg is True

    duas = consolidar(
        [
            linha("Argentina", "Freedom of Movement", notas=nota),
            linha("Argentina", "Visa required", tabela=TABELA_DE_TERRITORIOS, grupo="X"),
        ],
        dicionario_real,
    )
    assert duas.candidatos["AR"].categoria is EXIGIDO
    assert duas.candidatos["AR"].aceita_rg is False


# --------------------------------------------------------------------------- hash da fonte
def test_hash_da_fonte_e_o_sha256_do_json_canonico_das_linhas(dicionario_real: Dicionario) -> None:
    linhas = [linha("Albania", "Visa not required", "90 days", "Uma nota.")]
    candidato = consolidar(linhas, dicionario_real).candidatos["AL"]
    canonico = json.dumps(
        [
            {
                "grupo": None,
                "nome": "Albania",
                "notas": "Uma nota.",
                "permanencia": "90 days",
                "rotulo": "Visa not required",
                "tabela": "principal",
            }
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    esperado = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
    assert candidato.hash_fonte == esperado
    assert calcular_hash_da_fonte(linhas) == esperado


def test_hash_da_fonte_muda_quando_a_fonte_muda(dicionario_real: Dicionario) -> None:
    base = [linha("Albania", "Visa not required", "90 days", "Nota.")]
    alterados = [
        [linha("Albania", "Visa not required", "90 days", "Nota alterada.")],
        [linha("Albania", "Visa not required", "30 days", "Nota.")],
        [linha("Albania", "Visa required", "90 days", "Nota.")],
        [linha("Albania", "Visa not required", "90 days", "Nota.", tabela=TABELA_NAO_RECONHECIDOS)],
    ]
    hashes = {consolidar(b, dicionario_real).candidatos["AL"].hash_fonte for b in alterados}
    original = consolidar(base, dicionario_real).candidatos["AL"].hash_fonte
    assert original not in hashes
    assert len(hashes) == len(alterados)


def test_hash_da_fonte_nao_muda_quando_so_o_dicionario_muda(
    dicionario_real: Dicionario, tmp_path: Path
) -> None:
    """Mudança do dicionário muda a categoria derivada, nunca o hash da fonte (12g)."""
    rotulos = {"Visa not required": {"categoria": "visto_exigido"}}
    nomes = {"nomes": {"Albania": "AL"}, "ignorar": {}}
    for nome, conteudo in (
        ("rotulos.yaml", rotulos),
        ("nomes.yaml", nomes),
        ("regras_por_pais.yaml", {}),
    ):
        (tmp_path / nome).write_text(yaml.safe_dump(conteudo), encoding="utf-8")
    outro = carregar_dicionario(tmp_path)

    linhas = [linha("Albania", "Visa not required", "90 days")]
    a = consolidar(linhas, dicionario_real).candidatos["AL"]
    b = consolidar(linhas, outro).candidatos["AL"]
    assert a.categoria is ISENTO
    assert b.categoria is EXIGIDO
    assert a.hash_fonte == b.hash_fonte


def test_hash_da_fonte_nao_depende_da_ordem_das_linhas(dicionario_real: Dicionario) -> None:
    a = linha("Albania", "Visa not required", "90 days")
    b = linha("Albania", "Visa required", tabela=TABELA_DE_TERRITORIOS, grupo="X")
    um = consolidar([a, b], dicionario_real).candidatos["AL"]
    outro = consolidar([b, a], dicionario_real).candidatos["AL"]
    assert um.hash_fonte == outro.hash_fonte


# --------------------------------------------------------------------------- permanência
def test_permanencias_divergentes_nao_escolhem_um_prazo(dicionario_real: Dicionario) -> None:
    linhas = [
        linha("Albania", "Visa not required", "90 days"),
        linha("Albania", "Visa not required", "30 days"),
    ]
    candidato = consolidar(linhas, dicionario_real).candidatos["AL"]
    assert candidato.permanencia == Permanencia(TipoDePermanencia.PRAZOS_DIVERGENTES, None)


def test_permanencias_iguais_valem_uma_so(dicionario_real: Dicionario) -> None:
    linhas = [
        linha("Albania", "Visa not required", "90 days"),
        linha("Albania", "Visa not required", "90 days"),
    ]
    candidato = consolidar(linhas, dicionario_real).candidatos["AL"]
    assert candidato.permanencia == Permanencia(TipoDePermanencia.PADRONIZADA, "90 dias")


def test_linha_sem_prazo_nao_diverge_da_que_tem_prazo(dicionario_real: Dicionario) -> None:
    """Ausência de prazo em outra linha do mesmo país não diverge: vale o da tabela principal."""
    linhas = [
        linha("Albania", "Visa not required", "90 days"),
        linha("Albania", "Visa not required", tabela=TABELA_DE_TERRITORIOS, grupo="X"),
    ]
    candidato = consolidar(linhas, dicionario_real).candidatos["AL"]
    assert candidato.permanencia == Permanencia(TipoDePermanencia.PADRONIZADA, "90 dias")

    em_branco = [
        linha("Albania", "Visa not required", ""),
        linha("Albania", "Visa required", "60 days"),
    ]
    assert consolidar(em_branco, dicionario_real).candidatos["AL"].permanencia == Permanencia(
        TipoDePermanencia.PADRONIZADA, "60 dias"
    )


def test_prazo_so_vem_de_linha_da_tabela_principal(dicionario_real: Dicionario) -> None:
    linhas = [
        linha(
            "Hong Kong", "Visa not required", "90 days", tabela=TABELA_DE_TERRITORIOS, grupo="China"
        )
    ]
    candidato = consolidar(linhas, dicionario_real).candidatos["HK"]
    assert candidato.permanencia == Permanencia(TipoDePermanencia.NENHUMA, None)


def test_permanencia_em_formato_desconhecido_fica_como_na_fonte(
    dicionario_real: Dicionario,
) -> None:
    candidato = consolidar([linha("Albania", "Visa required", "up to 90 days")], dicionario_real)
    assert candidato.candidatos["AL"].permanencia == Permanencia(
        TipoDePermanencia.ORIGINAL, "up to 90 days"
    )


def test_prazos_diferem_por_motivo_vale_mais_que_a_divergencia(dicionario_real: Dicionario) -> None:
    linhas = [
        linha("Jamaica", "Visa not required", "6 months", "90 days (business), 6 months (tourist).")
    ]
    candidato = consolidar(linhas, dicionario_real).candidatos["JM"]
    assert candidato.permanencia == Permanencia(TipoDePermanencia.VARIA_CONFORME_MOTIVO, None)
    assert candidato.varia_conforme_motivo is True


# --------------------------------------------------------------------------- observações
def test_uma_observacao_por_linha_com_nota_e_o_hash_e_do_texto(dicionario_real: Dicionario) -> None:
    linhas = [
        linha("Albania", "Visa not required", notas="Primeira nota."),
        linha("Albania", "Visa not required", notas=""),
        linha(
            "Albania",
            "Visa not required",
            notas="Segunda nota.",
            tabela=TABELA_DE_TERRITORIOS,
            grupo="X",
        ),
    ]
    candidato = consolidar(linhas, dicionario_real).candidatos["AL"]
    assert [o.texto for o in candidato.observacoes] == ["Primeira nota.", "Segunda nota."]
    assert [o.hash for o in candidato.observacoes] == [
        hashlib.sha256(b"Primeira nota.").hexdigest(),
        hashlib.sha256(b"Segunda nota.").hexdigest(),
    ]


def test_pais_sem_nota_nao_tem_observacao(dicionario_real: Dicionario) -> None:
    assert (
        consolidar([linha("Albania", "Visa not required")], dicionario_real)
        .candidatos["AL"]
        .observacoes
        == ()
    )


def test_hash_da_observacao_so_para_paises_da_lista_curada(dicionario_real: Dicionario) -> None:
    jamaica = linha("Jamaica", "Visa not required", notas="Nota A")
    candidato = consolidar([jamaica], dicionario_real).candidatos["JM"]
    assert candidato.hash_observacao == calcular_hash_observacao(["Nota A"])
    assert candidato.hash_observacao != dicionario_real.regras["JM"].hash_observacao


# --------------------------------------------------------------------------- nomes
def test_nomes_ignorados_e_desconhecidos_nao_geram_candidato(dicionario_real: Dicionario) -> None:
    linhas = [
        linha("Kosovo", "Visa not required", tabela=TABELA_NAO_RECONHECIDOS),
        linha("Atlantis", "Visa not required"),
        linha("Albania", "Visa not required"),
    ]
    resultado = consolidar(linhas, dicionario_real)
    assert set(resultado.candidatos) == {"AL"}
    assert resultado.nomes_desconhecidos == (NomeDesconhecido(TABELA_PRINCIPAL, "Atlantis"),)
    assert resultado.ignoradas == (linhas[0],)
    assert resultado.paises_reconhecidos == 1  # os ignorados não contam como reconhecidos


def test_rotulo_de_nome_desconhecido_nao_vai_para_revisao(dicionario_real: Dicionario) -> None:
    """O rótulo é registrado com o país onde apareceu; sem país ligado, só o nome é registrado."""
    resultado = consolidar([linha("Atlantis", "Super Visa")], dicionario_real)
    assert resultado.rotulos_desconhecidos == ()
    assert len(resultado.nomes_desconhecidos) == 1


def test_codigo_vem_da_ligacao_e_nao_do_nome(dicionario_real: Dicionario) -> None:
    resultado = consolidar(
        [linha("United Kingdom and Crown dependencies", "Visa not required", "6 months")],
        dicionario_real,
    )
    assert set(resultado.candidatos) == {"GB"}
    assert resultado.candidatos["GB"].permanencia == Permanencia(
        TipoDePermanencia.PADRONIZADA, "6 meses"
    )


def test_sem_linhas_nao_ha_candidatos(dicionario_real: Dicionario) -> None:
    resultado = consolidar([], dicionario_real)
    assert resultado.candidatos == {}
    assert resultado.paises_reconhecidos == 0
