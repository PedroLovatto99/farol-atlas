"""A rodada de alertas do worker: coletar → (se completa, confirmar) → classificar (D5).

A confirmação acontece dentro da coleta, ao fim de uma execução completa. A classificação roda
sempre depois: mesmo após uma coleta incompleta ela deixa pronta a classificação do que foi lido,
para quando uma coleta completa o confirmar. Cada etapa tem a sua transação: uma falha do LLM não
desfaz a coleta já gravada.
"""

from collections.abc import Callable
from dataclasses import dataclass

from farol.classificacao import (
    ClassificadorDeAlertas,
    ResultadoDaClassificacao,
    ResultadoDaReclassificacao,
    ServicoDeClassificacao,
    criar_modelo,
)
from farol.coleta import (
    ClienteEducado,
    ResultadoDaColeta,
    ResultadoDaColetaDePostos,
    ServicoDeColetaDeAlertas,
    ServicoDeColetaDePostos,
)
from farol.infra import Configuracoes, RelogioDoSistema, abrir_sessao, obter_logger

_log = obter_logger("farol.worker")

# Valor do .env.example: quem não trocou ainda não se identificou de verdade
CONTATO_DE_EXEMPLO = "https://github.com/seu-usuario"


class ContatoInvalido(RuntimeError):
    """CONTATO_COLETA ausente ou ainda com o valor de exemplo: a coleta não começa."""


class ClassificadorIndisponivel(RuntimeError):
    """Sem chave ou sem modelo configurado: não há como reclassificar."""


@dataclass(frozen=True)
class ResultadoDaRodada:
    coleta: ResultadoDaColeta
    classificacao: ResultadoDaClassificacao


def rodada_de_alertas(
    coletar: Callable[[], ResultadoDaColeta],
    classificar: Callable[[], ResultadoDaClassificacao],
) -> ResultadoDaRodada:
    coleta = coletar()
    classificacao = classificar()
    return ResultadoDaRodada(coleta, classificacao)


def _cliente_educado(configuracoes: Configuracoes) -> ClienteEducado:
    contato = (configuracoes.contato_coleta or "").strip()
    if not contato or contato == CONTATO_DE_EXEMPLO:
        raise ContatoInvalido(
            "defina CONTATO_COLETA no .env com o seu contato (URL ou e-mail): "
            "ele vai no User-Agent da coleta"
        )
    return ClienteEducado(contato, pausa_segundos=configuracoes.pausa_segundos)


def rodada_real_de_postos(configuracoes: Configuracoes) -> ResultadoDaColetaDePostos:
    """Coleta de postos de verdade: gov.br e banco (sem LLM)."""
    cliente = _cliente_educado(configuracoes)
    with abrir_sessao() as sessao:
        return ServicoDeColetaDePostos(sessao, cliente, RelogioDoSistema()).coletar()


def reclassificar_real(configuracoes: Configuracoes, referencia: str) -> ResultadoDaReclassificacao:
    """Reclassifica um alerta (id ou URL) com o modelo de LLM_CLASSIFICADOR. Não coleta nada."""
    try:
        modelo, nome = criar_modelo(configuracoes)
    except Exception as erro:
        raise ClassificadorIndisponivel(
            f"não foi possível criar o modelo {configuracoes.llm_classificador!r}: {erro}"
        ) from erro
    with abrir_sessao() as sessao:
        servico = ServicoDeClassificacao(
            sessao, ClassificadorDeAlertas(modelo, nome), RelogioDoSistema()
        )
        return servico.reclassificar(referencia)


def rodada_real(configuracoes: Configuracoes) -> ResultadoDaRodada:
    """Uma rodada de verdade: gov.br, banco e o modelo configurado em LLM_CLASSIFICADOR."""
    relogio = RelogioDoSistema()

    def coletar() -> ResultadoDaColeta:
        cliente = _cliente_educado(configuracoes)
        with abrir_sessao() as sessao:
            return ServicoDeColetaDeAlertas(sessao, cliente, relogio).coletar()

    def classificar() -> ResultadoDaClassificacao:
        try:
            modelo, nome = criar_modelo(configuracoes)
        except Exception:
            # sem chave ou sem modelo: os alertas novos ficam pendentes e o site segue no ar
            _log.exception("classificador indisponível; os alertas novos ficam pendentes")
            return ResultadoDaClassificacao(0, 0)
        with abrir_sessao() as sessao:
            servico = ServicoDeClassificacao(sessao, ClassificadorDeAlertas(modelo, nome), relogio)
            return servico.classificar_pendentes()

    return rodada_de_alertas(coletar, classificar)
