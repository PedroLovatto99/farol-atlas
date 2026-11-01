"""Recuperação dos trechos que respondem a uma pergunta (busca vetorial, com plano B por texto).

Devolve poucos trechos (quatro, por padrão), filtrados pelo país da pergunta quando há um. Por
padrão só entram alertas em vigor: com país, os em vigor para ele; sem país, os em vigor para algum
país. Um alerta anterior (que não rege mais nível nenhum) não ocupa vaga numa pergunta normal. Com
`so_em_vigor=False` os anteriores voltam, e então o alerta que rege o nível do país entra se for
parecido o bastante com a pergunta, para a resposta não ficar só com avisos antigos. Se o serviço
de embeddings falhar, a busca por texto (sem diferença de acento) responde no lugar (o chat segue
funcionando, só com menos finura). Alertas que ainda não têm vetor
do modelo configurado (troca de modelo no meio do caminho) também entram pela busca por texto.
Número fixo de consultas por pergunta: no máximo quatro, qualquer que seja o tamanho do índice.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from farol.chat.protocolos import Embeddador
from farol.dominio import TrechoAlertaRepositorio, TrechoRecuperado
from farol.infra import obter_logger

_log = obter_logger("farol.chat")

LIMITE_DE_TRECHOS = 4
# Distância de cosseno até a qual o alerta que rege o nível "é parecido com a pergunta". É um ponto
# de partida: o gabarito de recuperação (T050/T052) é quem calibra o valor para o modelo real.
DISTANCIA_MAXIMA_DO_VIGOR = 0.45

_PALAVRA = re.compile(r"\w{3,}")


@dataclass(frozen=True)
class TrechoEncontrado:
    alerta_id: int
    posicao: int
    inicio: int  # o trecho é sempre `alerta.texto[inicio:fim]`
    fim: int
    em_vigor: bool  # o alerta rege o nível do país da pergunta
    origem: str  # "vetorial" ou "textual"
    distancia: float | None = None  # cosseno; só na busca vetorial


def _de(trecho: TrechoRecuperado, origem: str) -> TrechoEncontrado:
    return TrechoEncontrado(
        alerta_id=trecho.alerta_id,
        posicao=trecho.posicao,
        inicio=trecho.inicio,
        fim=trecho.fim,
        em_vigor=trecho.em_vigor,
        origem=origem,
        distancia=trecho.distancia if origem == "vetorial" else None,
    )


class RecuperadorDeTrechos:
    def __init__(
        self,
        sessao: Session,
        embeddador: Embeddador,
        *,
        modelo: str,
        dimensoes: int,
        limite: int = LIMITE_DE_TRECHOS,
        distancia_maxima_do_vigor: float = DISTANCIA_MAXIMA_DO_VIGOR,
    ) -> None:
        self._repo = TrechoAlertaRepositorio(sessao)
        self._embeddador = embeddador
        self._modelo = modelo
        self._dimensoes = dimensoes
        self._limite = limite
        self._distancia_do_vigor = distancia_maxima_do_vigor

    def recuperar(
        self, pergunta: str, paises: Sequence[str] | None = None, *, so_em_vigor: bool = True
    ) -> list[TrechoEncontrado]:
        paises = list(paises) if paises else None
        try:
            vetor = self._embeddador.vetorizar_pergunta(pergunta)
        except Exception as erro:
            # só o tipo do erro vai ao log: a pergunta não é registrada em lugar nenhum
            _log.warning("embedding da pergunta falhou (%s); busca por texto", type(erro).__name__)
            return self._por_texto(
                pergunta, paises, self._limite, so_sem_vetor=False, so_em_vigor=so_em_vigor
            )

        achados = [
            _de(t, "vetorial")
            for t in self._repo.recuperar_por_similaridade(
                vetor,
                modelo=self._modelo,
                dimensoes=self._dimensoes,
                limite=self._limite,
                paises=paises,
                so_em_vigor=so_em_vigor,
            )
        ]
        if paises and not so_em_vigor:
            achados = self._com_o_que_rege(vetor, paises, achados)
        if self._repo.alertas_sem_vetor(self._modelo, self._dimensoes):
            vagas = self._limite - len(achados)
            if vagas > 0:
                achados += self._por_texto(
                    pergunta, paises, vagas, so_sem_vetor=True, so_em_vigor=so_em_vigor
                )
        return achados

    def _com_o_que_rege(
        self, vetor: Sequence[float], paises: list[str], achados: list[TrechoEncontrado]
    ) -> list[TrechoEncontrado]:
        """Garante um trecho do alerta que rege o nível, se ele for parecido com a pergunta."""
        regentes = self._repo.recuperar_por_similaridade(
            vetor,
            modelo=self._modelo,
            dimensoes=self._dimensoes,
            limite=1,
            paises=paises,
            so_em_vigor=True,
        )
        if not regentes or regentes[0].distancia > self._distancia_do_vigor:
            return achados
        if regentes[0].alerta_id in {a.alerta_id for a in achados}:
            return achados
        regente = _de(regentes[0], "vetorial")
        if len(achados) >= self._limite:
            achados = achados[: self._limite - 1]  # sai o menos parecido
        return [*achados, regente]

    def _por_texto(
        self,
        pergunta: str,
        paises: list[str] | None,
        limite: int,
        *,
        so_sem_vetor: bool,
        so_em_vigor: bool,
    ) -> list[TrechoEncontrado]:
        palavras = _PALAVRA.findall(pergunta)
        if not palavras:
            return []
        return [
            _de(t, "textual")
            for t in self._repo.recuperar_por_texto(
                " or ".join(palavras),
                modelo=self._modelo,
                dimensoes=self._dimensoes,
                limite=limite,
                paises=paises,
                so_em_vigor=so_em_vigor,
                so_alertas_sem_vetor=so_sem_vetor,
            )
        ]
