"""Gera o rascunho de `nomes.yaml` (nome da Wikipédia -> código do mapa) lendo só a fixture, sem rede.

Uso (de dentro de `backend/`, onde o grupo `geo` com o pycountry está instalado):

    uv run python ../ferramentas/gerar_nomes_vistos.py                  # escreve no terminal
    uv run python ../ferramentas/gerar_nomes_vistos.py --saida ARQUIVO  # grava em ARQUIVO
    uv run python ../ferramentas/gerar_nomes_vistos.py --fixture OUTRA_PAGINA.html

O pycountry liga a maioria dos nomes aos códigos ISO; os APELIDOS abaixo (feitos à mão) cobrem os
que ele não liga, e IGNORAR guarda os nomes lidos e descartados de propósito, cada um com o motivo.
O resultado é um ponto de partida: revise e confira com `uv run pytest tests/unidade/vistos`.
O pycountry não vai para produção (por isso o `nomes.yaml` traz todos os nomes) e este script
também não: ele só roda no desenvolvimento, nunca acessa a internet e não toca em nenhum outro arquivo.
"""

import argparse
import json
import sys
from pathlib import Path

import pycountry

from farol.vistos.fonte import LinhaDaFonte, extrair_linhas

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE_PADRAO = (
    RAIZ / "backend" / "tests" / "fixtures" / "wikipedia" / "visa_requirements_for_brazilian_citizens.html"
)

# Nomes que o pycountry não liga sozinho (research.md 3.4); São Tomé só por causa do acento
APELIDOS = {
    "Brunei": "BN",
    "Cape Verde": "CV",
    "Democratic Republic of the Congo": "CD",
    "Micronesia": "FM",
    "Russia": "RU",
    "Turkey": "TR",
    "Vatican City": "VA",
    "United Kingdom and Crown dependencies": "GB",
    "Palestine": "PS",
    "Macau": "MO",
    "Saint Martin": "MF",
    "Sint Maarten": "SX",
    "Pitcairn Islands": "PN",
    "Saint Helena": "SH",
    "Ascension Island": "SH",
    "Tristan da Cunha": "SH",
    "Clipperton Island": "CLP",
    "U.S. Virgin Islands": "VI",
    "São Tomé and Príncipe": "ST",
    # Kosovo e Malvinas: a identidade do painel é a do soberano (001), mas a regra de entrada é a
    # da linha própria da fonte (esclarecimento de 28/10/2026, research.md 3.4a)
    "Kosovo": "XK",
    "Falkland Islands": "FK",
}

_SEM_DESENHO = "Sem desenho próprio no mapa"
_NAO_RECONHECIDO = "Território não reconhecido, sem desenho no mapa"
_FRANCA = "Parte da França no mapa, sem desenho próprio"
_PAISES_BAIXOS = "Parte dos Países Baixos no mapa, sem desenho próprio"
IGNORAR = {
    "Abkhazia": _NAO_RECONHECIDO,
    "South Ossetia": _NAO_RECONHECIDO,
    "Northern Cyprus": _NAO_RECONHECIDO,
    "Somaliland": _NAO_RECONHECIDO,
    "Transnistria": _NAO_RECONHECIDO,
    "Sahrawi Arab Democratic Republic": (
        "Área neutra (Saara Ocidental): não abre painel nem recebe visto"
    ),
    "Guadeloupe": _FRANCA,
    "Martinique": _FRANCA,
    "Mayotte": _FRANCA,
    "Réunion": _FRANCA,
    "Bonaire": _PAISES_BAIXOS,
    "Sint Eustatius": _PAISES_BAIXOS,
    "Saba": _PAISES_BAIXOS,
    "Tokelau": _SEM_DESENHO,
    "Jan Mayen": _SEM_DESENHO,
    "Svalbard": _SEM_DESENHO,
    "Akrotiri and Dhekelia": _SEM_DESENHO,
    "British Indian Ocean Territory": _SEM_DESENHO,
    "South Georgia and the South Sandwich Islands": _SEM_DESENHO,
}

TABELAS = (
    ("principal", "Tabela principal (países)"),
    ("nao_reconhecidos", "Países não reconhecidos ou parcialmente reconhecidos"),
    ("territorios", "Dependências e territórios autônomos"),
)

CABECALHO = """\
# Nomes da coluna de país/território do artigo da Wikipédia -> código do mapa (ISO 3166-1
# alfa-2; os que não têm ISO usam o código do mapa, como CLP).
# Formato: specs/002-visto-brasileiros/contracts/dicionario-de-rotulos.md. Levantamento aprovado
# em 28/10/2026 (specs/002-visto-brasileiros/research.md, seção 3.4).
#
# Traz TODOS os nomes da fonte, porque o pycountry não vai para produção. Os códigos vão entre
# aspas: o YAML lê NO (Noruega) sem aspas como falso. Vários nomes podem ter o mesmo código
# (Santa Helena, Ascensão e Tristão da Cunha -> SH): as linhas viram partes de um rótulo
# combinado. Nome novo na fonte vai para a lista de revisão do dono (`vistos pendentes`), nunca
# é descartado em silêncio.

nomes:
"""

RODAPE_DE_IGNORAR = """
# Nomes lidos e descartados de propósito, cada um com o motivo. Para um nome novo, o dono usa
# `vistos ignorar-nome "<nome>" --motivo "<texto>"`.
ignorar:
"""


def _texto(valor: str) -> str:
    """Escalar YAML entre aspas duplas (o JSON é um subconjunto válido do YAML)."""
    return json.dumps(valor, ensure_ascii=False)


def ligar(nome: str) -> str:
    if nome in APELIDOS:
        return APELIDOS[nome]
    return str(pycountry.countries.lookup(nome).alpha_2)


def montar(linhas: list[LinhaDaFonte]) -> str:
    nomes = {linha.nome: ligar(linha.nome) for linha in linhas if linha.nome not in IGNORAR}
    ausentes = sorted(set(IGNORAR) - {linha.nome for linha in linhas})
    if ausentes:
        raise SystemExit(f"nomes ignorados que não estão na fixture: {ausentes}")

    saida = [CABECALHO]
    for tabela, titulo in TABELAS:
        saida.append(f"  # {titulo}\n")
        for linha in linhas:
            if linha.tabela == tabela and linha.nome in nomes:
                saida.append(f"  {_texto(linha.nome)}: {_texto(nomes[linha.nome])}\n")
    saida.append(RODAPE_DE_IGNORAR)
    for nome, motivo in IGNORAR.items():
        saida.append(f"  {_texto(nome)}: {_texto(motivo)}\n")
    return "".join(saida)


def main(argumentos: list[str]) -> int:
    analisador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analisador.add_argument("--fixture", type=Path, default=FIXTURE_PADRAO)
    analisador.add_argument("--saida", type=Path, help="arquivo a gravar (padrão: o terminal)")
    opcoes = analisador.parse_args(argumentos)

    html = opcoes.fixture.read_text(encoding="utf-8")
    texto = montar(extrair_linhas(html))
    if opcoes.saida is None:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        sys.stdout.write(texto)
    else:
        opcoes.saida.write_text(texto, encoding="utf-8", newline="\n")
        print(f"gravado em {opcoes.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
