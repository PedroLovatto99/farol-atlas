"""Repositórios: o único lugar do backend que fala SQL."""

from farol.dominio.repositorios.alertas import AlertaRepositorio
from farol.dominio.repositorios.banco import BancoRepositorio
from farol.dominio.repositorios.classificacoes import ClassificacaoRepositorio
from farol.dominio.repositorios.contagens_chat import ContagemChatRepositorio, dia_em_brasilia
from farol.dominio.repositorios.execucoes import ExecucaoRepositorio
from farol.dominio.repositorios.fontes import FonteDadosRepositorio
from farol.dominio.repositorios.postos import PostoRepositorio
from farol.dominio.repositorios.territorios import TerritorioRepositorio
from farol.dominio.repositorios.trechos_alerta import (
    AlertaCitado,
    AlertaElegivel,
    NovoTrecho,
    TrechoAlertaRepositorio,
    TrechoGravado,
    TrechoRecuperado,
)
from farol.dominio.repositorios.vistos import (
    ColetaVistosRepositorio,
    ItemParaRevisaoRepositorio,
    MudancaRetidaRepositorio,
    RequisitoVistoRepositorio,
)

__all__ = [
    "AlertaCitado",
    "AlertaElegivel",
    "AlertaRepositorio",
    "BancoRepositorio",
    "ClassificacaoRepositorio",
    "ColetaVistosRepositorio",
    "ContagemChatRepositorio",
    "ExecucaoRepositorio",
    "FonteDadosRepositorio",
    "ItemParaRevisaoRepositorio",
    "MudancaRetidaRepositorio",
    "NovoTrecho",
    "PostoRepositorio",
    "RequisitoVistoRepositorio",
    "TerritorioRepositorio",
    "TrechoAlertaRepositorio",
    "TrechoGravado",
    "TrechoRecuperado",
    "dia_em_brasilia",
]
