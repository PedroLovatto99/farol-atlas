"""Chat de dúvidas de viagem (feature 003): interface pública do módulo.

Traz os contratos (`protocolos`), a indexação e a busca dos trechos dos alertas e o pipeline de
uma pergunta (entendimento, agente, verificador e montador). O chat não importa `mapa`,
`vistos`, `coleta` nem `classificacao`: o que ele precisa deles chega por Protocols (implementados
em `farol.api`) ou como argumento (o `vigor` da indexação, calculado pelo `worker`).
"""

from farol.chat.agente import RespostaDoModelo, ServicoDoModeloIndisponivel
from farol.chat.embeddador import EmbeddadorGoogle, criar_embeddador
from farol.chat.entendimento import MensagemAnterior
from farol.chat.fatiamento import fatiar
from farol.chat.indexador import (
    Andamento,
    ModeloNoIndice,
    ResumoDaIndexacao,
    ResumoDaReindexacao,
    SituacaoDoIndice,
    consultar_situacao,
    indexar_pendentes,
    reindexar,
)
from farol.chat.modelo import ModeloDoChat, ModeloDoChatIndisponivel, criar_modelo_do_chat
from farol.chat.montador import Citacao, RespostaMontada
from farol.chat.pipeline import (
    EventoDeErro,
    EventoDeProgresso,
    EventoDeResposta,
    EventoDoChat,
    PipelineDoChat,
    com_prazo,
)
from farol.chat.protocolos import (
    AlertaQueRege,
    NivelConsultado,
    PaisEncontrado,
    ResultadoDaResolucao,
)
from farol.chat.recuperacao import RecuperadorDeTrechos, TrechoEncontrado

__all__ = [
    "AlertaQueRege",
    "Andamento",
    "Citacao",
    "EmbeddadorGoogle",
    "EventoDeErro",
    "EventoDeProgresso",
    "EventoDeResposta",
    "EventoDoChat",
    "MensagemAnterior",
    "ModeloDoChat",
    "ModeloDoChatIndisponivel",
    "ModeloNoIndice",
    "NivelConsultado",
    "PaisEncontrado",
    "PipelineDoChat",
    "RecuperadorDeTrechos",
    "RespostaDoModelo",
    "RespostaMontada",
    "ResultadoDaResolucao",
    "ResumoDaIndexacao",
    "ResumoDaReindexacao",
    "ServicoDoModeloIndisponivel",
    "SituacaoDoIndice",
    "TrechoEncontrado",
    "com_prazo",
    "consultar_situacao",
    "criar_embeddador",
    "criar_modelo_do_chat",
    "fatiar",
    "indexar_pendentes",
    "reindexar",
]
