"""Linha de comando do worker.

python -m farol.worker                      fica de pé e coleta no horário agendado
python -m farol.worker coletar --alertas    uma rodada agora (coleta + classificação) e sai
"""

import argparse
from collections.abc import Callable, Sequence

from farol.dominio import ExecucaoRepositorio, TipoExecucao
from farol.infra import (
    RelogioDoSistema,
    abrir_sessao,
    configurar_logs,
    obter_configuracoes,
    obter_logger,
)
from farol.worker.agenda import preparar_agendador
from farol.worker.jobs import ContatoInvalido, ResultadoDaRodada, rodada_real

_log = obter_logger("farol.worker")


def _montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m farol.worker", description=__doc__)
    comandos = parser.add_subparsers(dest="comando")
    coletar = comandos.add_parser("coletar", help="roda uma coleta agora e sai")
    alvo = coletar.add_mutually_exclusive_group(required=True)
    alvo.add_argument("--alertas", action="store_true", help="alertas do Portal Consular")
    alvo.add_argument("--postos", action="store_true", help="endereço e telefone dos postos")
    return parser


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


def executar_comando(argumentos: Sequence[str], *, rodada: Callable[[], ResultadoDaRodada]) -> int:
    """Executa um comando de coleta única. Devolve o código de saída."""
    escolhido = _montar_parser().parse_args(list(argumentos))
    if escolhido.comando != "coletar":
        raise SystemExit(2)  # sem comando: quem chama sobe o agendador
    if escolhido.postos:
        print("A coleta de postos ainda não existe: ela é a última fase da feature.")
        return 2
    try:
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
        tentativa = ExecucaoRepositorio(sessao).ultima_tentativa(TipoExecucao.ALERTAS)
        ultima = tentativa.iniciada_em if tentativa is not None else None

    def rodada() -> None:
        resultado = rodada_real(configuracoes)
        _log.info("rodada concluída\n%s", _resumo(resultado))

    agendador = preparar_agendador(
        rodada,
        ultima_tentativa=ultima,
        agora=RelogioDoSistema().agora(),
        limite_horas=configuracoes.limite_horas_partida,
    )
    _log.info("worker iniciado: coleta diária às 06:17 (America/Sao_Paulo)")
    agendador.start()  # bloqueia até receber o sinal de parada


def main(argumentos: Sequence[str]) -> int:
    configurar_logs()
    if not argumentos:
        servir_agenda()
        return 0
    configuracoes = obter_configuracoes()
    return executar_comando(argumentos, rodada=lambda: rodada_real(configuracoes))
