"""Fixtures da coleta de vistos: banco semeado, Wikipédia falsa e um cenário com o serviço pronto.

O cenário monta a página a partir das 249 linhas da fixture real (a página de 1,5 MB), deixa o teste
alterar uma linha por vez (rótulo, nota, nome) e roda a coleta de verdade contra o banco de teste.
Nenhum teste acessa a rede nem um modelo de linguagem.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from farol.dominio import (
    ColetaVistos,
    EstadoDaRetencao,
    ItemParaRevisao,
    MudancaRetida,
    RequisitoVisto,
    Territorio,
    TipoDeItemParaRevisao,
    TipoTerritorio,
)
from farol.dominio.seed import carregar, executar
from farol.vistos import Dicionario, ResumoDaColetaDeVistos, ServicoDeColetaDeVistos, Tradutor
from farol.vistos.fonte import LinhaDaFonte, extrair_linhas

if TYPE_CHECKING:
    from tests.conftest import RelogioFalso, TradutorFalso, WikipediaFalsa

DADOS = Path(__file__).resolve().parents[4] / "dados"
IDADE_DA_EDICAO = timedelta(days=9)  # um artigo "calmo": editado há muito mais que 24 h


@pytest.fixture(scope="session")
def linhas_da_fonte(html_da_wikipedia: str) -> list[LinhaDaFonte]:
    return extrair_linhas(html_da_wikipedia)


@pytest.fixture
def semeado(sessao: Session) -> Session:
    """O banco só com os territórios do mapa (países e dependências): é o que a coleta precisa.

    O seed completo (postos, jurisdições) levaria 1,5 s por teste sem que a coleta o use.
    """
    dados = carregar(DADOS)
    dependencias = {d["codigo"]: d for d in dados.dependencias}
    paises = {c: n for c, n in dados.nomes_dos_paises.items() if c not in dependencias}
    sessao.add_all(
        Territorio(codigo=codigo, nome_pt=nome, tipo=TipoTerritorio.PAIS)
        for codigo, nome in paises.items()
    )
    sessao.flush()
    sessao.add_all(
        Territorio(
            codigo=codigo,
            nome_pt=d["nome_pt"],
            tipo=TipoTerritorio.DEPENDENCIA,
            soberano_codigo=d["soberano_codigo"],
        )
        for codigo, d in dependencias.items()
    )
    sessao.flush()
    return sessao


@pytest.fixture
def mapa_completo(sessao: Session) -> Session:
    """O seed completo do mapa (territórios, postos e jurisdições), como o de produção.

    Serve aos testes que dependem de `identidade_do_soberano` (Kosovo, Malvinas) e do cadastro
    real das dependências; os demais usam o `semeado`, bem mais leve.
    """
    executar(sessao, DADOS, datetime(2026, 10, 23, 12, 0, tzinfo=UTC))
    return sessao


class Cenario:
    """Uma Wikipédia editável e o serviço de coleta de vistos, ligados ao banco de teste."""

    def __init__(
        self,
        sessao: Session,
        wikipedia: "WikipediaFalsa",
        relogio: "RelogioFalso",
        tradutor: "TradutorFalso",
        linhas: list[LinhaDaFonte],
    ) -> None:
        self.sessao = sessao
        self.wikipedia = wikipedia
        self.relogio = relogio
        self.tradutor = tradutor
        self.linhas = list(linhas)
        self.dicionario: Dicionario | None = None  # nulo = os dicionários reais do pacote
        self.revisao = 1000

    # ----------------------------------------------------------- a página
    def _indice(self, nome: str) -> int:
        achados = [i for i, linha in enumerate(self.linhas) if linha.nome == nome]
        assert len(achados) == 1, f"esperava uma linha chamada {nome!r}, achei {len(achados)}"
        return achados[0]

    def linha(self, nome: str) -> LinhaDaFonte:
        return self.linhas[self._indice(nome)]

    def editar(self, nome: str, **campos: str) -> None:
        """Muda campos da linha (`rotulo`, `notas`, `permanencia`, `nome`)."""
        indice = self._indice(nome)
        self.linhas[indice] = replace(self.linhas[indice], **campos)

    def remover(self, *nomes: str) -> None:
        for nome in nomes:
            del self.linhas[self._indice(nome)]

    def acrescentar(self, linha: LinhaDaFonte) -> None:
        self.linhas.append(linha)

    def publicar(self, idade: timedelta = IDADE_DA_EDICAO) -> None:
        """Publica as linhas de agora como a página do artigo, editada há `idade`."""
        self.revisao += 1
        self.wikipedia.publicar_linhas(
            self.linhas, self.relogio.agora() - idade, revisao=self.revisao
        )

    # ----------------------------------------------------------- a coleta
    def servico(self, tradutor: Tradutor | bool | None = True) -> ServicoDeColetaDeVistos:
        """`tradutor=True` usa o falso do cenário; `None`/`False`, nenhum."""
        usado: Tradutor | None = self.tradutor if tradutor is True else (tradutor or None)
        return ServicoDeColetaDeVistos(
            self.sessao, self.wikipedia, self.relogio, usado, dicionario=self.dicionario
        )

    def coletar(
        self,
        *,
        agendada: bool = False,
        tradutor: Tradutor | bool | None = True,
        idade: timedelta = IDADE_DA_EDICAO,
    ) -> ResumoDaColetaDeVistos:
        """Publica a página de agora e roda uma coleta."""
        self.publicar(idade)
        return self.servico(tradutor).coletar(agendada=agendada)

    def semana_seguinte(self) -> None:
        self.relogio.avancar(days=7)

    # ----------------------------------------------------------- o que ficou no banco
    def requisito(self, codigo: str) -> RequisitoVisto | None:
        return self.sessao.get(RequisitoVisto, codigo)

    def requisitos(self) -> dict[str, RequisitoVisto]:
        consulta = select(RequisitoVisto).order_by(RequisitoVisto.territorio_codigo)
        return {r.territorio_codigo: r for r in self.sessao.scalars(consulta)}

    def foto(self) -> dict[str, tuple[Any, ...]]:
        """Tudo o que o site mostraria, por código: serve para provar que nada mudou."""
        return {
            codigo: (
                r.categoria,
                r.motivo_outra,
                r.rotulo_original,
                r.hash_fonte,
                r.aceita_rg,
                r.varia_conforme_motivo,
                r.permanencia_tipo,
                r.permanencia_texto,
                r.observacoes,
                r.lido_em,
                r.coleta_id,
            )
            for codigo, r in self.requisitos().items()
        }

    def coletas(self) -> list[ColetaVistos]:
        consulta = select(ColetaVistos).order_by(ColetaVistos.id)
        return list(self.sessao.scalars(consulta))

    def mudancas(
        self, codigo: str | None = None, estado: EstadoDaRetencao | None = None
    ) -> list[MudancaRetida]:
        consulta = select(MudancaRetida).order_by(MudancaRetida.id)
        if codigo is not None:
            consulta = consulta.where(MudancaRetida.territorio_codigo == codigo)
        if estado is not None:
            consulta = consulta.where(MudancaRetida.estado == estado)
        return list(self.sessao.scalars(consulta))

    def itens(self, tipo: TipoDeItemParaRevisao | None = None) -> list[ItemParaRevisao]:
        consulta = select(ItemParaRevisao).order_by(ItemParaRevisao.id)
        if tipo is not None:
            consulta = consulta.where(ItemParaRevisao.tipo == tipo)
        return list(self.sessao.scalars(consulta))


@pytest.fixture
def cenario(
    semeado: Session,
    wikipedia: "WikipediaFalsa",
    relogio: "RelogioFalso",
    tradutor_falso: "TradutorFalso",
    linhas_da_fonte: list[LinhaDaFonte],
) -> Cenario:
    return Cenario(semeado, wikipedia, relogio, tradutor_falso, linhas_da_fonte)


@pytest.fixture
def cenario_completo(
    mapa_completo: Session,
    wikipedia: "WikipediaFalsa",
    relogio: "RelogioFalso",
    tradutor_falso: "TradutorFalso",
    linhas_da_fonte: list[LinhaDaFonte],
) -> Cenario:
    """O mesmo cenário, sobre o seed completo do mapa."""
    return Cenario(mapa_completo, wikipedia, relogio, tradutor_falso, linhas_da_fonte)
