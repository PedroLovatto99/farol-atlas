"""Processo do worker. Por ora só fica de pé; as coletas agendadas chegam na história P1 (US1)."""

import threading

from farol.infra import configurar_logs, obter_logger


def main() -> None:
    configurar_logs()
    obter_logger("farol.worker").info("worker iniciado; ainda sem tarefas agendadas")
    threading.Event().wait()  # mantém o processo vivo até receber o sinal de parada


if __name__ == "__main__":
    main()
