"""Responde uma pergunta: entende pelo código, chama o modelo só se precisar e monta o texto fixo.

O modelo só escolhe o país e o assunto (FR-001); o que ele devolve é validado contra a lista de
territórios e nunca entra no texto. Sem modelo, ou se ele falhar, o chat responde pelo código
(FR-029). A pergunta nunca é logada (FR-028).
"""

from collections.abc import Mapping

from farol.chat import textos
from farol.chat.entendimento import (
    CODIGO_DO_BRASIL,
    Assunto,
    Entendimento,
    PaisCitado,
    Vocabulario,
    carregar_apelidos,
    decidir,
    entender,
    montar_vocabulario,
)
from farol.chat.portas import (
    FonteDoPainel,
    MapaLido,
    ModeloDeEntendimento,
    PalpiteDoModelo,
    Paragrafo,
    Resposta,
    TerritorioNaoEncontrado,
    TipoDeResposta,
    Trecho,
)
from farol.chat.respostas import paragrafos_do_alerta, paragrafos_do_visto
from farol.infra import obter_logger

_log = obter_logger("farol.chat")


def _fixa(tipo: TipoDeResposta, texto: str) -> Resposta:
    return Resposta(tipo, None, ((Trecho(texto),),))


class ServicoDoChat:
    def __init__(self, fonte: FonteDoPainel, modelo: ModeloDeEntendimento | None) -> None:
        self._fonte = fonte
        self._modelo = modelo

    def responder(self, pergunta: str) -> Resposta:
        mapa = self._fonte.mapa()
        codigos = {t.codigo for t in mapa.territorios}
        vocabulario = montar_vocabulario(mapa.territorios, carregar_apelidos(codigos))

        entendimento = entender(pergunta, vocabulario)
        if not entendimento.entendeu:
            entendimento = self._com_modelo(pergunta, entendimento, vocabulario)
            tem_pais = entendimento.paises or entendimento.brasil
            if not tem_pais and entendimento.assunto is not Assunto.FORA_DO_ASSUNTO:
                return _fixa(TipoDeResposta.REFORMULAR, textos.REFORMULAR)

        tipo, pais = decidir(entendimento)
        if tipo is TipoDeResposta.UM_PAIS_POR_VEZ:
            return _fixa(tipo, textos.um_pais_por_vez([p.nome for p in entendimento.paises]))
        if tipo is TipoDeResposta.BRASIL:
            return _fixa(tipo, textos.BRASIL)
        if tipo is TipoDeResposta.FORA_DO_ASSUNTO:
            return _fixa(tipo, textos.FORA_DO_ASSUNTO)
        if pais is None:
            return _fixa(TipoDeResposta.PEDIR_PAIS, textos.PEDIR_PAIS)
        if pais.ambiguo:
            nomes = pais.opcoes or [vocabulario.nomes[codigo] for codigo in pais.codigos]
            return _fixa(tipo, textos.qual_dos_paises(nomes))
        return self._com_dados(tipo, pais.codigos[0], mapa)

    def _com_modelo(
        self, pergunta: str, entendimento: Entendimento, vocabulario: Vocabulario
    ) -> Entendimento:
        """Completa o que o código não achou; o país do código vale mais que o do modelo."""
        palpite = self._palpite(pergunta, vocabulario.nomes)
        if palpite is None:
            return entendimento
        nomes = vocabulario.nomes
        codigos = [c for c in dict.fromkeys(palpite.codigos) if c in nomes]
        paises = tuple(PaisCitado(nomes[c], (c,)) for c in codigos if c != CODIGO_DO_BRASIL)
        assunto = Assunto(palpite.assunto) if palpite.assunto in Assunto else None
        return Entendimento(
            entendimento.paises or paises,
            entendimento.brasil or CODIGO_DO_BRASIL in codigos,
            entendimento.assunto or assunto,
            entendimento.sobra,
        )

    def _palpite(self, pergunta: str, nomes: Mapping[str, str]) -> PalpiteDoModelo | None:
        if self._modelo is None:
            return None
        try:
            return self._modelo.entender(pergunta, nomes)
        except Exception as erro:  # qualquer falha do modelo vale como "não respondeu"
            _log.warning("modelo do chat falhou", extra={"dados": {"erro": type(erro).__name__}})
            return None

    def _com_dados(self, tipo: TipoDeResposta, codigo: str, mapa: MapaLido) -> Resposta:
        try:
            dados = self._fonte.painel(codigo)
        except TerritorioNaoEncontrado:
            return _fixa(TipoDeResposta.REFORMULAR, textos.REFORMULAR)
        paragrafos: tuple[Paragrafo, ...] = ()
        if tipo is not TipoDeResposta.VISTO:
            paragrafos += paragrafos_do_alerta(dados.painel, mapa)
        if tipo is not TipoDeResposta.ALERTA and dados.visto is not None:
            paragrafos += paragrafos_do_visto(dados.visto, dados.painel.nome)
        return Resposta(tipo, codigo, paragrafos)
