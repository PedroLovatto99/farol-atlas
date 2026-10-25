"""Linha de comando do worker.

python -m farol.worker                      fica de pé e coleta no horário agendado
python -m farol.worker coletar --alertas    uma rodada agora (coleta + classificação) e sai
python -m farol.worker coletar --postos     coleta endereço e telefone dos postos agora e sai
python -m farol.worker reclassificar <id|url>   chama o modelo de novo para um alerta e sai
"""

import argparse
from collections.abc import Callable, Sequence

from farol.classificacao import (
    AlertaNaoEncontrado,
    ResultadoDaReclassificacao,
)
from farol.coleta import ResultadoDaColetaDePostos
from farol.dominio import ExecucaoRepositorio, TipoExecucao
from farol.infra import (
    RelogioDoSistema,
    abrir_sessao,
    configurar_logs,
    obter_configuracoes,
    obter_logger,
)
from farol.worker.agenda import preparar_agendador
from farol.worker.jobs import (
    ClassificadorIndisponivel,
    ContatoInvalido,
    ResultadoDaRodada,
    reclassificar_real,
    rodada_real,
    rodada_real_de_postos,
)

_log = obter_logger("farol.worker")


def _montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m farol.worker", description=__doc__)
    comandos = parser.add_subparsers(dest="comando")
    coletar = comandos.add_parser("coletar", help="roda uma coleta agora e sai")
    alvo = coletar.add_mutually_exclusive_group(required=True)
    alvo.add_argument("--alertas", action="store_true", help="alertas do Portal Consular")
    alvo.add_argument("--postos", action="store_true", help="endereço e telefone dos postos")
    reclassificar = comandos.add_parser(
        "reclassificar", help="refaz a classificação de um alerta (não coleta nada)"
    )
    reclassificar.add_argument("alerta", help="id do alerta no banco ou a URL dele")
    return parser


def _resumo_da_reclassificacao(resultado: ResultadoDaReclassificacao) -> str:
    if resultado.ok:
        return f"Alerta {resultado.alerta_id} reclassificado: {resultado.titulo}\n{resultado.url}"
    return (
        f"Alerta {resultado.alerta_id} NÃO reclassificado: {resultado.motivo}\n"
        "A classificação que valia continua valendo."
    )


def _reclassificar(
    referencia: str, reclassificar: Callable[[str], ResultadoDaReclassificacao]
) -> int:
    try:
        resultado = reclassificar(referencia)
    except AlertaNaoEncontrado:
        print(f"Não há alerta com o id ou a URL {referencia!r}.")
        return 2
    except ClassificadorIndisponivel as erro:
        print(f"Não foi possível reclassificar: {erro}")
        return 2
    print(_resumo_da_reclassificacao(resultado))
    return 0 if resultado.ok else 1


def _resumo(resultado: ResultadoDaRodada) -> str:
    coleta, classificacao = resultado.coleta, resultado.classificacao
    linhas = [
        f"Coleta {'completa' if coleta.completa else 'INCOMPLETA'}: "
        f"{coleta.paginas_lidas} de {coleta.paginas_esperadas} páginas lidas",
        f"Alertas novos ou alterados: {len(coleta.para_classificar)}"
        f" | removidos: {coleta.removidos}",
        f"Classificação: {classificacao.classificados} ok, {classificacao.falhas} com falha",
    ]
    if coleta.motivo_interrupcao:
        linhas.insert(1, f"Motivo: {coleta.motivo_interrupcao}")
    return "\n".join(linhas)


def _resumo_de_postos(resultado: ResultadoDaColetaDePostos) -> str:
    linhas = [
        f"Coleta de postos {'completa' if resultado.completa else 'INCOMPLETA'}: "
        f"{resultado.paginas_lidas} de {resultado.paginas_esperadas} páginas lidas",
        f"Postos com endereço: {resultado.postos_com_endereco}"
        f" | com telefone: {resultado.postos_com_telefone}",
    ]
    if resultado.motivo_interrupcao:
        linhas.insert(1, f"Motivo: {resultado.motivo_interrupcao}")
    return "\n".join(linhas)


def executar_comando(
    argumentos: Sequence[str],
    *,
    rodada: Callable[[], ResultadoDaRodada],
    rodada_de_postos: Callable[[], ResultadoDaColetaDePostos],
    reclassificar: Callable[[str], ResultadoDaReclassificacao] | None = None,
) -> int:
    """Executa um comando de execução única. Devolve o código de saída."""
    escolhido = _montar_parser().parse_args(list(argumentos))
    if escolhido.comando == "reclassificar" and reclassificar is not None:
        return _reclassificar(escolhido.alerta, reclassificar)
    if escolhido.comando != "coletar":
        raise SystemExit(2)  # sem comando: quem chama sobe o agendador
    try:
        if escolhido.postos:
            resultado_de_postos = rodada_de_postos()
            print(_resumo_de_postos(resultado_de_postos))
            return 0 if resultado_de_postos.completa else 1
        resultado = rodada()
    except ContatoInvalido as erro:
        print(f"Não foi possível coletar: {erro}")
        return 2
    print(_resumo(resultado))
    return 0 if resultado.coleta.completa else 1


def servir_agenda() -> None:
    """Fica de pé coletando todo dia (e na partida, se a última tentativa for antiga)."""
    configuracoes = obter_configuracoes()
    with abrir_sessao() as sessao:
        execucoes = ExecucaoRepositorio(sessao)
        tentativa = execucoes.ultima_tentativa(TipoExecucao.ALERTAS)
        tentativa_de_postos = execucoes.ultima_tentativa(TipoExecucao.POSTOS)
        ultima = tentativa.iniciada_em if tentativa is not None else None
        ultima_de_postos = tentativa_de_postos.iniciada_em if tentativa_de_postos else None

    def rodada() -> None:
        resultado = rodada_real(configuracoes)
        _log.info("rodada concluída\n%s", _resumo(resultado))

    def rodada_de_postos() -> None:
        resultado = rodada_real_de_postos(configuracoes)
        _log.info("rodada de postos concluída\n%s", _resumo_de_postos(resultado))

    agendador = preparar_agendador(
        rodada,
        ultima_tentativa=ultima,
        agora=RelogioDoSistema().agora(),
        limite_horas=configuracoes.limite_horas_partida,
        rodada_de_postos=rodada_de_postos,
        ultima_tentativa_de_postos=ultima_de_postos,
    )
    _log.info(
        "worker iniciado: alertas todo dia às 06:17 e postos todo dia 1 às 05:43 "
        "(America/Sao_Paulo)"
    )
    agendador.start()  # bloqueia até receber o sinal de parada


def main(argumentos: Sequence[str]) -> int:
    configurar_logs()
    if not argumentos:
        servir_agenda()
        return 0
    configuracoes = obter_configuracoes()
    return executar_comando(
        argumentos,
        rodada=lambda: rodada_real(configuracoes),
        rodada_de_postos=lambda: rodada_real_de_postos(configuracoes),
        reclassificar=lambda referencia: reclassificar_real(configuracoes, referencia),
    )
