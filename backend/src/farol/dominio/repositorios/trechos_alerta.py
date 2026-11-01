"""Índice de trechos dos alertas: o que falta indexar, gravar, apagar e recuperar.

É o único lugar que fala SQL com `trecho_alerta`. Toda recuperação passa por um `JOIN` com o alerta
que exige conteúdo em vigor (`removido_em` nulo e `confirmado_hash = alerta_hash`): o que saiu da
lista ou mudou de conteúdo deixa de ser devolvido mesmo antes de o varredor apagar as linhas. A
comparação de vetores só olha as linhas do modelo e da dimensão pedidos, porque a coluna não tem
dimensão fixa e vetores de tamanhos diferentes não se comparam.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, cast, delete, func, literal, or_, select, update
from sqlalchemy.dialects.postgresql import REGCONFIG, distinct_on
from sqlalchemy.orm import Session, aliased

from farol.dominio.enums import StatusClassificacao
from farol.dominio.modelos import Alerta, Classificacao, NivelTerritorio, TrechoAlerta


@dataclass(frozen=True)
class AlertaElegivel:
    """Alerta que vale para o nível e, por isso, tem trechos no índice."""

    id: int
    hash: str
    titulo: str
    texto: str
    html_corpo: str | None
    classificacao_id: int
    classificado_em: datetime
    paises: tuple[str, ...]  # os da classificação; vazio num aviso geral (não define nível)


@dataclass(frozen=True)
class AlertaCitado:
    """O que as citações do chat precisam de um alerta: identificação e o texto original."""

    id: int
    titulo: str
    url: str
    publicado_em: datetime
    modificado_em: datetime | None
    texto: str


@dataclass(frozen=True)
class NovoTrecho:
    posicao: int
    inicio: int
    fim: int
    embedding: Sequence[float]


@dataclass(frozen=True)
class TrechoGravado:
    """O que o índice já guarda de um trecho (sem o vetor)."""

    alerta_id: int
    alerta_hash: str
    classificacao_id: int
    posicao: int
    inicio: int
    fim: int
    paises: tuple[str, ...]
    em_vigor_para: tuple[str, ...]
    indexado_em: datetime


@dataclass(frozen=True)
class TrechoRecuperado:
    alerta_id: int
    posicao: int
    inicio: int
    fim: int
    paises: tuple[str, ...]
    # o alerta rege o nível do país pedido (ou de algum país, se não houve pedido) ou é aviso geral
    em_vigor: bool
    aviso_geral: bool = False  # a classificação não define nível nenhum (fraude, aliciamento…)
    distancia: float = 0.0  # cosseno (0 = igual); só na busca por similaridade
    pontuacao: float = 0.0  # `ts_rank`; só na busca por texto


def _elegiveis(*colunas: Any) -> Select[Any]:
    """Alertas confirmados, ativos, com página lida e classificação `ok` do conteúdo confirmado."""
    return (
        select(*colunas)
        .select_from(Alerta)
        .join(
            Classificacao,
            (Classificacao.alerta_id == Alerta.id)
            & (Classificacao.alerta_hash == Alerta.confirmado_hash)
            & (Classificacao.status == StatusClassificacao.OK),
        )
        .where(
            Alerta.confirmado_execucao_id.is_not(None),
            Alerta.removido_em.is_(None),
            Alerta.pagina_lida.is_(True),
        )
    )


class TrechoAlertaRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    # ------------------------------------------------------------------------ o que indexar
    def alertas_a_indexar(self, modelo_embedding: str, dimensoes: int) -> list[int]:
        """Ids dos alertas confirmados, ativos e com classificação `ok` do conteúdo confirmado
        que não têm trechos em dia: nenhum, ou de outro conteúdo (hash), de outra classificação, de
        uma classificação refeita depois da indexação ou de outro modelo ou dimensão."""
        em_dia = (
            select(TrechoAlerta.id)
            .where(
                TrechoAlerta.alerta_id == Alerta.id,
                TrechoAlerta.alerta_hash == Alerta.confirmado_hash,
                TrechoAlerta.classificacao_id == Classificacao.id,
                TrechoAlerta.indexado_em >= Classificacao.classificado_em,
                TrechoAlerta.modelo_embedding == modelo_embedding,
                TrechoAlerta.dimensoes == dimensoes,
            )
            .exists()
        )
        return list(self._sessao.scalars(_elegiveis(Alerta.id).where(~em_dia).order_by(Alerta.id)))

    def alertas_elegiveis(self) -> list[AlertaElegivel]:
        """Os alertas que devem ter trechos, com os países da classificação vigente."""
        linhas = self._sessao.execute(
            _elegiveis(
                Alerta.id,
                Alerta.confirmado_hash,
                Alerta.titulo,
                Alerta.texto,
                Alerta.html_corpo,
                Classificacao.id,
                Classificacao.classificado_em,
            ).order_by(Alerta.id)
        ).all()
        paises: dict[int, list[str]] = {}
        if linhas:
            consulta = (
                select(NivelTerritorio.classificacao_id, NivelTerritorio.territorio_codigo)
                .where(NivelTerritorio.classificacao_id.in_([linha[5] for linha in linhas]))
                .order_by(NivelTerritorio.territorio_codigo)
            )
            for classificacao_id, codigo in self._sessao.execute(consulta):
                paises.setdefault(classificacao_id, []).append(codigo)
        return [
            AlertaElegivel(
                id=alerta_id,
                hash=hash_,
                titulo=titulo,
                texto=texto or "",
                html_corpo=html_corpo,
                classificacao_id=classificacao_id,
                classificado_em=classificado_em,
                paises=tuple(paises.get(classificacao_id, [])),
            )
            for alerta_id, hash_, titulo, texto, html_corpo, classificacao_id, classificado_em in (
                linhas
            )
        ]

    def trechos_gravados(self, modelo: str, dimensoes: int) -> dict[int, list[TrechoGravado]]:
        """Os trechos do modelo e da dimensão pedidos, por alerta, sem os vetores."""
        consulta = (
            select(
                TrechoAlerta.alerta_id,
                TrechoAlerta.alerta_hash,
                TrechoAlerta.classificacao_id,
                TrechoAlerta.posicao,
                TrechoAlerta.inicio,
                TrechoAlerta.fim,
                TrechoAlerta.paises,
                TrechoAlerta.em_vigor_para,
                TrechoAlerta.indexado_em,
            )
            .where(TrechoAlerta.modelo_embedding == modelo, TrechoAlerta.dimensoes == dimensoes)
            .order_by(TrechoAlerta.alerta_id, TrechoAlerta.posicao)
        )
        gravados: dict[int, list[TrechoGravado]] = {}
        for linha in self._sessao.execute(consulta):
            gravados.setdefault(linha[0], []).append(
                TrechoGravado(*linha[:6], tuple(linha[6]), tuple(linha[7]), linha[8])
            )
        return gravados

    def resumo_do_indice(self) -> list[tuple[str, int, int, int]]:
        """`(modelo, dimensões, trechos, alertas)` de tudo o que há no índice."""
        consulta = (
            select(
                TrechoAlerta.modelo_embedding,
                TrechoAlerta.dimensoes,
                func.count(),
                func.count(TrechoAlerta.alerta_id.distinct()),
            )
            .group_by(TrechoAlerta.modelo_embedding, TrechoAlerta.dimensoes)
            .order_by(TrechoAlerta.modelo_embedding, TrechoAlerta.dimensoes)
        )
        return [(m, d, t, a) for m, d, t, a in self._sessao.execute(consulta)]

    # ------------------------------------------------------------------------ gravar e apagar
    def substituir_trechos(
        self,
        alerta_id: int,
        alerta_hash: str,
        novos: Sequence[NovoTrecho],
        *,
        modelo: str,
        dimensoes: int,
        classificacao_id: int,
        paises: Sequence[str],
        em_vigor_para: Sequence[str],
        agora: datetime,
    ) -> None:
        """Troca os trechos do alerta para o modelo e a dimensão dados, na transação em curso.

        Sai também o que for de outro conteúdo (hash diferente do dado), que não serve mais. Os
        vetores de outros modelos do mesmo conteúdo ficam; quem os apaga é
        `apagar_de_outros_modelos`.
        """
        for novo in novos:
            if len(novo.embedding) != dimensoes:
                raise ValueError(
                    f"o vetor do trecho {novo.posicao} tem {len(novo.embedding)} dimensões, "
                    f"e o índice espera {dimensoes}"
                )
        self._sessao.execute(
            delete(TrechoAlerta).where(
                TrechoAlerta.alerta_id == alerta_id,
                or_(
                    and_(
                        TrechoAlerta.modelo_embedding == modelo, TrechoAlerta.dimensoes == dimensoes
                    ),
                    TrechoAlerta.alerta_hash != alerta_hash,
                ),
            )
        )
        self._sessao.add_all(
            TrechoAlerta(
                alerta_id=alerta_id,
                alerta_hash=alerta_hash,
                classificacao_id=classificacao_id,
                posicao=novo.posicao,
                inicio=novo.inicio,
                fim=novo.fim,
                paises=list(paises),
                em_vigor_para=list(em_vigor_para),
                modelo_embedding=modelo,
                dimensoes=dimensoes,
                embedding=list(novo.embedding),
                indexado_em=agora,
            )
            for novo in novos
        )
        self._sessao.flush()

    def atualizar_metadados(
        self,
        alerta_id: int,
        alerta_hash: str,
        *,
        modelo: str,
        dimensoes: int,
        classificacao_id: int,
        paises: Sequence[str],
        em_vigor_para: Sequence[str],
        agora: datetime,
    ) -> None:
        """Muda países, vigor e classificação dos trechos sem tocar nos vetores."""
        self._sessao.execute(
            update(TrechoAlerta)
            .where(
                TrechoAlerta.alerta_id == alerta_id,
                TrechoAlerta.alerta_hash == alerta_hash,
                TrechoAlerta.modelo_embedding == modelo,
                TrechoAlerta.dimensoes == dimensoes,
            )
            .values(
                classificacao_id=classificacao_id,
                paises=list(paises),
                em_vigor_para=list(em_vigor_para),
                indexado_em=agora,
            )
        )

    def apagar_dos_que_nao_sao_elegiveis(self) -> int:
        """Apaga os trechos de alertas removidos, sem confirmação ou sem classificação válida.
        Devolve quantos alertas perderam trechos.

        Olha antes de apagar: um `DELETE` que não apaga nada ainda contaria como escrita e subiria a
        versão dos dados, esvaziando o cache do site a cada passada do varredor.
        """
        sobrando = list(
            self._sessao.scalars(
                select(TrechoAlerta.alerta_id)
                .where(TrechoAlerta.alerta_id.not_in(_elegiveis(Alerta.id)))
                .distinct()
            )
        )
        if sobrando:
            self._sessao.execute(delete(TrechoAlerta).where(TrechoAlerta.alerta_id.in_(sobrando)))
        return len(sobrando)

    def apagar_de_outros_modelos(self, alerta_id: int, modelo: str, dimensoes: int) -> int:
        """Apaga os vetores do alerta que não são do modelo e da dimensão dados; devolve quantos."""
        resultado = self._sessao.execute(
            delete(TrechoAlerta)
            .where(
                TrechoAlerta.alerta_id == alerta_id,
                or_(TrechoAlerta.modelo_embedding != modelo, TrechoAlerta.dimensoes != dimensoes),
            )
            .returning(TrechoAlerta.id)
        )
        return len(resultado.all())

    # ------------------------------------------------------------------------ recuperar
    def alertas_citados(self, ids: Sequence[int]) -> dict[int, AlertaCitado]:
        """Os alertas pelo id, numa consulta, para as citações (título, data, link e texto)."""
        if not ids:
            return {}
        consulta = select(
            Alerta.id,
            Alerta.titulo,
            Alerta.url,
            Alerta.publicado_em,
            Alerta.modificado_em,
            Alerta.texto,
        ).where(Alerta.id.in_(list(ids)))
        return {
            linha[0]: AlertaCitado(*linha[:5], linha[5] or "")
            for linha in self._sessao.execute(consulta)
        }

    @staticmethod
    def _em_vigor(
        em_vigor_para: Sequence[str], paises: Sequence[str] | None, aviso_geral: bool
    ) -> bool:
        rege = bool(set(em_vigor_para) & set(paises)) if paises else bool(em_vigor_para)
        return rege or aviso_geral

    def _consulta(
        self, paises: Sequence[str] | None, so_em_vigor: bool, *colunas: Any
    ) -> Select[Any]:
        """Os trechos de alertas ativos, do país pedido (se houver) e, com `so_em_vigor`, só de
        alerta em vigor: o que rege o nível (do país pedido, ou de algum país) ou o aviso geral.
        Fica de fora o alerta que define níveis mas não rege nenhum (foi substituído)."""
        aviso_geral = ~(
            select(NivelTerritorio.classificacao_id)
            .where(NivelTerritorio.classificacao_id == TrechoAlerta.classificacao_id)
            .exists()
        )
        consulta = (
            select(
                TrechoAlerta.alerta_id,
                TrechoAlerta.posicao,
                TrechoAlerta.inicio,
                TrechoAlerta.fim,
                TrechoAlerta.paises,
                TrechoAlerta.em_vigor_para,
                aviso_geral.label("aviso_geral"),
                *colunas,
            )
            .select_from(TrechoAlerta)
            .join(Alerta, Alerta.id == TrechoAlerta.alerta_id)
            .where(
                Alerta.removido_em.is_(None),
                Alerta.confirmado_execucao_id.is_not(None),
                Alerta.pagina_lida.is_(True),
                Alerta.confirmado_hash == TrechoAlerta.alerta_hash,
            )
        )
        if paises:
            consulta = consulta.where(TrechoAlerta.paises.overlap(list(paises)))
        if so_em_vigor:
            rege = (
                TrechoAlerta.em_vigor_para.overlap(list(paises))
                if paises
                else func.cardinality(TrechoAlerta.em_vigor_para) > 0
            )
            consulta = consulta.where(or_(rege, aviso_geral))
        return consulta

    def recuperar_por_similaridade(
        self,
        vetor: Sequence[float],
        *,
        modelo: str,
        dimensoes: int,
        limite: int,
        paises: Sequence[str] | None = None,
        so_em_vigor: bool = False,
    ) -> list[TrechoRecuperado]:
        """Os `limite` trechos mais próximos do vetor (distância de cosseno), numa consulta."""
        if len(vetor) != dimensoes:
            raise ValueError(
                f"o vetor da pergunta tem {len(vetor)} dimensões, e o índice espera {dimensoes}"
            )
        distancia = TrechoAlerta.embedding.cosine_distance(list(vetor)).label("distancia")
        consulta = (
            self._consulta(paises, so_em_vigor, distancia)
            .where(TrechoAlerta.modelo_embedding == modelo, TrechoAlerta.dimensoes == dimensoes)
            .order_by(distancia, TrechoAlerta.alerta_id, TrechoAlerta.posicao)
            .limit(limite)
        )
        return [
            TrechoRecuperado(
                alerta_id=a,
                posicao=p,
                inicio=i,
                fim=f,
                paises=tuple(ps),
                em_vigor=self._em_vigor(vigor, paises, geral),
                aviso_geral=geral,
                distancia=float(d),
            )
            for a, p, i, f, ps, vigor, geral, d in self._sessao.execute(consulta)
        ]

    def _sem_vetor_do_modelo(self, modelo: str, dimensoes: int) -> Any:
        """Condição: o alerta (de `Alerta`) não tem nenhum vetor do modelo e da dimensão pedidos."""
        outro = aliased(TrechoAlerta)
        return ~(
            select(outro.id)
            .where(
                outro.alerta_id == Alerta.id,
                outro.alerta_hash == Alerta.confirmado_hash,
                outro.modelo_embedding == modelo,
                outro.dimensoes == dimensoes,
            )
            .exists()
        )

    def alertas_sem_vetor(self, modelo: str, dimensoes: int) -> list[int]:
        """Alertas em vigor que têm trechos, mas nenhum do modelo e da dimensão pedidos (a troca
        de modelo está no meio). Alerta sem trecho nenhum ainda não foi indexado e não entra."""
        consulta = (
            self._consulta(None, False)
            .with_only_columns(TrechoAlerta.alerta_id)
            .where(self._sem_vetor_do_modelo(modelo, dimensoes))
            .distinct()
            .order_by(TrechoAlerta.alerta_id)
        )
        return list(self._sessao.scalars(consulta))

    def recuperar_por_texto(
        self,
        consulta: str,
        *,
        modelo: str,
        dimensoes: int,
        limite: int,
        paises: Sequence[str] | None = None,
        so_em_vigor: bool = False,
        so_alertas_sem_vetor: bool = False,
    ) -> list[TrechoRecuperado]:
        """Busca textual (`ts_rank`), sem diferença de acento, na fatia de cada trecho.

        Olha os trechos do modelo configurado e também os de alertas que ainda não têm vetor dele
        (outro modelo ou dimensão): o texto de um trecho não depende do modelo. Com
        `so_alertas_sem_vetor`, olha só estes últimos. Cada trecho aparece uma vez.
        """
        fatia = func.substr(
            Alerta.texto, TrechoAlerta.inicio + 1, TrechoAlerta.fim - TrechoAlerta.inicio
        )
        configuracao = cast(literal("portuguese"), REGCONFIG)
        # sem acento dos dois lados (extensão `unaccent`): "Irã" acha "Ira" e vice-versa
        documento = func.to_tsvector(configuracao, func.unaccent(fatia))
        busca = func.websearch_to_tsquery(configuracao, func.unaccent(consulta))
        pontuacao = func.ts_rank(documento, busca).label("pontuacao")
        sem_vetor = self._sem_vetor_do_modelo(modelo, dimensoes)
        do_modelo = and_(
            TrechoAlerta.modelo_embedding == modelo, TrechoAlerta.dimensoes == dimensoes
        )

        candidatos = (
            self._consulta(paises, so_em_vigor, pontuacao)
            .where(
                documento.op("@@")(busca),
                sem_vetor if so_alertas_sem_vetor else or_(do_modelo, sem_vetor),
            )
            .ext(distinct_on(TrechoAlerta.alerta_id, TrechoAlerta.inicio, TrechoAlerta.fim))
            .order_by(
                TrechoAlerta.alerta_id, TrechoAlerta.inicio, TrechoAlerta.fim, TrechoAlerta.id
            )
            .subquery()
        )
        colunas = candidatos.c
        ordenado = (
            select(candidatos)
            .order_by(colunas.pontuacao.desc(), colunas.alerta_id, colunas.posicao)
            .limit(limite)
        )
        return [
            TrechoRecuperado(
                alerta_id=a,
                posicao=p,
                inicio=i,
                fim=f,
                paises=tuple(ps),
                em_vigor=self._em_vigor(vigor, paises, geral),
                aviso_geral=geral,
                pontuacao=float(r),
            )
            for a, p, i, f, ps, vigor, geral, r in self._sessao.execute(ordenado)
        ]
