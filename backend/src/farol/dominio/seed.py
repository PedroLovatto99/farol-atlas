"""Seed idempotente: países, dependências, postos, responsáveis e fonte dos dados.

Lê, da pasta `dados/`:
  - postos/postos_brasileiros.csv e postos/jurisdicao_cumulativa.csv  (países e postos)
  - postos/fonte.yaml                                                  (fonte e data dos postos)
  - territorios/territorios.json  (dependências e ícones; gerado por scripts/gerar_geometria.py)
  - territorios/observacoes.yaml                                       (observações especiais)

Rode com `python -m farol.dominio.seed`. `--hashes` mostra o SHA-256 dos CSVs de postos, para
colar no `postos/fonte.yaml`.
"""

import csv
import hashlib
import json
import os
import sys
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from farol.dominio.enums import TipoPosto, TipoTerritorio
from farol.dominio.modelos import FonteDados, Posto, Territorio
from farol.infra import abrir_sessao, obter_configuracoes

CSV_POSTOS = "postos_brasileiros.csv"
CSV_JURISDICAO = "jurisdicao_cumulativa.csv"
ALIAS_DE_CIDADE = {"cambera": "camberra"}  # a lista oficial grafa "Cambera"
ORDEM_DE_TIPO = list(TipoPosto)


class ErroDeSeed(Exception):
    """Os dados do seed não batem entre si; é melhor falhar do que semear dados errados."""


def hash_do_arquivo(caminho: Path) -> str:
    """SHA-256 do arquivo com quebras de linha normalizadas (igual em Windows e Linux)."""
    conteudo = caminho.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(conteudo).hexdigest()


@dataclass(frozen=True)
class DadosSeed:
    nomes_dos_paises: dict[str, str]
    postos: list[dict[str, str]]
    jurisdicao: list[dict[str, str]]
    dependencias: list[dict[str, Any]]
    icones: dict[str, tuple[float, float]]
    observacoes: dict[str, Any]
    fonte: dict[str, Any]


def _ler_csv(caminho: Path) -> list[dict[str, str]]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def _ler_yaml(caminho: Path) -> dict[str, Any]:
    conteudo = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    if not isinstance(conteudo, dict):
        raise ErroDeSeed(f"{caminho} deveria ser um mapa YAML")
    return conteudo


def carregar(diretorio: Path) -> DadosSeed:
    postos = _ler_csv(diretorio / "postos" / CSV_POSTOS)
    jurisdicao = _ler_csv(diretorio / "postos" / CSV_JURISDICAO)
    nomes = {"BR": "Brasil"}
    for linha in postos + jurisdicao:
        nomes[linha["pais_iso"]] = linha["pais"]
    geometria = json.loads((diretorio / "territorios" / "territorios.json").read_text("utf-8"))
    return DadosSeed(
        nomes_dos_paises=nomes,
        postos=postos,
        jurisdicao=jurisdicao,
        dependencias=geometria["dependencias"],
        icones={
            i["codigo"]: (i["latitude"], i["longitude"]) for i in geometria["icones_sem_posto"]
        },
        observacoes=_ler_yaml(diretorio / "territorios" / "observacoes.yaml"),
        fonte=_ler_yaml(diretorio / "postos" / "fonte.yaml"),
    )


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def _upsert[M](sessao: Session, modelo: type[M], pk: object, /, **campos: Any) -> M:
    objeto = sessao.get(modelo, pk)
    if objeto is None:
        objeto = modelo(**campos)
        sessao.add(objeto)
    else:
        for nome, valor in campos.items():
            setattr(objeto, nome, valor)
    return objeto


def observacao_da_dependencia(codigo: str, soberano: str, dados: DadosSeed) -> str:
    """Observação do painel: a própria do território ou a padrão, com a preposição do soberano."""
    especial: dict[str, Any] = dados.observacoes.get("territorios", {}).get(codigo, {})
    if especial.get("observacao"):
        return " ".join(str(especial["observacao"]).split())
    formas: dict[str, str] = dados.observacoes["soberanos"]
    if soberano not in formas:
        raise ErroDeSeed(
            f"dependência {codigo}: falta a forma com preposição do soberano {soberano!r} "
            "em observacoes.yaml (soberanos)"
        )
    modelo: str = dados.observacoes["dependencia_padrao"]
    return " ".join(modelo.format(do_soberano=formas[soberano]).split())


def _semear_territorios(sessao: Session, dados: DadosSeed) -> None:
    dependencias = {d["codigo"]: d for d in dados.dependencias}
    paises = {c: n for c, n in dados.nomes_dos_paises.items() if c not in dependencias}

    for codigo, nome in paises.items():
        _upsert(
            sessao,
            Territorio,
            codigo,
            codigo=codigo,
            nome_pt=nome,
            tipo=TipoTerritorio.PAIS,
            soberano_codigo=None,
            na_lista_itamaraty=True,
            codigo_bandeira=codigo,
            identidade_do_soberano=False,
        )
    sessao.flush()

    especiais: dict[str, Any] = dados.observacoes.get("territorios", {})
    for codigo, dep in dependencias.items():
        soberano = dep["soberano_codigo"]
        if soberano not in paises:
            raise ErroDeSeed(f"dependência {codigo}: soberano {soberano!r} não é um país conhecido")
        especial: dict[str, Any] = especiais.get(codigo, {})
        _upsert(
            sessao,
            Territorio,
            codigo,
            codigo=codigo,
            nome_pt=dep["nome_pt"],
            tipo=TipoTerritorio.DEPENDENCIA,
            soberano_codigo=soberano,
            na_lista_itamaraty=dep["na_lista_itamaraty"],
            codigo_bandeira=dep["codigo_bandeira"],
            identidade_do_soberano=dep["identidade_do_soberano"],
            rotulo_busca=especial.get("rotulo_busca"),
            termos_busca=list(especial.get("termos_busca", [])),
            observacao=observacao_da_dependencia(codigo, soberano, dados),
        )
    sessao.flush()


def _semear_postos(sessao: Session, dados: DadosSeed) -> dict[str, list[Posto]]:
    """Grava os postos e devolve-os agrupados pela cidade normalizada."""
    por_cidade: dict[str, list[Posto]] = {}
    for linha in dados.postos:
        codigo = linha["pais_iso"]
        if sessao.get(Territorio, codigo) is None:
            raise ErroDeSeed(f"posto {linha['id']}: país {codigo!r} não está em territorio")
        posto = _upsert(
            sessao,
            Posto,
            int(linha["id"]),
            id=int(linha["id"]),
            territorio_codigo=codigo,
            cidade=linha["cidade"],
            tipo=TipoPosto(linha["tipo"]),
            latitude=Decimal(linha["latitude"]),
            longitude=Decimal(linha["longitude"]),
            na_lista_oficial=linha["na_lista_oficial"] == "sim",
            observacao_origem=linha["observacao"] or None,
        )
        por_cidade.setdefault(_normalizar(linha["cidade"]), []).append(posto)
    sessao.flush()
    return por_cidade


def _escolher_responsavel(candidatos: list[Posto]) -> Posto:
    """Prefere o posto que não é o da Santa Sé, depois a embaixada, depois o menor id."""
    return min(
        candidatos,
        key=lambda p: (p.territorio_codigo == "VA", ORDEM_DE_TIPO.index(p.tipo), p.id),
    )


def _semear_paises_sem_posto(
    sessao: Session, dados: DadosSeed, por_cidade: dict[str, list[Posto]]
) -> None:
    for linha in dados.jurisdicao:
        codigo = linha["pais_iso"]
        territorio = sessao.get(Territorio, codigo)
        if territorio is None:
            raise ErroDeSeed(f"país sem posto {codigo!r} não está em territorio")
        responsavel = linha["posto_responsavel"]
        if responsavel.startswith("("):  # ex.: Líbia, sem posto indicado na lista oficial
            territorio.sem_posto_indicado = True
            territorio.posto_responsavel_id = None
        else:
            cidade = ALIAS_DE_CIDADE.get(_normalizar(responsavel), _normalizar(responsavel))
            candidatos = por_cidade.get(cidade)
            if not candidatos:
                raise ErroDeSeed(
                    f"posto responsável {responsavel!r} (de {codigo}) não encontrado nos postos"
                )
            territorio.sem_posto_indicado = False
            territorio.posto_responsavel_id = _escolher_responsavel(candidatos).id
        if codigo not in dados.icones:
            raise ErroDeSeed(
                f"país sem posto {codigo!r} não tem ponto de ícone no territorios.json"
            )
        latitude, longitude = dados.icones[codigo]
        territorio.icone_latitude = Decimal(str(latitude))
        territorio.icone_longitude = Decimal(str(longitude))
    sessao.flush()


def _semear_fonte(sessao: Session, dados: DadosSeed, agora: datetime) -> None:
    fonte = dados.fonte
    _upsert(
        sessao,
        FonteDados,
        fonte["chave"],
        chave=fonte["chave"],
        fontes=fonte["fontes"],
        conferido_em=fonte["conferido_em"],
        carregado_em=agora,
    )
    sessao.flush()


def executar(sessao: Session, diretorio: Path, agora: datetime) -> None:
    """Semeia (ou atualiza) tudo; pode rodar quantas vezes quiser."""
    dados = carregar(diretorio)
    _semear_territorios(sessao, dados)
    por_cidade = _semear_postos(sessao, dados)
    _semear_paises_sem_posto(sessao, dados, por_cidade)
    _semear_fonte(sessao, dados, agora)


def main(argumentos: list[str]) -> int:
    if "--hashes" in argumentos:  # não precisa de banco nem de DATABASE_URL
        diretorio = Path(os.environ.get("DIRETORIO_DADOS", "../dados"))
        for nome in (CSV_POSTOS, CSV_JURISDICAO):
            print(f"  {nome}: {hash_do_arquivo(diretorio / 'postos' / nome)}")
        return 0
    diretorio = obter_configuracoes().diretorio_dados
    with abrir_sessao() as sessao:
        executar(sessao, diretorio, datetime.now(UTC))
    print(f"Seed concluído a partir de {diretorio.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
