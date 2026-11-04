"""Textos fixos do chat (contracts/textos-do-chat.md). O modelo nunca escreve a resposta (FR-001).

Os rótulos são os mesmos do painel (`compartilhado/niveis.ts` e `compartilhado/vistos.ts`).
"""

from collections.abc import Sequence
from datetime import datetime

from farol.infra import FUSO_DE_BRASILIA

URL_DO_PORTAL_CONSULAR = "https://www.gov.br/mre/pt-br/assuntos/portal-consular"
NOME_DO_PORTAL = "Portal Consular do Itamaraty"

ROTULOS_DE_NIVEL = {
    "evitar": "Evite viagens não essenciais",
    "nao_viajar": "Não viaje",
}
ALERTA_SO_REGIONAL = "Alerta só para parte do país"
AVISO_ALERTA_DESATUALIZADO = (
    "Dados desatualizados: a última atualização completa tem mais de 3 dias."
)

ROTULOS_DE_VISTO = {
    "isento": "Isento de visto",
    "visto_na_chegada": "Visto na chegada",
    "autorizacao_eletronica": "Autorização ou visto eletrônico",
    "visto_exigido": "Visto exigido",
    "outra_situacao": "Outra situação",
    "sem_informacao": "Sem informação de visto",
}
VARIA_CONFORME_O_MOTIVO = "Varia conforme o motivo da viagem"
PERMANENCIA_VARIA = "Varia conforme o motivo (ver observações)"
PERMANENCIA_DIVERGENTE = "Prazos divergentes na fonte (ver observações)"
AVISO_NAO_OFICIAL = (
    "Informação não oficial. Confirme com o consulado ou embaixada do país antes da viagem."
)
AVISO_VISTO_DESATUALIZADO = (
    "Estes dados podem estar desatualizados: foram lidos da fonte há mais de 14 dias."
)

PEDIR_PAIS = (
    'De qual país você quer saber? Pergunte citando o nome, por exemplo: "Preciso de visto para '
    'o Japão?"'
)
BRASIL = "Eu respondo sobre viagens de brasileiros ao exterior. Para qual país você vai?"
FORA_DO_ASSUNTO = (
    "Eu informo o nível de alerta do Itamaraty e a situação de visto para brasileiros em cada "
    'país, por exemplo: "Como está o alerta para o Peru?". Para o resto, como postos e o conteúdo '
    "dos alertas, abra o painel do país no mapa."
)
REFORMULAR = "Não consegui entender de qual país você fala. Pode reformular citando o nome do país?"


def data(instante: datetime) -> str:
    return instante.astimezone(FUSO_DE_BRASILIA).strftime("%d/%m/%Y")


def frase_do_alerta(nivel: str, pais: str, so_regional: bool, dados_obtidos: bool) -> str:
    if nivel == "nao_viajar":
        return f'Para {pais}, o Itamaraty recomenda não viajar (nível "Não viaje").'
    if nivel == "evitar":
        return (
            f"Para {pais}, o Itamaraty recomenda evitar viagens não essenciais "
            '(nível "Evite viagens não essenciais").'
        )
    if nivel == "sem_alerta" and so_regional:
        return (
            f'Para {pais}, há "{ALERTA_SO_REGIONAL}": ele vale só para a região indicada, não '
            "para o país inteiro. Para o restante do país, a ausência de alerta não significa "
            "que o governo recomenda a viagem."
        )
    if nivel == "sem_alerta":
        return (
            f"Não há alerta de viagem do Itamaraty para {pais}. "
            "Isso não significa que o governo recomenda a viagem."
        )
    if dados_obtidos:
        return (
            f"O nível de alerta de {pais} não foi verificado: ainda não temos informação "
            "confirmada do Itamaraty."
        )
    return (
        f"Ainda não obtivemos os dados do Itamaraty, então o nível de alerta de {pais} não foi "
        "verificado."
    )


def frase_do_visto(situacao: str, pais: str, aceita_rg: bool) -> str:
    if situacao == "isento" and aceita_rg:
        return (
            f"Não, brasileiros não precisam de visto para {pais}, "
            "e a entrada pode ser feita com o RG."
        )
    if situacao == "isento":
        return f"Não, brasileiros não precisam de visto para {pais}."
    if situacao == "visto_na_chegada":
        return f"Brasileiros precisam de visto para {pais}, mas ele é obtido na chegada."
    if situacao == "autorizacao_eletronica":
        return (
            f"Brasileiros precisam de uma autorização ou visto eletrônico para {pais}, "
            "obtido antes da viagem."
        )
    if situacao == "visto_exigido":
        return f"Sim, brasileiros precisam de visto para {pais}."
    if situacao == "outra_situacao":
        return f"A situação de visto de {pais} não se encaixa nas categorias do site."
    return f"Sem informação de visto para {pais}. Isso não significa que a entrada seja livre."


def _lista(nomes: Sequence[str], conjuncao: str) -> str:
    return f"{', '.join(nomes[:-1])} {conjuncao} {nomes[-1]}"


def qual_dos_paises(nomes: Sequence[str]) -> str:
    return (
        f"Qual deles você quer saber: {_lista(nomes, 'ou')}? Pergunte de novo com o nome do país."
    )


def um_pais_por_vez(nomes: Sequence[str]) -> str:
    return (
        f"Entendi que você perguntou sobre {_lista(nomes, 'e')}. "
        "Pergunte sobre um país de cada vez, por favor."
    )


def limite_de_perguntas(perguntas: int, minutos: int) -> str:
    return (
        f"Você chegou ao limite de {perguntas} perguntas por hora. Tente de novo em {minutos} min."
    )
