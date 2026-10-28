"""Comandos dos vistos: `coletar --vistos` e o grupo `vistos` (contracts/comandos-do-dono.md).

`executar_comando` roda com falsos: a rodada de vistos devolve um resumo pronto e o serviço do dono
é um objeto que só registra o que lhe pediram. Nada acessa o banco, a rede nem um modelo.
"""

import io
from contextlib import nullcontext
from datetime import UTC, datetime

import pytest

from farol.coleta import ResultadoDaColetaDePostos
from farol.dominio import CategoriaDeVisto, ResultadoDaColetaDeVistos, TipoDeItemParaRevisao
from farol.vistos import (
    ErroDoDono,
    ItemPendente,
    MudancaPendente,
    PendenciasDoDono,
    ProximaTentativa,
    RegraPendente,
    ResumoDaColetaDeVistos,
    RetidaNaColeta,
)
from farol.worker import ContatoInvalido, ResultadoDaRodada, executar_comando
from farol.worker.comando import configurar_saida_em_utf8

R = ResultadoDaColetaDeVistos
C = CategoriaDeVisto
EDICAO = datetime(2026, 10, 19, 5, 8, tzinfo=UTC)
RETIDA_EM = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
EXIBIDO_DE = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
HASH_ESPERADO = "3f1a" + "0" * 60
HASH_NOVO = "9c07" + "1" * 60


def sem_alertas() -> ResultadoDaRodada:
    raise AssertionError("a coleta de alertas não devia rodar")


def sem_postos() -> ResultadoDaColetaDePostos:
    raise AssertionError("a coleta de postos não devia rodar")


# --------------------------------------------------------------------------- coletar --vistos
def resumo_valido(**campos: object) -> ResumoDaColetaDeVistos:
    base = {
        "coleta_id": 7,
        "resultado": R.VALIDA,
        "motivo": None,
        "proxima_tentativa": ProximaTentativa.PROXIMA_SEGUNDA,
        "paises_reconhecidos": 226,
        "minimo": 204,
        "revisao_fonte": 1380975986,
        "ultima_edicao_fonte": EDICAO,
        "aplicadas": 3,
        "sem_mudanca": 222,
        "retidas": (RetidaNaColeta("AR", C.VISTO_EXIGIDO, C.ISENTO, False, False),),
        "traducoes_novas": 4,
        "lotes_de_traducao": 1,
        "traducoes_falhas": 0,
    }
    return ResumoDaColetaDeVistos(**{**base, **campos})  # type: ignore[arg-type]


def resumo_nao_valido(
    resultado: ResultadoDaColetaDeVistos, motivo: str, proxima: ProximaTentativa
) -> ResumoDaColetaDeVistos:
    return ResumoDaColetaDeVistos(
        coleta_id=8, resultado=resultado, motivo=motivo, proxima_tentativa=proxima
    )


def coletar_vistos(
    resumo: ResumoDaColetaDeVistos,
) -> tuple[int, list[int]]:
    chamadas: list[int] = []

    def rodada_de_vistos() -> ResumoDaColetaDeVistos:
        chamadas.append(1)
        return resumo

    codigo = executar_comando(
        ["coletar", "--vistos"],
        rodada=sem_alertas,
        rodada_de_postos=sem_postos,
        rodada_de_vistos=rodada_de_vistos,
    )
    return codigo, chamadas


def test_coletar_vistos_roda_so_a_rodada_de_vistos_e_imprime_o_resumo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo, chamadas = coletar_vistos(resumo_valido())

    assert (codigo, chamadas) == (0, [1])
    assert capsys.readouterr().out.splitlines() == [
        "Coleta de vistos VÁLIDA: 226 países reconhecidos (mínimo 204)",
        "Artigo: revisão 1380975986, última edição em 19/10/2026 05:08 UTC",
        "Dados aplicados: 3 | sem mudança: 222 | retidos: 1",
        "Retidos (esperam confirmação; veja `vistos pendentes`):",
        "  AR  Visto exigido → Isento de visto",
        "Nomes não reconhecidos: 0 | rótulos não reconhecidos: 0",
        "Traduções: 4 novas (1 lote), 0 falhas",
    ]


def test_sem_retidas_o_resumo_nao_tem_a_lista(capsys: pytest.CaptureFixture[str]) -> None:
    codigo, _ = coletar_vistos(resumo_valido(retidas=(), aplicadas=0, sem_mudanca=226))

    saida = capsys.readouterr().out
    assert codigo == 0
    assert "retidos: 0" in saida
    assert "Retidos (esperam" not in saida


def test_o_resumo_mostra_o_que_a_coleta_nao_reconheceu(
    capsys: pytest.CaptureFixture[str],
) -> None:
    resumo = resumo_valido(
        nomes_nao_reconhecidos=("Atlantis", "Lemuria"),
        rotulos_nao_reconhecidos=("super visa",),
        regras_para_reconfirmar=("JM",),
        traducoes_falhas=2,
        lotes_de_traducao=3,
        traducoes_novas=0,
    )

    codigo, _ = coletar_vistos(resumo)

    saida = capsys.readouterr().out
    assert codigo == 0  # há pendência, mas a coleta foi válida
    assert "Nomes não reconhecidos: 2 | rótulos não reconhecidos: 1" in saida
    assert "Atlantis" in saida
    assert "Lemuria" in saida
    assert "super visa" in saida
    assert "JM" in saida  # regra por país a reconfirmar
    assert "Traduções: 0 novas (3 lotes), 2 falhas" in saida


def test_as_retidas_mostram_a_categoria_exibida_a_lida_e_o_rg(
    capsys: pytest.CaptureFixture[str],
) -> None:
    resumo = resumo_valido(
        retidas=(
            RetidaNaColeta("AR", C.ISENTO, C.ISENTO, False, True),  # passou a aceitar só o RG
            RetidaNaColeta("BO", None, C.VISTO_NA_CHEGADA, False, False),  # país sem dado antes
            RetidaNaColeta("CL", C.VISTO_EXIGIDO, None, False, False),  # a linha saiu da fonte
        )
    )

    coletar_vistos(resumo)

    saida = capsys.readouterr().out
    assert "  AR  Isento de visto → Isento, entrada com RG" in saida
    assert "  BO  Sem informação de visto → Visto na chegada" in saida
    assert "  CL  Visto exigido → Sem informação de visto" in saida


@pytest.mark.parametrize(
    ("resultado", "nome", "motivo", "proxima"),
    [
        (
            R.ADIADA,
            "ADIADA",
            "a última edição do artigo foi há 6 h (mínimo 24 h); tentativa 1 de 3, nova "
            "tentativa amanhã",
            ProximaTentativa.AMANHA,
        ),
        (
            R.REJEITADA,
            "REJEITADA",
            "só 120 países reconhecidos (mínimo 204: 90% dos 226 da última coleta válida)",
            ProximaTentativa.PROXIMA_SEGUNDA,
        ),
        (R.FALHOU, "FALHOU", "HTTP 503", ProximaTentativa.AMANHA),
        (R.BLOQUEADA, "BLOQUEADA", "bloqueado (HTTP 429)", ProximaTentativa.PROXIMA_SEGUNDA),
    ],
)
def test_coleta_que_nao_foi_valida_sai_com_codigo_1_e_mostra_o_motivo(
    capsys: pytest.CaptureFixture[str],
    resultado: ResultadoDaColetaDeVistos,
    nome: str,
    motivo: str,
    proxima: ProximaTentativa,
) -> None:
    codigo, _ = coletar_vistos(resumo_nao_valido(resultado, motivo, proxima))

    saida = capsys.readouterr().out
    assert codigo == 1
    assert saida.startswith(f"Coleta de vistos {nome}: {motivo}")
    assert ("amanhã" in saida) is (proxima is ProximaTentativa.AMANHA)
    assert ("segunda" in saida) is (proxima is ProximaTentativa.PROXIMA_SEGUNDA)
    assert "Dados aplicados" not in saida  # nada mudou


def test_contato_ausente_ou_de_exemplo_sai_com_codigo_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # `ContatoInvalido` vem de `rodada_real_de_vistos` (testada em test_jobs.py) para os dois casos
    def rodada_de_vistos() -> ResumoDaColetaDeVistos:
        raise ContatoInvalido("defina CONTATO_COLETA no .env")

    codigo = executar_comando(
        ["coletar", "--vistos"],
        rodada=sem_alertas,
        rodada_de_postos=sem_postos,
        rodada_de_vistos=rodada_de_vistos,
    )

    assert codigo == 2
    assert "defina CONTATO_COLETA" in capsys.readouterr().out


def test_coletar_alertas_e_postos_nao_tocam_nos_vistos() -> None:
    def sem_vistos() -> ResumoDaColetaDeVistos:
        raise AssertionError("a coleta de vistos não devia rodar")

    codigo = executar_comando(
        ["coletar", "--postos"],
        rodada=sem_alertas,
        rodada_de_postos=lambda: ResultadoDaColetaDePostos(1, True, None, 10, 10, 5, 5),
        rodada_de_vistos=sem_vistos,
    )

    assert codigo == 0


def test_coletar_exige_um_e_so_um_alvo() -> None:
    for argumentos in (["coletar"], ["coletar", "--vistos", "--alertas"]):
        with pytest.raises(SystemExit) as saida:
            executar_comando(
                argumentos,
                rodada=sem_alertas,
                rodada_de_postos=sem_postos,
                rodada_de_vistos=lambda: resumo_valido(),
            )
        assert saida.value.code == 2


# --------------------------------------------------------------------------- o dono (falsos)
class DonoFalso:
    """Cumpre `MeiosDoDono` e registra o que o comando lhe pediu."""

    def __init__(
        self,
        pendencias: PendenciasDoDono | None = None,
        *,
        sem_retida: tuple[str, ...] = (),
        nomes_pendentes: tuple[str, ...] = ("Atlantis",),
        todas: tuple[str, ...] = ("AR", "BO"),
    ) -> None:
        self.pendencias = pendencias or PendenciasDoDono((), (), (), ())
        self.sem_retida = sem_retida
        self.nomes_pendentes = nomes_pendentes
        self.todas = todas
        self.pedidos: list[tuple[str, ...]] = []

    def listar_pendentes(self) -> PendenciasDoDono:
        self.pedidos.append(("pendentes",))
        return self.pendencias

    def confirmar(self, codigo: str) -> MudancaPendente:
        self.pedidos.append(("confirmar", codigo))
        if codigo in self.sem_retida:
            raise ErroDoDono(f"{codigo}: não há mudança retida esperando confirmação")
        return mudanca(codigo.strip().upper())  # o serviço real também normaliza o código

    def confirmar_todos(self) -> tuple[str, ...]:
        self.pedidos.append(("confirmar", "--todos"))
        return self.todas

    def rejeitar(self, codigo: str) -> None:
        self.pedidos.append(("rejeitar", codigo))
        if codigo in self.sem_retida:
            raise ErroDoDono(f"{codigo}: não há mudança retida esperando confirmação")

    def ignorar_nome(self, nome: str, motivo: str) -> None:
        self.pedidos.append(("ignorar-nome", nome, motivo))
        if not motivo.strip():
            raise ErroDoDono("informe o motivo para ignorar o nome")
        if nome not in self.nomes_pendentes:
            raise ErroDoDono(f"{nome!r} não é um nome pendente")


def mudanca(
    codigo: str = "AR",
    exibida: CategoriaDeVisto | None = C.VISTO_EXIGIDO,
    lida: CategoriaDeVisto | None = C.ISENTO,
    *,
    exibido_de: datetime | None = EXIBIDO_DE,
) -> MudancaPendente:
    return MudancaPendente(codigo, exibida, lida, False, False, RETIDA_EM, exibido_de)


def item(tipo: TipoDeItemParaRevisao, valor: str, nome_na_fonte: str) -> ItemPendente:
    return ItemPendente(
        tipo=tipo,
        valor=valor,
        contexto=[{"tabela": "principal", "nome_na_fonte": nome_na_fonte}],
        primeira_vez_em=RETIDA_EM,
        ultima_vez_em=RETIDA_EM,
    )


def regra() -> RegraPendente:
    return RegraPendente("JM", HASH_ESPERADO, HASH_NOVO, "Outra nota.", RETIDA_EM, RETIDA_EM)


def dono_do_comando(argumentos: list[str], dono: DonoFalso) -> int:
    return executar_comando(
        argumentos,
        rodada=sem_alertas,
        rodada_de_postos=sem_postos,
        dono=lambda: nullcontext(dono),
    )


# --------------------------------------------------------------------------- vistos pendentes
def test_sem_pendencias_a_lista_mostra_os_quatro_grupos_vazios(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = dono_do_comando(["vistos", "pendentes"], DonoFalso())

    assert codigo == 0
    assert capsys.readouterr().out.splitlines() == [
        "Mudanças retidas (0)",
        "Nomes não reconhecidos (0)",
        "Rótulos não reconhecidos (0)",
        "Regras por país a reconfirmar (0)",
    ]


def test_pendentes_na_forma_do_contrato(capsys: pytest.CaptureFixture[str]) -> None:
    pendencias = PendenciasDoDono(
        retidas=(mudanca(),),
        nomes=(item(TipoDeItemParaRevisao.NOME, "atlantis", "Atlantis"),),
        rotulos=(item(TipoDeItemParaRevisao.ROTULO, "super visa", "Albania"),),
        regras=(regra(),),
    )

    codigo = dono_do_comando(["vistos", "pendentes"], DonoFalso(pendencias))

    saida = capsys.readouterr().out
    linhas = saida.splitlines()
    assert codigo == 0
    assert linhas[0] == "Mudanças retidas (1)"
    assert linhas[1].split() == ["código", "exibido", "→", "lido", "desde", "dado", "exibido", "de"]
    assert linhas[2].split() == [
        "AR",
        "Visto",
        "exigido",
        "→",
        "Isento",
        "de",
        "visto",
        "27/10/2026",
        "20/10/2026",
    ]
    assert "Nomes não reconhecidos (1)" in linhas
    assert any(linha.split()[:2] == ["atlantis", "(Atlantis)"] for linha in linhas)
    assert "Rótulos não reconhecidos (1)" in linhas
    assert any(linha.split()[:3] == ["super", "visa", "(Albania)"] for linha in linhas)
    assert "Regras por país a reconfirmar (1)" in linhas


def test_a_regra_a_reconfirmar_traz_os_dois_hashes_inteiros_e_o_texto_novo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    pendencias = PendenciasDoDono((), (), (), (regra(),))

    dono_do_comando(["vistos", "pendentes"], DonoFalso(pendencias))

    saida = capsys.readouterr().out
    [linha] = [linha for linha in saida.splitlines() if linha.strip().startswith("JM")]
    assert linha == (
        f"  JM  a nota mudou; hash esperado {HASH_ESPERADO}, hash novo {HASH_NOVO}; "
        'texto novo: "Outra nota."'
    )


def test_retida_de_pais_sem_dado_mostra_sem_informacao_e_traco_na_data(
    capsys: pytest.CaptureFixture[str],
) -> None:
    pendencias = PendenciasDoDono(
        (mudanca("BO", None, C.VISTO_NA_CHEGADA, exibido_de=None),), (), (), ()
    )

    dono_do_comando(["vistos", "pendentes"], DonoFalso(pendencias))

    saida = capsys.readouterr().out
    assert "Sem informação de visto → Visto na chegada" in saida
    assert "—" in saida  # não há data de dado exibido


# --------------------------------------------------------------------------- confirmar
def test_confirmar_um_codigo_aplica_so_esse_e_diz_o_que_mudou(
    capsys: pytest.CaptureFixture[str],
) -> None:
    dono = DonoFalso()

    codigo = dono_do_comando(["vistos", "confirmar", "ar"], dono)

    assert codigo == 0
    assert dono.pedidos == [("confirmar", "ar")]
    assert "AR" in capsys.readouterr().out


def test_confirmar_todos_aplica_todas_e_lista_os_codigos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    dono = DonoFalso()

    codigo = dono_do_comando(["vistos", "confirmar", "--todos"], dono)

    assert codigo == 0
    assert dono.pedidos == [("confirmar", "--todos")]
    saida = capsys.readouterr().out
    assert "2" in saida
    assert "AR, BO" in saida


def test_confirmar_todos_sem_nada_retido_nao_e_erro(capsys: pytest.CaptureFixture[str]) -> None:
    codigo = dono_do_comando(["vistos", "confirmar", "--todos"], DonoFalso(todas=()))

    assert codigo == 0
    assert "Não há mudanças retidas" in capsys.readouterr().out


def test_confirmar_codigo_sem_mudanca_retida_sai_com_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = dono_do_comando(["vistos", "confirmar", "ZZ"], DonoFalso(sem_retida=("ZZ",)))

    assert codigo == 2
    assert "ZZ: não há mudança retida" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argumentos",
    [["vistos", "confirmar"], ["vistos", "confirmar", "AR", "--todos"]],
    ids=["sem-nada", "codigo-e-todos"],
)
def test_confirmar_exige_um_codigo_ou_todos(argumentos: list[str]) -> None:
    dono = DonoFalso()
    with pytest.raises(SystemExit) as saida:
        dono_do_comando(argumentos, dono)
    assert saida.value.code == 2
    assert dono.pedidos == []


# --------------------------------------------------------------------------- rejeitar
def test_rejeitar_pede_a_rejeicao_do_codigo(capsys: pytest.CaptureFixture[str]) -> None:
    dono = DonoFalso()

    codigo = dono_do_comando(["vistos", "rejeitar", "AR"], dono)

    assert codigo == 0
    assert dono.pedidos == [("rejeitar", "AR")]
    assert "AR" in capsys.readouterr().out


def test_rejeitar_codigo_sem_mudanca_retida_sai_com_2(capsys: pytest.CaptureFixture[str]) -> None:
    codigo = dono_do_comando(["vistos", "rejeitar", "ZZ"], DonoFalso(sem_retida=("ZZ",)))

    assert codigo == 2
    assert "ZZ" in capsys.readouterr().out


def test_rejeitar_sem_codigo_e_recusado() -> None:
    with pytest.raises(SystemExit) as saida:
        dono_do_comando(["vistos", "rejeitar"], DonoFalso())
    assert saida.value.code == 2


# --------------------------------------------------------------------------- ignorar-nome
def test_ignorar_nome_passa_o_nome_e_o_motivo(capsys: pytest.CaptureFixture[str]) -> None:
    dono = DonoFalso()

    codigo = dono_do_comando(
        ["vistos", "ignorar-nome", "Atlantis", "--motivo", "continente lendário"], dono
    )

    assert codigo == 0
    assert dono.pedidos == [("ignorar-nome", "Atlantis", "continente lendário")]
    assert "Atlantis" in capsys.readouterr().out


def test_ignorar_nome_que_nao_esta_pendente_sai_com_2(capsys: pytest.CaptureFixture[str]) -> None:
    codigo = dono_do_comando(
        ["vistos", "ignorar-nome", "Brasil", "--motivo", "porque sim"], DonoFalso()
    )

    assert codigo == 2
    assert "não é um nome pendente" in capsys.readouterr().out


def test_ignorar_nome_com_motivo_vazio_sai_com_2(capsys: pytest.CaptureFixture[str]) -> None:
    codigo = dono_do_comando(["vistos", "ignorar-nome", "Atlantis", "--motivo", "  "], DonoFalso())

    assert codigo == 2
    assert "motivo" in capsys.readouterr().out


def test_ignorar_nome_sem_motivo_e_recusado() -> None:
    dono = DonoFalso()
    with pytest.raises(SystemExit) as saida:
        dono_do_comando(["vistos", "ignorar-nome", "Atlantis"], dono)
    assert saida.value.code == 2
    assert dono.pedidos == []


# --------------------------------------------------------------------------- uso errado
@pytest.mark.parametrize(
    "argumentos",
    [["vistos"], ["vistos", "apagar-tudo"], ["vistos", "pendentes", "extra"]],
    ids=["sem-subcomando", "subcomando-desconhecido", "argumento-sobrando"],
)
def test_uso_errado_do_grupo_vistos_sai_com_2(argumentos: list[str]) -> None:
    dono = DonoFalso()
    with pytest.raises(SystemExit) as saida:
        dono_do_comando(argumentos, dono)
    assert saida.value.code == 2
    assert dono.pedidos == []


def test_os_comandos_do_dono_nunca_disparam_uma_coleta() -> None:
    # `sem_alertas` e `sem_postos` levantam se rodarem; nenhum comando do dono chega a elas
    dono = DonoFalso()
    for argumentos in (
        ["vistos", "pendentes"],
        ["vistos", "confirmar", "AR"],
        ["vistos", "rejeitar", "AR"],
        ["vistos", "ignorar-nome", "Atlantis", "--motivo", "x"],
    ):
        assert dono_do_comando(argumentos, dono) == 0


# --------------------------------------------------------------------------- console
def test_saida_do_comando_vai_em_utf8_mesmo_com_o_console_em_cp1252() -> None:
    sem_ajuste = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")  # o console padrão do Windows
    with pytest.raises(UnicodeEncodeError):
        sem_ajuste.write("AR  Visto exigido → Isento de visto")

    buffer = io.BytesIO()
    console = io.TextIOWrapper(buffer, encoding="cp1252")
    configurar_saida_em_utf8(console)
    console.write("AR  Visto exigido → Isento de visto — sem data")
    console.flush()

    assert buffer.getvalue().decode("utf-8") == "AR  Visto exigido → Isento de visto — sem data"


def test_o_interrogacao_fica_so_para_o_que_nem_o_utf8_escreve() -> None:
    buffer = io.BytesIO()
    console = io.TextIOWrapper(buffer, encoding="cp1252")
    configurar_saida_em_utf8(console)
    substituto_solto = chr(0xD800)  # não existe em UTF-8

    console.write(f"ok {substituto_solto} ok")
    console.flush()

    assert buffer.getvalue() == b"ok ? ok"


def test_console_sem_reconfigure_fica_como_esta() -> None:
    configurar_saida_em_utf8(io.StringIO())  # StringIO não tem `reconfigure`: nada acontece
