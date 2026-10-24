"""Enumerações do domínio. Os valores gravados no banco são os de `value`."""

from enum import StrEnum


class TipoTerritorio(StrEnum):
    PAIS = "pais"
    DEPENDENCIA = "dependencia"
    NEUTRO = "neutro"


class TipoPosto(StrEnum):
    EMBAIXADA = "Embaixada"
    CONSULADO_GERAL = "Consulado-Geral"
    CONSULADO = "Consulado"
    VICE_CONSULADO = "Vice-Consulado"
    ESCRITORIO_DE_REPRESENTACAO = "Escritório de Representação"
    ESCRITORIO_COMERCIAL = "Escritório Comercial"


class NivelAlerta(StrEnum):
    """Nível que um alerta atribui a um país ou região."""

    EVITAR = "evitar"
    NAO_VIAJAR = "nao_viajar"
    NORMALIZADA = "normalizada"  # o alerta informa o fim do problema


class StatusClassificacao(StrEnum):
    OK = "ok"
    FALHOU = "falhou"


class TipoExecucao(StrEnum):
    ALERTAS = "alertas"
    POSTOS = "postos"
