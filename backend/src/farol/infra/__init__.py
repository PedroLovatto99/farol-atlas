"""Infraestrutura: configuração, banco, relógio, logs e cliente HTTP. Camada mais baixa."""

from farol.infra.banco import (
    abrir_sessao,
    criar_engine,
    criar_fabrica_de_sessoes,
    obter_engine,
    obter_fabrica_de_sessoes,
)
from farol.infra.cliente_http import (
    Baixador,
    ClienteEducado,
    Pagina,
    RespostaHttp,
    SessaoHttp,
    parece_verificacao,
)
from farol.infra.config import Configuracoes, obter_configuracoes
from farol.infra.logs import configurar_logs, obter_logger
from farol.infra.modelo import argumentos_do_modelo
from farol.infra.relogio import FUSO_DE_BRASILIA, Relogio, RelogioDoSistema

__all__ = [
    "FUSO_DE_BRASILIA",
    "Baixador",
    "ClienteEducado",
    "Configuracoes",
    "Pagina",
    "Relogio",
    "RelogioDoSistema",
    "RespostaHttp",
    "SessaoHttp",
    "abrir_sessao",
    "argumentos_do_modelo",
    "configurar_logs",
    "criar_engine",
    "criar_fabrica_de_sessoes",
    "obter_configuracoes",
    "obter_engine",
    "obter_fabrica_de_sessoes",
    "obter_logger",
    "parece_verificacao",
]
