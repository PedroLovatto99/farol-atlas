"""`chat/apelidos.yaml`: cada entrada leva ao território certo e os códigos existem no seed."""

from pathlib import Path

import pytest

from farol.chat.entendimento import (
    APELIDOS,
    Apelidos,
    carregar_apelidos,
    entender,
    montar_vocabulario,
    normalizar,
)
from farol.dominio.seed import carregar

DADOS = Path(__file__).resolve().parents[4] / "dados"


class Territorio:
    def __init__(self, codigo: str, nome: str) -> None:
        self.codigo = codigo
        self.nome = nome
        self.rotulo_busca = nome
        self.termos_busca: tuple[str, ...] = ()
        self.identidade_do_soberano = False


@pytest.fixture(scope="module")
def territorios() -> list[Territorio]:
    """Os territórios do seed (países e dependências), com o nome que o site mostra."""
    dados = carregar(DADOS)
    nomes = dados.nomes_dos_paises | {d["codigo"]: d["nome_pt"] for d in dados.dependencias}
    return [Territorio(c, n) for c, n in nomes.items()]


@pytest.fixture(scope="module")
def apelidos(territorios: list[Territorio]) -> Apelidos:
    return carregar_apelidos({t.codigo for t in territorios})


@pytest.mark.parametrize(
    ("termo", "codigo"),
    [
        ("EUA", "US"),
        ("Estados Unidos da América", "US"),
        ("Inglaterra", "GB"),
        ("Escócia", "GB"),
        ("Holanda", "NL"),
        ("República Democrática do Congo", "CD"),
        ("República do Congo", "CG"),
        ("Tchéquia", "CZ"),
        ("Eslováquia", "SK"),
        ("Essuatíni", "SZ"),
        ("Birmânia", "MM"),
        ("Bielorrússia", "BY"),
        ("Macedônia do Norte", "MK"),
        ("Emirados", "AE"),
        ("Dubai", "AE"),
        ("Irlanda do Norte", "GB"),
        ("Novo México", "US"),
        ("Nova Escócia", "CA"),
        ("Geórgia (país)", "GE"),
        ("o país Geórgia", "GE"),
        ("Geórgia (estado americano)", "US"),
        ("o estado da Geórgia", "US"),
        ("Geórgia EUA", "US"),
        ("Geórgia nos EUA", "US"),
    ],
)
def test_cada_apelido(
    territorios: list[Territorio], apelidos: Apelidos, termo: str, codigo: str
) -> None:
    vocabulario = montar_vocabulario(territorios, apelidos)
    assert [p.codigos for p in entender(f"visto para {termo}", vocabulario).paises] == [(codigo,)]


@pytest.mark.parametrize(
    ("termo", "codigos"),
    [
        ("Congo", ("CG", "CD")),
        ("Guiné", ("GN", "GW", "GQ")),
        ("Coreia", ("KR", "KP")),
        ("Geórgia", ("GE", "US")),
    ],
)
def test_cada_ambiguo(
    territorios: list[Territorio], apelidos: Apelidos, termo: str, codigos: tuple[str, ...]
) -> None:
    vocabulario = montar_vocabulario(territorios, apelidos)
    assert [p.codigos for p in entender(f"e o {termo}?", vocabulario).paises] == [codigos]


def test_todas_as_entradas_do_yaml_tem_caso(apelidos: Apelidos) -> None:
    """Quem acrescentar um apelido acrescenta o caso acima."""
    casos = {
        normalizar(t)
        for t in (
            "EUA", "Estados Unidos da América", "Inglaterra", "Escócia", "Holanda",
            "República Democrática do Congo", "República do Congo", "Tchéquia", "Eslováquia",
            "Essuatíni", "Birmânia", "Bielorrússia", "Macedônia do Norte", "Emirados", "Dubai",
            "Irlanda do Norte", "Novo México", "Nova Escócia", "Geórgia país", "país Geórgia",
            "Geórgia estado americano", "estado da Geórgia", "Geórgia EUA", "Geórgia nos EUA",
        )
    }  # fmt: skip
    assert set(apelidos.apelidos) == casos
    assert set(apelidos.ambiguos) == {"Congo", "Guiné", "Coreia", "Geórgia"}


def test_as_opcoes_da_georgia_levam_a_uma_resposta(
    territorios: list[Territorio], apelidos: Apelidos
) -> None:
    """Repetir a opção mostrada resolve: a pergunta de volta não entra em laço."""
    vocabulario = montar_vocabulario(territorios, apelidos)
    (pais,) = entender("visto para a Geórgia", vocabulario).paises
    assert pais.opcoes == ("Geórgia (país)", "Geórgia (estado americano)")
    respostas = [entender(opcao, vocabulario).paises[0].codigos for opcao in pais.opcoes]
    assert respostas == [("GE",), ("US",)]


def test_codigo_fora_da_lista_falha_com_erro_claro(tmp_path: Path) -> None:
    arquivo = tmp_path / "apelidos.yaml"
    arquivo.write_text("apelidos:\n  terra media: ZZ\nambiguos: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"ZZ.*terra media"):
        carregar_apelidos({"JP"}, arquivo)


def test_ambiguo_com_codigo_fora_da_lista_tambem_falha(tmp_path: Path) -> None:
    arquivo = tmp_path / "apelidos.yaml"
    arquivo.write_text("apelidos: {}\nambiguos:\n  Congo: [CG, ZZ]\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"ZZ.*Congo"):
        carregar_apelidos({"CG"}, arquivo)


def test_o_arquivo_padrao_e_o_do_pacote() -> None:
    assert APELIDOS.name == "apelidos.yaml"
    assert APELIDOS.parent.name == "chat"
