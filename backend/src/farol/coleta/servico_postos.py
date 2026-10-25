"""Coleta mensal de postos: endereço e telefone de plantão, de melhor esforço (research.md, R1).

Fluxo:

1. Lê a tabela de repartições do Portal Consular: país → posto que o atende, com o link do posto.
2. Liga cada link a um posto do banco pela cidade (e, se a cidade tem mais de um posto, pelo
   tipo que o link sugere e pelo país da linha). Links que não se ligam a um posto são ignorados.
3. Para cada posto, baixa a página inicial (os links da tabela redirecionam para `www.gov.br`),
   registra a página final em `url_gov_br` e procura o contato nela e em até 3 subpáginas do
   próprio posto (emergências, fale conosco...), parando quando já achou os dois.
4. Grava endereço, telefone, data e fonte **juntos**: o que não foi achado agora fica nulo. Se
   nada foi achado, o contato que já existia é mantido (com a data em que foi lido de verdade).

Mesmas regras de coleta responsável dos alertas: o cliente educado consulta o robots.txt de cada
host, espera entre os pedidos e, se for bloqueado, a coleta para e o motivo é gravado. A coleta é
completa se nenhum bloqueio ocorreu e pelo menos 70% das páginas iniciais foram lidas.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from farol.coleta.cliente_educado import Pagina
from farol.coleta.extratores import (
    LinhaDeReparticao,
    extrair_contato,
    extrair_reparticoes,
    links_de_contato,
)
from farol.coleta.servico_alertas import MINIMO_LIDO, Baixador
from farol.coleta.texto import chave_de_comparacao
from farol.dominio import (
    ExecucaoColeta,
    ExecucaoRepositorio,
    Posto,
    PostoRepositorio,
    TerritorioRepositorio,
    TipoExecucao,
    TipoPosto,
)
from farol.infra import Relogio, obter_logger

URL_REPARTICOES = (
    "https://www.gov.br/mre/pt-br/assuntos/portal-consular/reparticoes-consulares-do-brasil"
)
MAXIMO_DE_SUBPAGINAS = 3

# A tabela do gov.br escreve algumas cidades de outro jeito que os CSVs do seed
APELIDOS_DE_CIDADE = {
    "cambera": "camberra",
    "cingapura": "singapura",
    "guatemala": "cidade da guatemala",
}
_TIPOS_DE_CONSULADO = frozenset(
    {TipoPosto.CONSULADO_GERAL, TipoPosto.CONSULADO, TipoPosto.VICE_CONSULADO}
)

_log = obter_logger("farol.coleta")


@dataclass(frozen=True)
class ResultadoDaColetaDePostos:
    execucao_id: int
    completa: bool
    motivo_interrupcao: str | None
    paginas_esperadas: int  # postos do banco que a tabela liga a um link
    paginas_lidas: int  # destes, quantos tiveram a página inicial lida
    postos_com_endereco: int  # cobertura no banco inteiro, depois desta coleta
    postos_com_telefone: int


@dataclass(frozen=True)
class _Contato:
    endereco: str | None
    telefone: str | None
    fonte_url: str


def _tipos_sugeridos(url: str) -> frozenset[TipoPosto] | None:
    """O tipo de posto que o link sugere: `cgparis.itamaraty...` e `.../consulado-...` são
    consulados; `.../embaixada-...` é embaixada. Sem pista, nenhum."""
    partes = urlsplit(url)
    host = partes.netloc.lower()
    caminho = partes.path.lower()
    if host.split(".")[0].startswith("cg") or "consulado" in host or "consulado" in caminho:
        return _TIPOS_DE_CONSULADO
    if "embaixada" in host or "embaixada" in caminho:
        return frozenset({TipoPosto.EMBAIXADA})
    return None


def _desempatar(candidatos: Sequence[Posto], url: str, codigo_do_pais: str | None) -> Posto | None:
    if len(candidatos) <= 1:
        return candidatos[0] if candidatos else None
    tipos = _tipos_sugeridos(url)
    if tipos is not None:
        candidatos = [p for p in candidatos if p.tipo in tipos]
    if len(candidatos) > 1 and codigo_do_pais is not None:
        candidatos = [p for p in candidatos if p.territorio_codigo == codigo_do_pais]
    return candidatos[0] if len(candidatos) == 1 else None


def associar_postos(
    linhas: Sequence[LinhaDeReparticao],
    postos: Sequence[Posto],
    codigos_por_nome_de_pais: Mapping[str, str],
) -> dict[str, int]:
    """URL do link do posto → id do posto do banco, só para o que se liga a um posto sem dúvida.

    `codigos_por_nome_de_pais` usa o nome já passado por `_chave`.
    """
    por_cidade: dict[str, list[Posto]] = {}
    for posto in postos:
        por_cidade.setdefault(chave_de_comparacao(posto.cidade), []).append(posto)

    associados: dict[str, int] = {}
    for linha in linhas:
        codigo_do_pais = codigos_por_nome_de_pais.get(chave_de_comparacao(linha.pais))
        for link in linha.postos:
            if link.url in associados:
                continue
            cidade = chave_de_comparacao(link.nome)
            candidatos = por_cidade.get(APELIDOS_DE_CIDADE.get(cidade, cidade), [])
            escolhido = _desempatar(candidatos, link.url, codigo_do_pais)
            if escolhido is not None:
                associados[link.url] = escolhido.id
    return associados


class ServicoDeColetaDePostos:
    def __init__(
        self,
        sessao: Session,
        cliente: Baixador,
        relogio: Relogio,
        *,
        url_da_tabela: str = URL_REPARTICOES,
    ) -> None:
        self._sessao = sessao
        self._cliente = cliente
        self._relogio = relogio
        self._url_da_tabela = url_da_tabela
        self._postos = PostoRepositorio(sessao)
        self._territorios = TerritorioRepositorio(sessao)
        self._execucoes = ExecucaoRepositorio(sessao)

    def coletar(self) -> ResultadoDaColetaDePostos:
        execucao = ExecucaoColeta(tipo=TipoExecucao.POSTOS, iniciada_em=self._relogio.agora())
        self._execucoes.adicionar(execucao)
        self._sessao.flush()

        associados, motivo = self._ler_tabela()
        lidas = 0
        if motivo is None:
            lidas = self._ler_postos(associados)
        esperadas = len(associados)

        interrompida = self._cliente.interrompido_por
        suficiente = esperadas >= 1 and lidas * MINIMO_LIDO[1] >= esperadas * MINIMO_LIDO[0]
        if motivo is None and interrompida is not None:
            motivo = interrompida
        if motivo is None and not suficiente:
            motivo = f"só {lidas} de {esperadas} páginas lidas (mínimo de 70%)"
        completa = motivo is None

        com_endereco, com_telefone = self._postos.contar_com_contato()
        execucao.finalizada_em = self._relogio.agora()
        execucao.paginas_esperadas = esperadas
        execucao.paginas_lidas = lidas
        execucao.lista_lida_inteira = esperadas > 0
        execucao.completa = completa
        execucao.motivo_interrupcao = motivo
        execucao.postos_com_endereco = com_endereco
        execucao.postos_com_telefone = com_telefone
        self._sessao.flush()

        _log.info(
            "coleta de postos %s: %d de %d páginas lidas; %d postos com endereço e %d com "
            "telefone%s",
            "completa" if completa else "INCOMPLETA",
            lidas,
            esperadas,
            com_endereco,
            com_telefone,
            "" if completa else f" ({motivo})",
        )
        return ResultadoDaColetaDePostos(
            execucao_id=execucao.id,
            completa=completa,
            motivo_interrupcao=motivo,
            paginas_esperadas=esperadas,
            paginas_lidas=lidas,
            postos_com_endereco=com_endereco,
            postos_com_telefone=com_telefone,
        )

    # ------------------------------------------------------------------ tabela
    def _ler_tabela(self) -> tuple[dict[str, int], str | None]:
        """Links dos postos ligados ao banco e, se não deu, o motivo."""
        tabela = self._cliente.baixar(self._url_da_tabela)
        if not tabela.ok:
            return {}, self._cliente.interrompido_por or (
                f"não leu a tabela de repartições ({tabela.motivo})"
            )
        linhas = extrair_reparticoes(tabela.html, tabela.destino)
        if not linhas:
            return {}, "tabela de repartições em formato inesperado"
        paises = {
            chave_de_comparacao(t.nome_pt): t.codigo for t in self._territorios.listar_todos()
        }
        associados = associar_postos(linhas, self._postos.listar_todos(), paises)
        if not associados:
            return {}, "nenhum posto do banco aparece na tabela de repartições"
        return associados, None

    # ------------------------------------------------------------------ postos
    def _ler_postos(self, associados: Mapping[str, int]) -> int:
        lidas = 0
        for url, posto_id in associados.items():
            if self._cliente.interrompido_por is not None:
                break  # bloqueio ou verificação humana: nunca insiste
            posto = self._postos.obter(posto_id)
            if posto is None:
                continue
            inicial = self._cliente.baixar(url)
            if not inicial.ok:
                _log.warning("página do posto não lida (%s): %s", inicial.motivo, url)
                continue
            lidas += 1
            posto.url_gov_br = inicial.destino
            contato = self._procurar_contato(inicial)
            if contato is not None:
                self._postos.registrar_contato(
                    posto,
                    endereco=contato.endereco,
                    telefone_plantao=contato.telefone,
                    coletado_em=self._relogio.agora(),
                    fonte_url=contato.fonte_url,
                )
        self._sessao.flush()
        return lidas

    def _procurar_contato(self, inicial: Pagina) -> _Contato | None:
        """Procura na página inicial e, se faltar algo, em até 3 subpáginas do posto."""
        endereco: str | None = None
        telefone: str | None = None
        fontes: list[str] = []

        def ler(pagina: Pagina) -> None:
            nonlocal endereco, telefone
            achado = extrair_contato(pagina.html)
            novo = (endereco is None and achado.endereco) or (
                telefone is None and achado.telefone_plantao
            )
            endereco = endereco or achado.endereco
            telefone = telefone or achado.telefone_plantao
            if novo and pagina.destino not in fontes:
                fontes.append(pagina.destino)

        ler(inicial)
        for url in links_de_contato(inicial.html, inicial.destino, limite=MAXIMO_DE_SUBPAGINAS):
            if (endereco and telefone) or self._cliente.interrompido_por is not None:
                break
            subpagina = self._cliente.baixar(url)
            if subpagina.ok:
                ler(subpagina)

        if endereco is None and telefone is None:
            return None
        # de uma página só, cita essa página; de várias, a inicial do posto, que leva a todas
        fonte = fontes[0] if len(fontes) == 1 else inicial.destino
        return _Contato(endereco, telefone, fonte)
