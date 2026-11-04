"""`chat/artigos.yaml`: todo nome que o chat mostra tem a forma certa com artigo e preposição."""

from pathlib import Path

import pytest
import yaml

from farol.chat import textos
from farol.chat.entendimento import APELIDOS
from farol.dominio.seed import carregar
from farol.vistos.leitura import NOMES_DA_001

DADOS = Path(__file__).resolve().parents[4] / "dados"


def nomes_que_o_chat_mostra() -> set[str]:
    dados = carregar(DADOS)
    nomes = set(dados.nomes_dos_paises.values())
    for dependencia in dados.dependencias:
        nomes |= {dependencia["nome_pt"], dependencia.get("rotulo_busca") or dependencia["nome_pt"]}
    ambiguos = yaml.safe_load(APELIDOS.read_text(encoding="utf-8"))["ambiguos"]
    return nomes | set(NOMES_DA_001.values()) | set(ambiguos)


def test_todo_nome_tem_artigo_decidido() -> None:
    """Território novo sem entrada sairia sem artigo, e "para Itália" passaria despercebido."""
    faltando = {n.split(" (")[0] for n in nomes_que_o_chat_mostra()} - set(textos.artigos())
    assert not faltando


def test_nenhum_nome_em_dois_grupos() -> None:
    grupos = yaml.safe_load(textos.ARTIGOS.read_text(encoding="utf-8"))
    nomes = [nome for grupo in grupos.values() for nome in grupo]
    assert len(nomes) == len(set(nomes))


@pytest.mark.parametrize(
    ("nome", "para", "de"),
    [
        ("Afeganistão", "para o Afeganistão", "do Afeganistão"),
        ("Kosovo", "para o Kosovo", "do Kosovo"),
        ("França", "para a França", "da França"),
        ("Guiana Francesa (França)", "para a Guiana Francesa (França)",
         "da Guiana Francesa (França)"),
        ("Estados Unidos", "para os Estados Unidos", "dos Estados Unidos"),
        ("Países Baixos", "para os Países Baixos", "dos Países Baixos"),
        ("Filipinas", "para as Filipinas", "das Filipinas"),
        ("Ilhas Malvinas", "para as Ilhas Malvinas", "das Ilhas Malvinas"),
        ("Portugal", "para Portugal", "de Portugal"),
        ("Cuba", "para Cuba", "de Cuba"),
    ],
)  # fmt: skip
def test_forma_do_nome_nas_frases(nome: str, para: str, de: str) -> None:
    assert f"visto {para}." in textos.frase_do_visto("visto_exigido", nome, False)
    assert f"visto {de} não" in textos.frase_do_visto("outra_situacao", nome, False)
    assert textos.frase_do_alerta("nao_viajar", nome, False, True).startswith(f"P{para[1:]},")
    assert f"alerta {de} não" in textos.frase_do_alerta("nao_verificado", nome, False, True)


def test_um_pais_por_vez_com_artigos() -> None:
    assert textos.um_pais_por_vez(["França", "Portugal", "Estados Unidos"]).startswith(
        "Entendi que você perguntou sobre a França, Portugal e os Estados Unidos."
    )


def test_um_pais_por_vez_com_kosovo_pelo_rotulo() -> None:
    assert textos.um_pais_por_vez(["Sérvia", "Kosovo (Sérvia)"]).startswith(
        "Entendi que você perguntou sobre a Sérvia e o Kosovo (Sérvia)."
    )


def test_qual_dos_paises_fica_sem_artigo() -> None:
    """São opções para copiar na próxima pergunta, não uma frase."""
    assert textos.qual_dos_paises(["Coreia do Sul", "Coreia do Norte"]).startswith(
        "Qual deles você quer saber: Coreia do Sul ou Coreia do Norte?"
    )
