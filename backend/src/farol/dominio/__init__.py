"""Domínio: modelos, enums e repositórios. É a interface pública usada pelas camadas de cima."""

from farol.dominio.enums import (
    NivelAlerta,
    StatusClassificacao,
    TipoExecucao,
    TipoPosto,
    TipoTerritorio,
)
from farol.dominio.modelos import (
    Alerta,
    Base,
    Classificacao,
    ExecucaoColeta,
    FonteDados,
    NivelTerritorio,
    Posto,
    Territorio,
)
from farol.dominio.repositorios import (
    AlertaRepositorio,
    BancoRepositorio,
    ClassificacaoRepositorio,
    ExecucaoRepositorio,
    FonteDadosRepositorio,
    PostoRepositorio,
    TerritorioRepositorio,
)

__all__ = [
    "Alerta",
    "AlertaRepositorio",
    "BancoRepositorio",
    "Base",
    "Classificacao",
    "ClassificacaoRepositorio",
    "ExecucaoColeta",
    "ExecucaoRepositorio",
    "FonteDados",
    "FonteDadosRepositorio",
    "NivelAlerta",
    "NivelTerritorio",
    "Posto",
    "PostoRepositorio",
    "StatusClassificacao",
    "Territorio",
    "TerritorioRepositorio",
    "TipoExecucao",
    "TipoPosto",
    "TipoTerritorio",
]
