"""Coleta dos vistos da Wikipédia: lê o artigo, valida, aplica ou retém, traduz e registra.

Regras (spec 002, FR-010 a FR-012b, FR-016; data-model.md):

- Só a página do artigo é pedida (nunca a API, que o `robots.txt` proíbe), pelo cliente educado.
- Uma coleta só muda o que o site mostra se for **válida**: formato esperado e países reconhecidos
  pelo menos no mínimo (`validade.py`). Uma coleta `rejeitada`, `adiada`, `falhou` ou `bloqueada`
  só grava o motivo.
- Edição do artigo de menos de 24 h adia a rodada (`estabilidade.py`).
- Numa coleta válida, cada país passa pela regra de retenção (`retencao.py`): mudança para menos
  exigente fica retida até o dono confirmar; o país mantém o dado e a data antigos.
- Observações novas ou alteradas são traduzidas em lote; a falha do tradutor nunca invalida a
  coleta, e o que ficou sem tradução é tentado de novo na coleta seguinte.
- O que a coleta não reconhece (nomes, rótulos) e as regras por país a reconfirmar vão para
  `item_para_revisao`, nunca descartados em silêncio.
"""

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from farol.dominio import (
    CategoriaDeVisto,
    ColetaVistos,
    ColetaVistosRepositorio,
    EstadoDaRetencao,
    EstadoDoItem,
    ItemParaRevisaoRepositorio,
    MudancaRetida,
    MudancaRetidaRepositorio,
    RequisitoVisto,
    RequisitoVistoRepositorio,
    ResultadoDaColetaDeVistos,
    TipoDeItemParaRevisao,
)
from farol.infra import Baixador, Pagina, Relogio, obter_logger
from farol.vistos.consolidacao import (
    Candidato,
    Consolidacao,
    calcular_hash_da_fonte,
    consolidar,
)
from farol.vistos.dicionario import Dicionario, dicionario_padrao
from farol.vistos.estabilidade import (
    IDADE_MINIMA_DA_EDICAO,
    LIMITE_DE_ADIAMENTOS,
    ProximaTentativa,
    avaliar_estabilidade,
    proxima_tentativa,
)
from farol.vistos.fonte import URL_DO_ARTIGO, ArtigoLido, ErroDeFormato, ler_artigo
from farol.vistos.normalizacao import chave_de_consulta
from farol.vistos.registro import (
    CANDIDATO_SEM_LINHA,
    candidato_em_json,
    completar_traducoes,
    preencher_requisito,
    situacao_do_candidato,
    situacao_do_requisito,
    traducoes_conhecidas,
)
from farol.vistos.retencao import HASH_SEM_LINHA, Aberta, AcaoDaRetencao, decidir_retencao
from farol.vistos.tradutor import TAMANHO_DO_LOTE, Tradutor, traduzir_em_lotes
from farol.vistos.validade import avaliar_validade

# Retidos acima de 10% dos países reconhecidos: possível vandalismo em massa na fonte
LIMITE_DE_VANDALISMO = (1, 10)

_log = obter_logger("farol.vistos")

R = ResultadoDaColetaDeVistos


@dataclass(frozen=True)
class RetidaNaColeta:
    """Um país com mudança retida: o que o site mostra e o que a fonte passou a dizer."""

    codigo: str
    categoria_exibida: CategoriaDeVisto | None  # nulo = "sem informação"
    categoria_lida: CategoriaDeVisto | None
    aceita_rg_exibido: bool
    aceita_rg_lido: bool


@dataclass(frozen=True)
class ContagemDePendencias:
    """O que espera o dono, no banco, depois da rodada (de todas as rodadas até agora)."""

    retidas: int = 0
    nomes: int = 0
    rotulos: int = 0
    regras: int = 0

    @property
    def total(self) -> int:
        return self.retidas + self.nomes + self.rotulos + self.regras


@dataclass(frozen=True)
class ResumoDaColetaDeVistos:
    coleta_id: int
    resultado: ResultadoDaColetaDeVistos
    motivo: str | None  # nulo quando válida
    proxima_tentativa: ProximaTentativa
    adiamentos_seguidos: int = 0
    falhas_seguidas: int = 0
    paises_reconhecidos: int | None = None
    minimo: int | None = None
    revisao_fonte: int | None = None
    ultima_edicao_fonte: datetime | None = None
    aplicadas: int = 0
    sem_mudanca: int = 0
    retidas: tuple[RetidaNaColeta, ...] = ()
    nomes_nao_reconhecidos: tuple[str, ...] = ()  # nesta rodada, como na fonte
    rotulos_nao_reconhecidos: tuple[str, ...] = ()  # nesta rodada, em chave de consulta
    regras_para_reconfirmar: tuple[str, ...] = ()  # códigos cuja nota mudou
    traducoes_novas: int = 0
    lotes_de_traducao: int = 0
    traducoes_falhas: int = 0
    pendencias: ContagemDePendencias = field(default_factory=ContagemDePendencias)

    @property
    def valida(self) -> bool:
        return self.resultado is R.VALIDA


@dataclass
class _Traducao:
    conhecidas: dict[str, dict[str, Any]]  # hash do texto -> tradução, data e modelo
    novas: int = 0
    lotes: int = 0
    falhas: int = 0


@dataclass
class _Itens:
    nomes: tuple[str, ...] = ()
    rotulos: tuple[str, ...] = ()
    regras: tuple[str, ...] = ()


def _formatar_idade(idade: timedelta) -> str:
    horas = int(idade.total_seconds() // 3600)
    if horas >= 1:
        return f"{horas} h"
    return f"{max(int(idade.total_seconds() // 60), 0)} min"


def _nome_da_categoria(categoria: CategoriaDeVisto | None) -> str:
    return "sem_informacao" if categoria is None else categoria.value


class ServicoDeColetaDeVistos:
    def __init__(
        self,
        sessao: Session,
        cliente: Baixador,
        relogio: Relogio,
        tradutor: Tradutor | None = None,
        *,
        dicionario: Dicionario | None = None,
        url_do_artigo: str = URL_DO_ARTIGO,
    ) -> None:
        self._sessao = sessao
        self._cliente = cliente
        self._relogio = relogio
        self._tradutor = tradutor
        self._dicionario = dicionario or dicionario_padrao()
        self._url = url_do_artigo
        self._coletas = ColetaVistosRepositorio(sessao)
        self._requisitos = RequisitoVistoRepositorio(sessao)
        self._mudancas = MudancaRetidaRepositorio(sessao)
        self._itens = ItemParaRevisaoRepositorio(sessao)

    # ------------------------------------------------------------------ a rodada
    def coletar(self, *, agendada: bool = False) -> ResumoDaColetaDeVistos:
        """Uma rodada. `agendada` liga o aviso de pendências do registro operacional (FR-012b)."""
        agora = self._relogio.agora()
        adiadas_antes = self._coletas.adiadas_seguidas()
        falhas_antes = self._coletas.falhas_seguidas()
        ultima_valida = self._coletas.ultima_valida()
        anteriores = ultima_valida.paises_reconhecidos if ultima_valida else None

        pagina = self._cliente.baixar(self._url)
        if not pagina.ok:
            resumo = self._registrar_nao_valida(
                agora,
                self._resultado_da_falha(pagina),
                pagina.motivo or "página não baixada",
                adiadas_antes,
                falhas_antes,
            )
        else:
            resumo = self._processar(
                pagina,
                agora,
                adiadas_antes,
                falhas_antes,
                anteriores,
                primeira=ultima_valida is None,
            )
        if agendada:
            self._avisar_pendencias(resumo.pendencias)
        return resumo

    def _resultado_da_falha(self, pagina: Pagina) -> ResultadoDaColetaDeVistos:
        """Bloqueio (403, 429, verificação humana, robots.txt) nunca insiste; o resto é falha."""
        motivo = pagina.motivo or ""
        if self._cliente.interrompido_por is not None or motivo.startswith("proibida pelo robots"):
            return R.BLOQUEADA
        return R.FALHOU

    def _processar(
        self,
        pagina: Pagina,
        agora: datetime,
        adiadas_antes: int,
        falhas_antes: int,
        anteriores: int | None,
        *,
        primeira: bool,
    ) -> ResumoDaColetaDeVistos:
        html_sha256 = hashlib.sha256(pagina.html.encode("utf-8")).hexdigest()
        try:
            artigo = ler_artigo(pagina.html)
        except ErroDeFormato as erro:
            veredito = avaliar_validade(
                0,
                formato_esperado=False,
                reconhecidos_anteriores=anteriores,
                detalhe_do_formato=str(erro),
            )
            return self._registrar_nao_valida(
                agora,
                R.REJEITADA,
                veredito.motivo or "formato inesperado",
                adiadas_antes,
                falhas_antes,
                formato_inesperado=True,
                html_sha256=html_sha256,
            )

        campos_da_fonte: dict[str, Any] = {
            "ultima_edicao_fonte": artigo.ultima_edicao,
            "revisao_fonte": artigo.revisao,
            "html_sha256": html_sha256,
        }
        estabilidade = avaliar_estabilidade(artigo.ultima_edicao, agora, adiadas_antes)
        if estabilidade.adiar:
            tentativa = adiadas_antes + 1
            motivo = (
                f"a última edição do artigo foi há {_formatar_idade(estabilidade.idade)} "
                f"(mínimo {_formatar_idade(IDADE_MINIMA_DA_EDICAO)}); "
                f"tentativa {tentativa} de {LIMITE_DE_ADIAMENTOS}, nova tentativa amanhã"
            )
            return self._registrar_nao_valida(
                agora, R.ADIADA, motivo, adiadas_antes, falhas_antes, **campos_da_fonte
            )
        if estabilidade.forcada:
            _log.info(
                "vistos: o artigo foi editado há %s, mas já são %d adiamentos seguidos; "
                "a coleta segue mesmo assim",
                _formatar_idade(estabilidade.idade),
                adiadas_antes,
            )

        consolidacao = consolidar(artigo.linhas, self._dicionario)
        veredito = avaliar_validade(
            consolidacao.paises_reconhecidos,
            formato_esperado=True,
            reconhecidos_anteriores=anteriores,
        )
        if not veredito.valida:
            return self._registrar_nao_valida(
                agora,
                R.REJEITADA,
                veredito.motivo or "países reconhecidos de menos",
                adiadas_antes,
                falhas_antes,
                linhas_lidas=len(artigo.linhas),
                paises_reconhecidos=consolidacao.paises_reconhecidos,
                minimo=veredito.minimo,
                **campos_da_fonte,
            )
        return self._aplicar(
            artigo, consolidacao, veredito.minimo, html_sha256, agora, primeira=primeira
        )

    # ------------------------------------------------------------------ coleta não válida
    def _registrar_nao_valida(
        self,
        agora: datetime,
        resultado: ResultadoDaColetaDeVistos,
        motivo: str,
        adiadas_antes: int,
        falhas_antes: int,
        *,
        minimo: int | None = None,
        formato_inesperado: bool = False,
        **campos: Any,
    ) -> ResumoDaColetaDeVistos:
        """Grava a tentativa e o motivo. Nenhum dado exibido muda (SC-007)."""
        adiamentos = adiadas_antes + 1 if resultado is R.ADIADA else 0
        falhas = falhas_antes + 1 if resultado is R.FALHOU else 0
        coleta = ColetaVistos(
            iniciada_em=agora,
            finalizada_em=self._relogio.agora(),
            resultado=resultado,
            motivo=motivo,
            adiamentos_seguidos=adiamentos,
            falhas_seguidas=falhas,
            **campos,
        )
        self._coletas.adicionar(coleta)
        self._sessao.flush()
        proxima = proxima_tentativa(
            resultado, adiamentos_seguidos=adiamentos, falhas_seguidas=falhas
        )
        self._registrar_no_log(
            resultado, motivo, adiamentos, falhas, proxima, formato_inesperado=formato_inesperado
        )
        return ResumoDaColetaDeVistos(
            coleta_id=coleta.id,
            resultado=resultado,
            motivo=motivo,
            proxima_tentativa=proxima,
            adiamentos_seguidos=adiamentos,
            falhas_seguidas=falhas,
            paises_reconhecidos=campos.get("paises_reconhecidos"),
            minimo=minimo,
            revisao_fonte=campos.get("revisao_fonte"),
            ultima_edicao_fonte=campos.get("ultima_edicao_fonte"),
            pendencias=self._contar_pendencias(),
        )

    @staticmethod
    def _registrar_no_log(
        resultado: ResultadoDaColetaDeVistos,
        motivo: str,
        adiamentos: int,
        falhas: int,
        proxima: ProximaTentativa,
        *,
        formato_inesperado: bool = False,
    ) -> None:
        dados = {"motivo": motivo}
        if formato_inesperado:
            _log.warning(
                "vistos: coleta rejeitada por formato inesperado: o leitor da página precisa de "
                "manutenção (mudança de estrutura na fonte)",
                extra={"dados": dados},
            )
            return
        if resultado is R.ADIADA:
            _log.info(
                "vistos: rodada adiada",
                extra={
                    "dados": {**dados, "tentativa": adiamentos, "proxima_tentativa": proxima.value}
                },
            )
        elif resultado is R.FALHOU:
            _log.warning(
                "vistos: rodada falhou",
                extra={"dados": {**dados, "tentativa": falhas, "proxima_tentativa": proxima.value}},
            )
        elif resultado is R.BLOQUEADA:
            _log.warning("vistos: coleta interrompida", extra={"dados": dados})
        else:
            _log.warning("vistos: coleta rejeitada", extra={"dados": dados})

    # ------------------------------------------------------------------ coleta válida
    def _aplicar(
        self,
        artigo: ArtigoLido,
        consolidacao: Consolidacao,
        minimo: int,
        html_sha256: str,
        agora: datetime,
        *,
        primeira: bool,
    ) -> ResumoDaColetaDeVistos:
        coleta = ColetaVistos(
            iniciada_em=agora,
            resultado=R.VALIDA,
            linhas_lidas=len(artigo.linhas),
            paises_reconhecidos=consolidacao.paises_reconhecidos,
            ultima_edicao_fonte=artigo.ultima_edicao,
            revisao_fonte=artigo.revisao,
            html_sha256=html_sha256,
        )
        self._coletas.adicionar(coleta)
        self._sessao.flush()

        existentes = {r.territorio_codigo: r for r in self._requisitos.listar_todos()}
        pendentes = {m.territorio_codigo: m for m in self._mudancas.listar_pendentes()}
        rejeitadas = {m.territorio_codigo: m for m in self._mudancas.listar_rejeitadas()}
        hashes_de_nomes_pendentes = self._hashes_de_nomes_pendentes()

        traducao = self._traduzir(
            consolidacao, existentes, [*pendentes.values(), *rejeitadas.values()], agora
        )
        for requisito in existentes.values():  # tradução que faltava (a coleta anterior falhou)
            completas = completar_traducoes(requisito.observacoes, traducao.conhecidas)
            if completas != requisito.observacoes:
                requisito.observacoes = completas

        aplicadas = sem_mudanca = 0
        retidas: list[RetidaNaColeta] = []
        codigos = sorted({*consolidacao.candidatos, *existentes, *pendentes, *rejeitadas})
        for codigo in codigos:
            candidato = consolidacao.candidatos.get(codigo)
            existente = existentes.get(codigo)
            aberta_no_banco = pendentes.get(codigo) or rejeitadas.get(codigo)
            decisao = decidir_retencao(
                situacao_do_requisito(existente) if existente else None,
                situacao_do_candidato(candidato) if candidato else None,
                primeira_coleta=primeira,
                aberta=(
                    Aberta(aberta_no_banco.estado, aberta_no_banco.hash_fonte_lido)
                    if aberta_no_banco
                    else None
                ),
                fonte_ja_lida=(
                    existente is None
                    and candidato is not None
                    and candidato.hash_fonte in hashes_de_nomes_pendentes
                ),
            )
            if aberta_no_banco is not None and decisao.encerrar is not None:
                if decisao.encerrar is EstadoDaRetencao.REVERTIDA:
                    self._mudancas.reverter(aberta_no_banco, agora)
                else:
                    self._mudancas.superar(aberta_no_banco, agora)
                self._sessao.flush()  # a nova pendente não pode coexistir com a antiga no índice

            dados = candidato_em_json(candidato, traducao.conhecidas) if candidato else None
            match decisao.acao:
                case AcaoDaRetencao.SEM_MUDANCA:
                    if existente is not None:  # a mesma fonte, confirmada hoje
                        existente.lido_em = agora
                        existente.coleta_id = coleta.id
                        sem_mudanca += 1
                case AcaoDaRetencao.MANTER_REJEITADA:
                    sem_mudanca += 1
                case AcaoDaRetencao.APLICAR if dados is not None:
                    if existente is None:
                        novo = RequisitoVisto(territorio_codigo=codigo)
                        preencher_requisito(novo, dados, agora, coleta.id)
                        self._requisitos.adicionar(novo)
                    else:
                        preencher_requisito(existente, dados, agora, coleta.id)
                    aplicadas += 1
                case AcaoDaRetencao.RETER:  # inclusive a saída da linha: candidato nulo
                    self._mudancas.adicionar(
                        MudancaRetida(
                            territorio_codigo=codigo,
                            coleta_id=coleta.id,
                            estado=EstadoDaRetencao.PENDENTE,
                            hash_fonte_lido=candidato.hash_fonte if candidato else HASH_SEM_LINHA,
                            candidato=dados if dados is not None else dict(CANDIDATO_SEM_LINHA),
                            categoria_exibida=existente.categoria if existente else None,
                            categoria_lida=candidato.categoria if candidato else None,
                            aceita_rg_exibido=existente.aceita_rg if existente else False,
                            aceita_rg_lido=candidato.aceita_rg if candidato else False,
                            criada_em=agora,
                        )
                    )
                    retidas.append(self._retida(codigo, existente, candidato))
                case AcaoDaRetencao.ATUALIZAR_RETIDA if pendentes.get(codigo):
                    mudanca = pendentes[codigo]
                    self._mudancas.atualizar_coleta(mudanca, coleta.id)
                    if candidato is not None and dados is not None:
                        mudanca.candidato = dados
                        mudanca.categoria_lida = candidato.categoria
                        mudanca.aceita_rg_lido = candidato.aceita_rg
                    retidas.append(self._retida(codigo, existente, candidato))
                case _:
                    raise AssertionError(f"decisão sem os dados que ela exige: {codigo} {decisao}")
        self._sessao.flush()

        itens = self._registrar_itens(artigo, consolidacao, agora)
        self._itens.resolver_nao_vistos(agora, agora)

        coleta.aplicadas = aplicadas
        coleta.retidas = len(retidas)
        coleta.finalizada_em = self._relogio.agora()
        self._sessao.flush()

        self._registrar_retidas(retidas, consolidacao.paises_reconhecidos)
        proxima = proxima_tentativa(R.VALIDA, adiamentos_seguidos=0, falhas_seguidas=0)
        _log.info(
            "vistos: coleta válida",
            extra={
                "dados": {
                    "reconhecidos": consolidacao.paises_reconhecidos,
                    "aplicadas": aplicadas,
                    "sem_mudanca": sem_mudanca,
                    "retidas": len(retidas),
                }
            },
        )
        return ResumoDaColetaDeVistos(
            coleta_id=coleta.id,
            resultado=R.VALIDA,
            motivo=None,
            proxima_tentativa=proxima,
            paises_reconhecidos=consolidacao.paises_reconhecidos,
            minimo=minimo,
            revisao_fonte=artigo.revisao,
            ultima_edicao_fonte=artigo.ultima_edicao,
            aplicadas=aplicadas,
            sem_mudanca=sem_mudanca,
            retidas=tuple(retidas),
            nomes_nao_reconhecidos=itens.nomes,
            rotulos_nao_reconhecidos=itens.rotulos,
            regras_para_reconfirmar=itens.regras,
            traducoes_novas=traducao.novas,
            lotes_de_traducao=traducao.lotes,
            traducoes_falhas=traducao.falhas,
            pendencias=self._contar_pendencias(),
        )

    @staticmethod
    def _retida(
        codigo: str, exibido: RequisitoVisto | None, lido: Candidato | None
    ) -> RetidaNaColeta:
        return RetidaNaColeta(
            codigo=codigo,
            categoria_exibida=exibido.categoria if exibido else None,
            categoria_lida=lido.categoria if lido else None,
            aceita_rg_exibido=exibido.aceita_rg if exibido else False,
            aceita_rg_lido=lido.aceita_rg if lido else False,
        )

    def _hashes_de_nomes_pendentes(self) -> set[str]:
        """Hash da linha de cada nome que a coleta anterior não reconheceu e ainda espera revisão.

        Um país sem registro cuja linha já estava na fonte só pode ter mudado por causa do
        dicionário: a retenção vale para mudanças da fonte, não do dicionário (FR-010a).
        """
        return {
            entrada["hash_fonte"]
            for item in self._itens.listar_pendentes(TipoDeItemParaRevisao.NOME)
            for entrada in item.contexto
            if "hash_fonte" in entrada
        }

    # ------------------------------------------------------------------ tradução
    def _traduzir(
        self,
        consolidacao: Consolidacao,
        existentes: dict[str, RequisitoVisto],
        abertas: list[MudancaRetida],
        agora: datetime,
    ) -> _Traducao:
        """Traduz em lote só as observações novas, alteradas ou que ficaram sem tradução."""
        gravadas = [o for r in existentes.values() for o in r.observacoes]
        gravadas += [o for m in abertas for o in m.candidato.get("observacoes", [])]
        traducao = _Traducao(conhecidas=traducoes_conhecidas(gravadas))

        faltam: dict[str, str] = {}  # hash -> texto
        for candidato in consolidacao.candidatos.values():
            for observacao in candidato.observacoes:
                if observacao.hash not in traducao.conhecidas:
                    faltam[observacao.hash] = observacao.texto
        for gravada in gravadas:
            if gravada["hash"] not in traducao.conhecidas:
                faltam[gravada["hash"]] = gravada["texto"]
        if self._tradutor is None or not faltam:
            return traducao

        traduzidas = traduzir_em_lotes(self._tradutor, list(faltam.values()))
        for hash_do_texto, texto in faltam.items():
            if texto in traduzidas:
                traducao.conhecidas[hash_do_texto] = {
                    "traducao": traduzidas[texto],
                    "traduzido_em": agora.isoformat(),
                    "modelo": self._tradutor.nome_do_modelo,
                }
        traducao.novas = len(traduzidas)
        traducao.lotes = -(-len(faltam) // TAMANHO_DO_LOTE)
        traducao.falhas = len(faltam) - len(traduzidas)
        return traducao

    # ------------------------------------------------------------------ itens para revisão
    def _registrar_itens(
        self, artigo: ArtigoLido, consolidacao: Consolidacao, agora: datetime
    ) -> _Itens:
        """Nomes e rótulos não reconhecidos e regras por país a reconfirmar (FR-012, FR-012a)."""
        linhas = {(linha.tabela, linha.nome): linha for linha in artigo.linhas}

        por_nome: dict[str, list[dict[str, str]]] = {}
        como_na_fonte: dict[str, str] = {}
        for nome in consolidacao.nomes_desconhecidos:
            chave = chave_de_consulta(nome.nome)
            como_na_fonte.setdefault(chave, nome.nome)
            por_nome.setdefault(chave, []).append(
                {
                    "tabela": nome.tabela,
                    "nome_na_fonte": nome.nome,
                    "hash_fonte": calcular_hash_da_fonte([linhas[(nome.tabela, nome.nome)]]),
                }
            )
        nomes = []
        for chave, contexto in por_nome.items():
            item = self._itens.registrar_visto(TipoDeItemParaRevisao.NOME, chave, contexto, agora)
            if item.estado is EstadoDoItem.PENDENTE:  # o que o dono já ignorou não volta ao resumo
                nomes.append(como_na_fonte[chave])

        por_rotulo: dict[str, list[dict[str, str]]] = {}
        for rotulo in consolidacao.rotulos_desconhecidos:
            por_rotulo.setdefault(rotulo.rotulo, []).append(
                {"tabela": rotulo.tabela, "nome_na_fonte": rotulo.nome}
            )
        for chave, contexto in por_rotulo.items():
            self._itens.registrar_visto(TipoDeItemParaRevisao.ROTULO, chave, contexto, agora)

        regras = []
        for codigo, candidato in consolidacao.candidatos.items():
            regra = self._dicionario.regras.get(codigo)
            if regra is None or candidato.hash_observacao == regra.hash_observacao:
                continue
            contexto_da_regra = {
                "hash_esperado": regra.hash_observacao,
                "hash_lido": candidato.hash_observacao,
                "texto": "\n".join(linha.notas for linha in candidato.linhas_fonte if linha.notas),
            }
            self._itens.registrar_visto(
                TipoDeItemParaRevisao.REGRA, codigo, contexto_da_regra, agora
            )
            regras.append(codigo)
        return _Itens(tuple(nomes), tuple(por_rotulo), tuple(regras))

    # ------------------------------------------------------------------ pendências e registro
    def _contar_pendencias(self) -> ContagemDePendencias:
        por_tipo = Counter(item.tipo for item in self._itens.listar_pendentes())
        return ContagemDePendencias(
            retidas=len(self._mudancas.listar_pendentes()),
            nomes=por_tipo[TipoDeItemParaRevisao.NOME],
            rotulos=por_tipo[TipoDeItemParaRevisao.ROTULO],
            regras=por_tipo[TipoDeItemParaRevisao.REGRA],
        )

    @staticmethod
    def _registrar_retidas(retidas: list[RetidaNaColeta], reconhecidos: int) -> None:
        for retida in retidas:
            _log.warning(
                "vistos: mudança retida",
                extra={
                    "dados": {
                        "codigo": retida.codigo,
                        "exibida": _nome_da_categoria(retida.categoria_exibida),
                        "lida": _nome_da_categoria(retida.categoria_lida),
                    }
                },
            )
        numerador, denominador = LIMITE_DE_VANDALISMO
        if retidas and len(retidas) * denominador > reconhecidos * numerador:
            _log.warning(
                "vistos: possível vandalismo em massa na fonte",
                extra={
                    "dados": {
                        "retidas": len(retidas),
                        "reconhecidos": reconhecidos,
                        "percentual": round(len(retidas) / reconhecidos * 100, 1),
                    }
                },
            )

    @staticmethod
    def _avisar_pendencias(pendencias: ContagemDePendencias) -> None:
        """Rodada agendada que termina com pendência escreve uma linha de aviso (FR-012b)."""
        if pendencias.total == 0:
            return
        _log.warning(
            "vistos: há pendências para o dono",
            extra={
                "dados": {
                    "retidas": pendencias.retidas,
                    "nomes_pendentes": pendencias.nomes,
                    "rotulos_pendentes": pendencias.rotulos,
                    "regras_pendentes": pendencias.regras,
                }
            },
        )
