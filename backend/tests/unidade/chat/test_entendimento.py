"""Entendimento da pergunta: de que país se fala (e quando perguntar de volta, sem chamar o modelo).

O país vem da pergunta atual e, na falta, das mensagens anteriores DA PESSOA. O que o assistente
disse antes nunca conta, e o país aberto no mapa também não.
"""

from farol.chat.entendimento import MensagemAnterior, entender
from farol.chat.protocolos import PaisEncontrado, ResultadoDaResolucao

IRA = PaisEncontrado("IR", "Irã")
LIBANO = PaisEncontrado("LB", "Líbano")
CONGO = PaisEncontrado("CG", "Rep. do Congo")
CONGO_RD = PaisEncontrado("CD", "Rep. Dem. do Congo")


class ResolvedorFalso:
    """Acha países por palavra e conhece um nome ambíguo; guarda o que lhe perguntaram."""

    def __init__(self) -> None:
        self.textos: list[str] = []

    def resolver(self, texto: str) -> ResultadoDaResolucao:
        self.textos.append(texto)
        minusculo = texto.lower()
        if "congo" in minusculo:
            return ResultadoDaResolucao(ambiguos=((CONGO, CONGO_RD),))
        achados = tuple(p for nome, p in (("irã", IRA), ("líbano", LIBANO)) if nome in minusculo)
        return ResultadoDaResolucao(encontrados=achados)


def pessoa(texto: str) -> MensagemAnterior:
    return MensagemAnterior("pessoa", texto)


def assistente(texto: str) -> MensagemAnterior:
    return MensagemAnterior("assistente", texto)


def test_pais_da_pergunta_atual() -> None:
    entendimento = entender("O que o Itamaraty recomenda para o Irã?", [], ResolvedorFalso())
    assert entendimento.paises == (IRA,)
    assert entendimento.pergunta_de_volta is None


def test_mais_de_um_pais_na_pergunta() -> None:
    entendimento = entender("E o Irã e o Líbano?", [], ResolvedorFalso())
    assert entendimento.paises == (IRA, LIBANO)


def test_sem_pais_e_sem_historico_pergunta_de_volta() -> None:
    entendimento = entender("Posso levar remédios?", [], ResolvedorFalso())
    assert entendimento.paises == ()
    assert entendimento.pergunta_de_volta is not None
    assert "país" in entendimento.pergunta_de_volta


def test_sem_pais_usa_o_pais_da_ultima_mensagem_da_pessoa() -> None:
    historico = [pessoa("Como está o Líbano?"), assistente("Há um alerta."), pessoa("E o Irã?")]
    entendimento = entender("Preciso de visto?", historico, ResolvedorFalso())
    assert entendimento.paises == (IRA,)  # a mais recente da pessoa


def test_o_que_o_assistente_disse_nunca_define_pais() -> None:
    historico = [assistente("O Irã tem alerta de não viajar.")]
    entendimento = entender("E o visto?", historico, ResolvedorFalso())
    assert entendimento.paises == ()
    assert entendimento.pergunta_de_volta is not None


def test_pais_da_pergunta_vale_mais_que_o_do_historico() -> None:
    entendimento = entender("E o Líbano?", [pessoa("Como está o Irã?")], ResolvedorFalso())
    assert entendimento.paises == (LIBANO,)


def test_nome_ambiguo_pergunta_de_volta_com_as_opcoes() -> None:
    entendimento = entender("Como está o Congo?", [pessoa("Como está o Irã?")], ResolvedorFalso())
    assert entendimento.paises == ()
    texto = entendimento.pergunta_de_volta or ""
    assert "Rep. do Congo" in texto and "Rep. Dem. do Congo" in texto


def test_nome_ambiguo_no_historico_e_ignorado() -> None:
    historico = [pessoa("Como está o Congo?")]
    entendimento = entender("E o visto?", historico, ResolvedorFalso())
    assert entendimento.paises == ()
    assert entendimento.pergunta_de_volta is not None


def test_a_pergunta_atual_so_chega_ao_resolvedor_como_texto() -> None:
    resolvedor = ResolvedorFalso()
    entender("Irã", [pessoa("oi")], resolvedor)
    assert resolvedor.textos == ["Irã"]  # achou na pergunta: nem olhou o histórico
