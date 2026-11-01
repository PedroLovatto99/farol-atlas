"""`ResolvedorDePaises` e `ConsultaDeNivel` do chat, sobre as mesmas funções do painel e do mapa."""

from sqlalchemy.orm import Session

from farol.chat import (
    AlertaQueRege,
    NivelConsultado,
    PaisEncontrado,
    ResultadoDaResolucao,
)
from farol.dominio import (
    AlertaRepositorio,
    ExecucaoRepositorio,
    Territorio,
    TipoExecucao,
)
from farol.mapa import ProcuradorDeTerritorios, montar_painel


class ResolvedorDePaisesDoSite:
    """Acha países e territórios num texto com o `ProcuradorDeTerritorios` (nomes da busca do site,
    sem acento, por palavra inteira, o nome mais longo vence e um nome ambíguo nunca escolhe)."""

    def __init__(self, sessao: Session) -> None:
        self._procurador = ProcuradorDeTerritorios(sessao)

    @staticmethod
    def _achado(territorio: Territorio) -> PaisEncontrado:
        return PaisEncontrado(
            codigo=territorio.codigo, nome=territorio.nome_pt, soberano=territorio.soberano_codigo
        )

    def resolver(self, texto: str) -> ResultadoDaResolucao:
        citados = self._procurador.procurar(texto)
        return ResultadoDaResolucao(
            encontrados=tuple(self._achado(t) for t in citados.encontrados),
            ambiguos=tuple(tuple(self._achado(t) for t in grupo) for grupo in citados.ambiguos),
        )


class ConsultaDeNivelDoSite:
    """O nível de um território, exatamente como o painel o monta (`montar_painel`)."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def consultar(self, codigo: str) -> NivelConsultado:
        visao = montar_painel(self._sessao, codigo)
        ultima = ExecucaoRepositorio(self._sessao).ultima_completa(TipoExecucao.ALERTAS)
        regente = next((a for a in visao.alertas if a.define_nivel), None)
        alerta_que_rege = None
        if regente is not None:
            alerta = AlertaRepositorio(self._sessao).obter_por_url(regente.url)
            if alerta is not None:
                alerta_que_rege = AlertaQueRege(
                    id=alerta.id,
                    titulo=regente.titulo,
                    data=regente.modificado_em or regente.publicado_em,
                    url=regente.url,
                )
        return NivelConsultado(
            codigo=visao.codigo,
            nome=visao.nome,
            nivel=visao.nivel.value,
            regioes=tuple(r.nome for r in visao.regioes),
            so_regional=visao.regiao_unica_do_alerta,
            alerta_que_rege=alerta_que_rege,
            observacao=visao.observacao,
            atualizado_em=ultima.finalizada_em if ultima is not None else None,
            dados_obtidos=ultima is not None,
        )
