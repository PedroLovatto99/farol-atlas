"""Leitura dos vistos para a API: resolve o visto de cada território (data-model.md).

Como a leitura resolve o visto de um território:

1. Território sem painel (área neutra) ou código desconhecido: sem visto. Brasil: sem visto (nulo no
   painel, `nao_se_aplica` no globo).
2. `identidade_do_soberano` (Kosovo, Malvinas): a identidade do painel é a do soberano (001), mas a
   regra de entrada é a da linha própria da fonte, que segue quem controla a fronteira. Só o
   registro do próprio território vale (`origem = proprio`, sem nota de herança); sem ele, o
   visto é `sem_informacao`, nunca o do soberano (a Argentina aceita RG, as Malvinas não). A seção
   diz de que território é (`territorio_nome`).
3. Há registro com o código do território: usa-o (`origem = proprio`).
4. Dependência comum sem registro: usa o do soberano (`origem = soberano`, com o nome do soberano).
5. Sem registro, ou nunca houve coleta válida: `sem_informacao`.

Número fixo de consultas (princípio III): `GET /vistos` faz 3 (última coleta válida, territórios e
registros); o visto de um país faz até 3 (última coleta válida, território com o soberano e os
registros dos dois).
"""

from collections.abc import Mapping
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from farol.dominio import (
    CODIGO_DO_BRASIL,
    ColetaVistosRepositorio,
    RequisitoVisto,
    RequisitoVistoRepositorio,
    Territorio,
    TerritorioRepositorio,
    TipoTerritorio,
)
from farol.infra import Relogio
from farol.vistos.fonte import LICENCA_DA_FONTE, NOME_DA_FONTE, URL_DO_ARTIGO
from farol.vistos.permanencia import TipoDePermanencia
from farol.vistos.visoes import (
    FonteDosVistos,
    ObservacaoDoVisto,
    OrigemDoVisto,
    PermanenciaDoVisto,
    SituacaoDeVisto,
    SituacaoNoGlobo,
    TerritorioComVisto,
    VisaoDosVistos,
    VisaoDoVisto,
)

LIMITE_DE_DADOS_ANTIGOS = timedelta(days=14)  # FR-015 e FR-029a

FONTE = FonteDosVistos(NOME_DA_FONTE, URL_DO_ARTIGO, LICENCA_DA_FONTE)

# O nome que a 001 usa para os territórios cuja identidade no painel é a de outro país
NOMES_DA_001 = {"XK": "Kosovo", "FK": "Ilhas Malvinas"}


class _Resolvido:
    """O registro que vale para um território e de onde ele veio."""

    __slots__ = ("origem", "requisito", "soberano_nome")

    def __init__(
        self,
        requisito: RequisitoVisto | None,
        origem: OrigemDoVisto | None = None,
        soberano_nome: str | None = None,
    ) -> None:
        self.requisito = requisito
        self.origem = origem
        self.soberano_nome = soberano_nome


def _resolver(
    territorio: Territorio,
    territorios: Mapping[str, Territorio],
    requisitos: Mapping[str, RequisitoVisto],
) -> _Resolvido:
    """Regras 2 a 5. `territorios` tem ao menos o território e o soberano dele."""
    proprio = requisitos.get(territorio.codigo)
    if proprio is not None:
        return _Resolvido(proprio, OrigemDoVisto.PROPRIO)
    if territorio.identidade_do_soberano:
        return _Resolvido(None)  # a regra de entrada nunca é a do soberano (regra 2)
    soberano = territorios.get(territorio.soberano_codigo) if territorio.soberano_codigo else None
    if territorio.tipo is TipoTerritorio.DEPENDENCIA and soberano is not None:
        herdado = requisitos.get(soberano.codigo)
        if herdado is not None:
            return _Resolvido(herdado, OrigemDoVisto.SOBERANO, soberano.nome_pt)
    return _Resolvido(None)


def _desatualizado(data: datetime | None, agora: datetime) -> bool:
    return data is not None and agora - data > LIMITE_DE_DADOS_ANTIGOS


def _nome_do_territorio(territorio: Territorio) -> str | None:
    """Só para quem tem a identidade de outro no painel; os demais já se chamam pelo nome certo."""
    if not territorio.identidade_do_soberano:
        return None
    return (
        NOMES_DA_001.get(territorio.codigo)
        or (territorio.rotulo_busca or territorio.nome_pt).split(" (")[0]
    )


def _visao(resolvido: _Resolvido, territorio: Territorio, agora: datetime) -> VisaoDoVisto:
    requisito = resolvido.requisito
    nome = _nome_do_territorio(territorio)
    if requisito is None:
        return VisaoDoVisto(
            situacao=SituacaoDeVisto.SEM_INFORMACAO,
            motivo_outra_situacao=None,
            rotulo_original=None,
            aceita_rg=False,
            varia_conforme_motivo=False,
            permanencia=None,
            observacoes=(),
            origem=None,
            soberano_nome=None,
            territorio_nome=nome,
            dado_de=None,
            desatualizado=False,
            fonte=FONTE,
        )
    tipo = TipoDePermanencia(requisito.permanencia_tipo)
    return VisaoDoVisto(
        situacao=SituacaoDeVisto(requisito.categoria.value),
        motivo_outra_situacao=requisito.motivo_outra,
        rotulo_original=requisito.rotulo_original,
        aceita_rg=requisito.aceita_rg,
        varia_conforme_motivo=requisito.varia_conforme_motivo,
        permanencia=(
            None
            if tipo is TipoDePermanencia.NENHUMA
            else PermanenciaDoVisto(tipo, requisito.permanencia_texto)
        ),
        observacoes=tuple(
            ObservacaoDoVisto(texto_original=o["texto"], traducao=o.get("traducao"))
            for o in requisito.observacoes
        ),
        origem=resolvido.origem,
        soberano_nome=resolvido.soberano_nome,
        territorio_nome=nome,
        dado_de=requisito.lido_em,
        desatualizado=_desatualizado(requisito.lido_em, agora),
        fonte=FONTE,
    )


def montar_visto_do_pais(sessao: Session, codigo: str, relogio: Relogio) -> VisaoDoVisto | None:
    """A seção "Visto" do painel; nulo para o Brasil, área neutra e código desconhecido."""
    if codigo == CODIGO_DO_BRASIL:
        return None
    agora = relogio.agora()
    ultima = ColetaVistosRepositorio(sessao).ultima_valida()
    envolvidos = {t.codigo: t for t in TerritorioRepositorio(sessao).obter_com_soberano(codigo)}
    territorio = envolvidos.get(codigo)
    if territorio is None or territorio.tipo is TipoTerritorio.NEUTRO:
        return None
    requisitos = (
        {r.territorio_codigo: r for r in RequisitoVistoRepositorio(sessao).listar(list(envolvidos))}
        if ultima is not None
        else {}
    )
    return _visao(_resolver(territorio, envolvidos, requisitos), territorio, agora)


def montar_vistos_do_mapa(sessao: Session, relogio: Relogio) -> VisaoDosVistos:
    """A situação de visto de cada território com painel, para pintar o globo."""
    agora = relogio.agora()
    ultima = ColetaVistosRepositorio(sessao).ultima_valida()
    territorios = {
        t.codigo: t
        for t in TerritorioRepositorio(sessao).listar_todos()
        if t.tipo is not TipoTerritorio.NEUTRO
    }
    requisitos = (
        {r.territorio_codigo: r for r in RequisitoVistoRepositorio(sessao).listar_todos()}
        if ultima is not None
        else {}
    )

    itens = []
    for codigo, territorio in territorios.items():
        if codigo == CODIGO_DO_BRASIL:
            itens.append(TerritorioComVisto(codigo, SituacaoNoGlobo.NAO_SE_APLICA, False))
            continue
        requisito = _resolver(territorio, territorios, requisitos).requisito
        itens.append(
            TerritorioComVisto(
                codigo=codigo,
                situacao=(
                    SituacaoNoGlobo(requisito.categoria.value)
                    if requisito
                    else SituacaoNoGlobo.SEM_INFORMACAO
                ),
                aceita_rg=requisito.aceita_rg if requisito else False,
            )
        )
    coletado_em = ultima.finalizada_em if ultima is not None else None
    return VisaoDosVistos(
        dados_obtidos=ultima is not None,
        coletado_em=coletado_em,
        desatualizado=_desatualizado(coletado_em, agora),
        fonte=FONTE,
        territorios=tuple(itens),
    )
