"""Formato e regras de leitura dos dicionários (YAML sintético: nada do conteúdo real).

As regras estão em `specs/002-visto-brasileiros/contracts/dicionario-de-rotulos.md`.
"""

import ast
import hashlib
import inspect
import logging
from pathlib import Path
from typing import Any

import pytest
import yaml

from farol.dominio import CategoriaDeVisto, MotivoOutraSituacao
from farol.vistos import dicionario as modulo
from farol.vistos.dicionario import (
    DIRETORIO_DOS_DICIONARIOS,
    ORDEM_DE_EXIGENCIA,
    Dicionario,
    ErroDeDicionario,
    calcular_hash_observacao,
    carregar_dicionario,
    mais_exigente,
)

ISENTO = CategoriaDeVisto.ISENTO
NA_CHEGADA = CategoriaDeVisto.VISTO_NA_CHEGADA
ELETRONICA = CategoriaDeVisto.AUTORIZACAO_ELETRONICA
EXIGIDO = CategoriaDeVisto.VISTO_EXIGIDO
OUTRA = CategoriaDeVisto.OUTRA_SITUACAO

ROTULOS: dict[str, Any] = {
    "Visa not required": {"categoria": "isento"},
    "Freedom of Movement": {"categoria": "isento", "aceita_rg": True},
    "Visa on arrival": {"categoria": "visto_na_chegada"},
    "eVisa": {"categoria": "autorizacao_eletronica"},
    "Visa required": {"categoria": "visto_exigido", "motivo": "exemplo"},
    "Permit required": {"categoria": "outra_situacao", "exemplo": "Tokelau"},
}
NOMES: dict[str, str] = {"Albania": "AL", "Côte d’Ivoire": "CI", "Macau": "MO"}
IGNORAR: dict[str, str] = {"Kosovo": "Usa a identidade da Sérvia"}
HASH = "a" * 64
REGRAS: dict[str, Any] = {
    "JM": {
        "varia_conforme_motivo": True,
        "prazos_diferem_por_motivo": True,
        "hash_observacao": HASH,
    }
}


def escrever(
    pasta: Path,
    *,
    rotulos: dict[str, Any] | None = None,
    nomes: dict[str, str] | None = None,
    ignorar: dict[str, str | None] | None = None,
    regras: dict[str, Any] | None = None,
) -> Path:
    def gravar(nome: str, conteudo: object) -> None:
        texto = yaml.safe_dump(conteudo, allow_unicode=True, sort_keys=False)
        (pasta / nome).write_text(texto, encoding="utf-8")

    gravar("rotulos.yaml", ROTULOS if rotulos is None else rotulos)
    gravar(
        "nomes.yaml",
        {
            "nomes": NOMES if nomes is None else nomes,
            "ignorar": IGNORAR if ignorar is None else ignorar,
        },
    )
    gravar("regras_por_pais.yaml", REGRAS if regras is None else regras)
    return pasta


@pytest.fixture
def dicionario(tmp_path: Path) -> Dicionario:
    return carregar_dicionario(escrever(tmp_path))


# --------------------------------------------------------------------------- validação ao carregar
def test_carrega_os_tres_arquivos(dicionario: Dicionario) -> None:
    assert set(dicionario.rotulos) == {
        "visa not required",
        "freedom of movement",
        "visa on arrival",
        "evisa",
        "visa required",
        "permit required",
    }
    assert dicionario.rotulos["freedom of movement"].aceita_rg is True
    assert dicionario.rotulos["visa required"].motivo == "exemplo"
    assert dicionario.rotulos["permit required"].exemplo == "Tokelau"
    assert dicionario.regras["JM"].varia_conforme_motivo is True
    assert dicionario.regras["JM"].prazos_diferem_por_motivo is True
    assert dicionario.regras["JM"].hash_observacao == HASH


def test_categoria_invalida_e_erro(tmp_path: Path) -> None:
    rotulos = {**ROTULOS, "Visa foo": {"categoria": "quase_isento"}}
    with pytest.raises(ErroDeDicionario, match="categoria"):
        carregar_dicionario(escrever(tmp_path, rotulos=rotulos))


def test_entrada_sem_categoria_e_erro(tmp_path: Path) -> None:
    with pytest.raises(ErroDeDicionario, match="categoria"):
        carregar_dicionario(escrever(tmp_path, rotulos={"Visa foo": {"exemplo": "X"}}))


def test_campo_desconhecido_na_entrada_e_erro(tmp_path: Path) -> None:
    rotulos = {"Visa foo": {"categoria": "isento", "categora": "isento"}}
    with pytest.raises(ErroDeDicionario, match="categora"):
        carregar_dicionario(escrever(tmp_path, rotulos=rotulos))


def test_aceita_rg_precisa_ser_booleano(tmp_path: Path) -> None:
    rotulos = {"Visa foo": {"categoria": "isento", "aceita_rg": "sim"}}
    with pytest.raises(ErroDeDicionario, match="aceita_rg"):
        carregar_dicionario(escrever(tmp_path, rotulos=rotulos))


def test_rotulos_repetidos_depois_de_normalizar_sao_erro(tmp_path: Path) -> None:
    rotulos = {
        "Visa required": {"categoria": "visto_exigido"},
        "visa  REQUIRED": {"categoria": "isento"},
    }
    with pytest.raises(ErroDeDicionario, match="repetid"):
        carregar_dicionario(escrever(tmp_path, rotulos=rotulos))


def test_nome_nas_duas_listas_e_erro(tmp_path: Path) -> None:
    with pytest.raises(ErroDeDicionario, match="'nomes' e em 'ignorar'"):
        carregar_dicionario(
            escrever(tmp_path, nomes={"Kosovo": "XK"}, ignorar={"kosovo": "motivo"})
        )


@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_ignorar_sem_motivo_e_erro(tmp_path: Path, motivo: str | None) -> None:
    with pytest.raises(ErroDeDicionario, match="Abkhazia"):
        carregar_dicionario(escrever(tmp_path, ignorar={"Abkhazia": motivo}))


def test_nomes_repetidos_depois_de_normalizar_sao_erro(tmp_path: Path) -> None:
    with pytest.raises(ErroDeDicionario, match="repetid"):
        carregar_dicionario(
            escrever(tmp_path, nomes={"Côte d’Ivoire": "CI", "Côte d'Ivoire": "CI"})
        )


def test_codigo_inexistente_e_erro(tmp_path: Path) -> None:
    pasta = escrever(tmp_path)
    with pytest.raises(ErroDeDicionario, match="Macau"):
        carregar_dicionario(pasta, codigos_validos={"AL", "CI", "JM"})


def test_codigo_de_area_neutra_e_erro(tmp_path: Path) -> None:
    pasta = escrever(tmp_path, nomes={"Western Sahara": "EH"})
    with pytest.raises(ErroDeDicionario, match="neutra"):
        carregar_dicionario(pasta, codigos_validos={"EH", "JM"}, codigos_neutros={"EH"})


def test_codigo_inexistente_na_regra_por_pais_e_erro(tmp_path: Path) -> None:
    pasta = escrever(tmp_path)
    with pytest.raises(ErroDeDicionario, match="JM"):
        carregar_dicionario(pasta, codigos_validos={"AL", "CI", "MO"})


def test_sem_lista_de_codigos_nao_valida_os_codigos(tmp_path: Path) -> None:
    assert carregar_dicionario(escrever(tmp_path)).nomes["albania"] == "AL"


def test_codigo_que_o_yaml_leu_como_booleano_e_erro(tmp_path: Path) -> None:
    pasta = escrever(tmp_path)
    (pasta / "nomes.yaml").write_text("nomes:\n  Norway: NO\nignorar: {}\n", encoding="utf-8")
    with pytest.raises(ErroDeDicionario, match="Norway"):
        carregar_dicionario(pasta)


@pytest.mark.parametrize(
    "regra",
    [
        {
            "varia_conforme_motivo": True,
            "prazos_diferem_por_motivo": True,
            "hash_observacao": "abc",
        },
        {
            "varia_conforme_motivo": "sim",
            "prazos_diferem_por_motivo": True,
            "hash_observacao": HASH,
        },
        {"varia_conforme_motivo": True, "hash_observacao": HASH},
        {"varia_conforme_motivo": True, "prazos_diferem_por_motivo": True},
    ],
)
def test_regra_por_pais_mal_formada_e_erro(tmp_path: Path, regra: dict[str, Any]) -> None:
    with pytest.raises(ErroDeDicionario, match="JM"):
        carregar_dicionario(escrever(tmp_path, regras={"JM": regra}))


def test_arquivo_que_nao_e_um_mapa_e_erro(tmp_path: Path) -> None:
    pasta = escrever(tmp_path)
    (pasta / "rotulos.yaml").write_text("- um\n- dois\n", encoding="utf-8")
    with pytest.raises(ErroDeDicionario, match=r"rotulos\.yaml"):
        carregar_dicionario(pasta)


def test_arquivo_ausente_e_erro(tmp_path: Path) -> None:
    pasta = escrever(tmp_path)
    (pasta / "regras_por_pais.yaml").unlink()
    with pytest.raises(ErroDeDicionario, match=r"regras_por_pais\.yaml"):
        carregar_dicionario(pasta)


def test_os_arquivos_sao_lidos_de_dentro_do_pacote_por_importlib_resources() -> None:
    arvore = ast.parse(inspect.getsource(modulo))
    importados = {n.module for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom)}
    assert "importlib.resources" in importados
    assert DIRETORIO_DOS_DICIONARIOS.name == "dicionarios_yaml"
    assert (
        str(DIRETORIO_DOS_DICIONARIOS).replace("\\", "/").endswith("farol/vistos/dicionarios_yaml")
    )


# --------------------------------------------------------------------------- ordem de exigência
def test_ordem_de_exigencia_vai_do_isento_ao_visto_exigido() -> None:
    assert ORDEM_DE_EXIGENCIA == (ISENTO, NA_CHEGADA, ELETRONICA, EXIGIDO)
    assert OUTRA not in ORDEM_DE_EXIGENCIA


def test_mais_exigente() -> None:
    assert mais_exigente([ISENTO, ELETRONICA]) is ELETRONICA
    assert mais_exigente([EXIGIDO, ISENTO, NA_CHEGADA]) is EXIGIDO
    assert mais_exigente([NA_CHEGADA]) is NA_CHEGADA
    with pytest.raises(ValueError):
        mais_exigente([ISENTO, OUTRA])
    with pytest.raises(ValueError):
        mais_exigente([])


# --------------------------------------------------------------------------- classificar_rotulo
def test_rotulo_direto_usa_a_entrada(dicionario: Dicionario) -> None:
    resultado = dicionario.classificar_rotulo("Visa on arrival")
    assert resultado.categoria is NA_CHEGADA
    assert resultado.motivo_outra is None
    assert resultado.rotulo_para_revisao is None
    assert resultado.aceita_rg is False


def test_rotulo_direto_ignora_caixa_espacos_e_apostrofos(dicionario: Dicionario) -> None:
    assert dicionario.classificar_rotulo("  VISA   not\xa0required[3] ").categoria is ISENTO


def test_rotulo_conhecido_em_outra_situacao(dicionario: Dicionario) -> None:
    resultado = dicionario.classificar_rotulo("Permit required")
    assert resultado.categoria is OUTRA
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_CONHECIDO
    assert resultado.rotulo_para_revisao is None


@pytest.mark.parametrize(
    ("rotulo", "esperada"),
    [
        ("eVisa / Visa on arrival", ELETRONICA),
        ("eVisa/Visa on arrival", ELETRONICA),
        ("Visa not required / eVisa", ELETRONICA),
        ("Visa on arrival / Visa not required", NA_CHEGADA),
        ("Visa not required / Visa required", EXIGIDO),
        ("Visa not required / Visa on arrival / eVisa", ELETRONICA),
    ],
)
def test_rotulo_combinado_vale_a_categoria_mais_exigente(
    dicionario: Dicionario, rotulo: str, esperada: CategoriaDeVisto
) -> None:
    resultado = dicionario.classificar_rotulo(rotulo)
    assert resultado.categoria is esperada
    assert resultado.motivo_outra is None
    assert resultado.rotulo_para_revisao is None


def test_combinado_com_parte_em_outra_situacao_vence(dicionario: Dicionario) -> None:
    for rotulo in ("Visa not required / Permit required", "Permit required / Visa required"):
        resultado = dicionario.classificar_rotulo(rotulo)
        assert resultado.categoria is OUTRA
        assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_CONHECIDO
        assert resultado.rotulo_para_revisao is None


def test_combinado_com_parte_desconhecida_vai_para_revisao(dicionario: Dicionario) -> None:
    resultado = dicionario.classificar_rotulo("Visa required / Admission refused")
    assert resultado.categoria is OUTRA
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert resultado.rotulo_para_revisao == "visa required / admission refused"

    resultado = dicionario.classificar_rotulo("Visa not required / Rótulo Novo")
    assert resultado.categoria is OUTRA  # nunca "isento"
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert resultado.rotulo_para_revisao == "visa not required / rótulo novo"


def test_rotulo_inteiro_desconhecido_vai_para_revisao(dicionario: Dicionario) -> None:
    resultado = dicionario.classificar_rotulo("Super Visa[4]")
    assert resultado.categoria is OUTRA
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert resultado.rotulo_para_revisao == "super visa"
    assert resultado.aceita_rg is False


def test_parte_vazia_do_combinado_e_desconhecida(dicionario: Dicionario) -> None:
    resultado = dicionario.classificar_rotulo("Visa required / ")
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO


def test_rotulo_vazio_e_outra_situacao_sem_nada_para_revisar(dicionario: Dicionario) -> None:
    resultado = dicionario.classificar_rotulo("  ")
    assert resultado.categoria is OUTRA
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert resultado.rotulo_para_revisao is None


# --------------------------------------------------------------------------- aceita_rg
def test_aceita_rg_exige_a_entrada_e_a_frase_id_card_na_nota(dicionario: Dicionario) -> None:
    nota = "Entry is allowed with a valid ID card that is less than 10 years old."
    resultado = dicionario.classificar_rotulo("Freedom of Movement", nota)
    assert resultado.categoria is ISENTO
    assert resultado.aceita_rg is True


def test_aceita_rg_ignora_a_caixa_da_frase(dicionario: Dicionario) -> None:
    assert dicionario.classificar_rotulo("freedom of movement", "valid id CARD").aceita_rg is True


def test_sem_a_frase_continua_isento_sem_rg_e_avisa_no_log(
    dicionario: Dicionario, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="farol.vistos"):
        resultado = dicionario.classificar_rotulo("Freedom of Movement", "Livre circulação.")
    assert resultado.categoria is ISENTO
    assert resultado.aceita_rg is False
    avisos = [r.getMessage() for r in caplog.records if r.name == "farol.vistos"]
    assert any("ID card" in aviso for aviso in avisos)


def test_nota_com_id_card_em_rotulo_sem_aceita_rg_nao_afirma_o_rg(
    dicionario: Dicionario, caplog: pytest.LogCaptureFixture
) -> None:
    """A Guiana: "Visa not required" com visita à fronteira por ID card não é "basta o RG"."""
    nota = (
        "Brief visits just to the border town of Lethem are possible with a valid Brazilian ID card"
    )
    with caplog.at_level(logging.WARNING, logger="farol.vistos"):
        resultado = dicionario.classificar_rotulo("Visa not required", nota)
    assert resultado.aceita_rg is False
    assert not caplog.records


def test_rotulo_combinado_nunca_aceita_rg(dicionario: Dicionario) -> None:
    resultado = dicionario.classificar_rotulo(
        "Freedom of Movement / eVisa", "Entry is allowed with a valid ID card"
    )
    assert resultado.categoria is ELETRONICA
    assert resultado.aceita_rg is False


# --------------------------------------------------------------------------- ligar_nome
def test_ligar_nome_por_nomes_ignorar_ou_desconhecido(dicionario: Dicionario) -> None:
    ligado = dicionario.ligar_nome("Albania")
    assert ligado.codigo == "AL"
    assert not ligado.ignorado
    assert not ligado.desconhecido

    ignorado = dicionario.ligar_nome("Kosovo")
    assert ignorado.codigo is None
    assert ignorado.ignorado
    assert ignorado.motivo == "Usa a identidade da Sérvia"
    assert not ignorado.desconhecido

    desconhecido = dicionario.ligar_nome("Atlantis")
    assert desconhecido.codigo is None
    assert not desconhecido.ignorado
    assert desconhecido.desconhecido


def test_ligar_nome_ignora_caixa_espacos_e_apostrofos(dicionario: Dicionario) -> None:
    assert dicionario.ligar_nome("  côte d'ivoire[5] ").codigo == "CI"
    assert dicionario.ligar_nome("ALBANIA").codigo == "AL"
    assert dicionario.ligar_nome("KOSOVO").ignorado


# --------------------------------------------------------------------------- hash da observação
def test_hash_da_observacao_e_o_sha256_das_notas_normalizadas_unidas_por_quebra_de_linha() -> None:
    notas = ["90 days (business), 6 months (tourist).[3]", "Segunda\xa0nota"]
    esperado = hashlib.sha256(b"90 days (business), 6 months (tourist).\nSegunda nota").hexdigest()
    assert calcular_hash_observacao(notas) == esperado


def test_hash_da_observacao_depende_da_ordem_e_do_texto() -> None:
    assert calcular_hash_observacao(["a", "b"]) != calcular_hash_observacao(["b", "a"])
    assert calcular_hash_observacao(["a"]) != calcular_hash_observacao(["a."])


def test_hash_da_observacao_ignora_notas_em_branco() -> None:
    assert calcular_hash_observacao(["a", "", "  "]) == calcular_hash_observacao(["a"])
    assert calcular_hash_observacao([]) == hashlib.sha256(b"").hexdigest()
