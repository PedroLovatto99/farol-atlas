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


class CategoriaDeVisto(StrEnum):
    """Situação de visto de um território para brasileiros.

    A ordem de exigência é a ordem dos quatro primeiros membros (de `ISENTO` a `VISTO_EXIGIDO`);
    `OUTRA_SITUACAO` fica fora dela.
    """

    ISENTO = "isento"
    VISTO_NA_CHEGADA = "visto_na_chegada"
    AUTORIZACAO_ELETRONICA = "autorizacao_eletronica"
    VISTO_EXIGIDO = "visto_exigido"
    OUTRA_SITUACAO = "outra_situacao"


class MotivoOutraSituacao(StrEnum):
    ROTULO_CONHECIDO = "rotulo_conhecido"  # mapeado de propósito para "Outra situação"
    ROTULO_DESCONHECIDO = "rotulo_desconhecido"


class ResultadoDaColetaDeVistos(StrEnum):
    VALIDA = "valida"
    REJEITADA = "rejeitada"  # baixou, mas formato ou países reconhecidos não passaram
    ADIADA = "adiada"  # edição de menos de 24 horas
    FALHOU = "falhou"  # erro técnico
    BLOQUEADA = "bloqueada"  # 403, 429, verificação humana ou robots.txt


class EstadoDaRetencao(StrEnum):
    PENDENTE = "pendente"
    CONFIRMADA = "confirmada"
    REJEITADA = "rejeitada"
    REVERTIDA = "revertida"  # a fonte voltou ao valor exibido
    SUPERADA = "superada"  # a fonte mudou para outro valor


class TipoDeItemParaRevisao(StrEnum):
    NOME = "nome"
    ROTULO = "rotulo"
    REGRA = "regra"  # regra por país a reconfirmar


class EstadoDoItem(StrEnum):
    PENDENTE = "pendente"
    RESOLVIDO = "resolvido"
    IGNORADO = "ignorado"
