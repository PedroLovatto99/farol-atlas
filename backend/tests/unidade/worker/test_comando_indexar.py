"""Comandos `indexar` e `reindexar` do worker e a indexação ao fim de `coletar --alertas` e
`reclassificar` (contracts/indexacao-e-comandos.md, seção 4). Sem banco, sem rede, sem chave."""

import pytest

from farol.chat import (
    ModeloNoIndice,
    ResumoDaIndexacao,
    ResumoDaReindexacao,
    SituacaoDoIndice,
)
from farol.classificacao import ResultadoDaClassificacao, ResultadoDaReclassificacao
from farol.coleta import ResultadoDaColeta, ResultadoDaColetaDePostos
from farol.dominio import ResultadoDaColetaDeVistos
from farol.vistos import ProximaTentativa, ResumoDaColetaDeVistos
from farol.worker import IndexacaoIndisponivel, ResultadoDaRodada, executar_comando


def rodada_falsa(completa: bool = True) -> ResultadoDaRodada:
    coleta = ResultadoDaColeta(
        execucao_id=1,
        completa=completa,
        motivo_interrupcao=None if completa else "caiu na verificação humana",
        paginas_esperadas=18,
        paginas_lidas=18 if completa else 4,
        para_classificar=(1, 2),
        removidos=0,
    )
    return ResultadoDaRodada(coleta, ResultadoDaClassificacao(2, 0))


def sem_postos() -> ResultadoDaColetaDePostos:
    raise AssertionError("a coleta de postos não devia rodar")


class Indexacao:
    """Registra como `indexar`, `reindexar` e o status foram chamados."""

    def __init__(
        self,
        resumo: ResumoDaIndexacao | None = None,
        reindexacao: ResumoDaReindexacao | None = None,
        situacao: SituacaoDoIndice | None = None,
        erro: Exception | None = None,
    ) -> None:
        self.resumo = resumo or ResumoDaIndexacao(novos=2, trechos=9)
        self.reindexacao = reindexacao or ResumoDaReindexacao(refeitos=3, trechos_novos=11)
        self.situacao = situacao or SituacaoDoIndice(18, 18, (), ())
        self.erro = erro
        self.chamadas: list[tuple[str, bool]] = []

    def indexar(self, tudo: bool) -> ResumoDaIndexacao:
        self.chamadas.append(("indexar", tudo))
        if self.erro:
            raise self.erro
        return self.resumo

    def reindexar(self, manter_antigos: bool) -> ResumoDaReindexacao:
        self.chamadas.append(("reindexar", manter_antigos))
        if self.erro:
            raise self.erro
        return self.reindexacao

    def situacao_do_indice(self) -> SituacaoDoIndice:
        self.chamadas.append(("status", False))
        return self.situacao


def executar(argumentos: list[str], indexacao: Indexacao | None, **extra: object) -> int:
    return executar_comando(
        argumentos,
        rodada=extra.pop("rodada", rodada_falsa),  # type: ignore[arg-type]
        rodada_de_postos=sem_postos,
        indexar=indexacao.indexar if indexacao else None,
        reindexar=indexacao.reindexar if indexacao else None,
        situacao_do_indice=indexacao.situacao_do_indice if indexacao else None,
        **extra,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- indexar
def test_indexar_faz_uma_passada_e_mostra_o_resumo(capsys: pytest.CaptureFixture[str]) -> None:
    indexacao = Indexacao(
        ResumoDaIndexacao(
            novos=2, atualizados=1, inalterados=14, metadados=1, apagados=1, trechos=9
        )
    )

    codigo = executar(["indexar"], indexacao)

    assert codigo == 0
    assert indexacao.chamadas == [("indexar", False)]
    saida = capsys.readouterr().out
    assert "novos: 2" in saida and "atualizados: 1" in saida and "inalterados: 14" in saida
    assert "apagados: 1" in saida and "trechos gravados: 9" in saida and "falhas: 0" in saida


def test_indexar_tudo_refaz_tudo() -> None:
    indexacao = Indexacao()
    assert executar(["indexar", "--tudo"], indexacao) == 0
    assert indexacao.chamadas == [("indexar", True)]


def test_indexar_com_falhas_sai_com_codigo_1(capsys: pytest.CaptureFixture[str]) -> None:
    indexacao = Indexacao(ResumoDaIndexacao(novos=1, falhas=2))
    assert executar(["indexar"], indexacao) == 1
    assert "falhas: 2" in capsys.readouterr().out


def test_indexar_sem_chave_ou_configuracao_sai_com_codigo_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    indexacao = Indexacao(erro=IndexacaoIndisponivel("GOOGLE_API_KEY_CHAT não definida"))
    assert executar(["indexar"], indexacao) == 2
    assert "GOOGLE_API_KEY_CHAT" in capsys.readouterr().out


def test_indexar_tudo_e_status_nao_combinam() -> None:
    with pytest.raises(SystemExit) as saida:
        executar(["indexar", "--tudo", "--status"], Indexacao())
    assert saida.value.code == 2


# --------------------------------------------------------------------------- indexar --status
def test_status_em_dia_sai_com_0_e_so_olha(capsys: pytest.CaptureFixture[str]) -> None:
    situacao = SituacaoDoIndice(18, 18, (ModeloNoIndice("falso:v1", 256, 40, 18),), ())
    indexacao = Indexacao(situacao=situacao)

    codigo = executar(["indexar", "--status"], indexacao)

    assert codigo == 0
    assert indexacao.chamadas == [("status", False)]  # não indexou nada
    saida = capsys.readouterr().out
    assert "18 de 18" in saida and "falso:v1" in saida and "256" in saida and "40 trechos" in saida


def test_status_com_pendencia_sai_com_1(capsys: pytest.CaptureFixture[str]) -> None:
    indexacao = Indexacao(situacao=SituacaoDoIndice(18, 15, (), ()))
    assert executar(["indexar", "--status"], indexacao) == 1
    assert "15 de 18" in capsys.readouterr().out


def test_status_avisa_em_destaque_quando_o_indice_e_de_outro_modelo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    aviso = "O índice só tem vetores de falso:v1 (16 dimensões). Rode `reindexar`."
    indexacao = Indexacao(
        situacao=SituacaoDoIndice(18, 0, (ModeloNoIndice("falso:v1", 16, 40, 18),), (aviso,))
    )

    codigo = executar(["indexar", "--status"], indexacao)

    assert codigo == 1
    saida = capsys.readouterr().out
    assert "ATENÇÃO" in saida and "reindexar" in saida


# --------------------------------------------------------------------------- reindexar
def test_reindexar_mostra_o_resumo(capsys: pytest.CaptureFixture[str]) -> None:
    indexacao = Indexacao(
        reindexacao=ResumoDaReindexacao(
            refeitos=17, ja_completos=1, trechos_novos=40, vetores_antigos_apagados=40
        )
    )

    codigo = executar(["reindexar"], indexacao)

    assert codigo == 0
    assert indexacao.chamadas == [("reindexar", False)]
    saida = capsys.readouterr().out
    assert "refeitos: 17" in saida and "trechos novos: 40" in saida
    assert "vetores antigos apagados: 40" in saida and "falhas: 0" in saida


def test_reindexar_manter_antigos_repassa_a_opcao() -> None:
    indexacao = Indexacao()
    assert executar(["reindexar", "--manter-antigos"], indexacao) == 0
    assert indexacao.chamadas == [("reindexar", True)]


def test_reindexar_com_alerta_que_falhou_sai_com_1() -> None:
    indexacao = Indexacao(reindexacao=ResumoDaReindexacao(refeitos=16, falhas=1))
    assert executar(["reindexar"], indexacao) == 1


def test_reindexar_sem_configuracao_sai_com_2() -> None:
    assert executar(["reindexar"], Indexacao(erro=IndexacaoIndisponivel("sem chave"))) == 2


# --------------------------------------------------------------------------- ao fim de outros
def test_coletar_alertas_termina_indexando(capsys: pytest.CaptureFixture[str]) -> None:
    ordem: list[str] = []
    indexacao = Indexacao()

    def rodada() -> ResultadoDaRodada:
        ordem.append("coleta")
        return rodada_falsa()

    def indexar(tudo: bool) -> ResumoDaIndexacao:
        ordem.append("indexacao")
        return indexacao.indexar(tudo)

    codigo = executar_comando(
        ["coletar", "--alertas"],
        rodada=rodada,
        rodada_de_postos=sem_postos,
        indexar=indexar,
    )

    assert codigo == 0
    assert ordem == ["coleta", "indexacao"]
    saida = capsys.readouterr().out
    assert "Coleta completa" in saida and "Indexação" in saida and "novos: 2" in saida


def test_coleta_incompleta_continua_saindo_com_1_e_indexa_assim_mesmo() -> None:
    indexacao = Indexacao()
    codigo = executar(["coletar", "--alertas"], indexacao, rodada=lambda: rodada_falsa(False))
    assert codigo == 1
    assert indexacao.chamadas == [("indexar", False)]


def test_indexacao_indisponivel_no_fim_da_coleta_nao_muda_o_codigo_de_saida(
    capsys: pytest.CaptureFixture[str],
) -> None:
    indexacao = Indexacao(erro=IndexacaoIndisponivel("GOOGLE_API_KEY_CHAT não definida"))

    codigo = executar(["coletar", "--alertas"], indexacao)

    assert codigo == 0
    assert "Indexação não feita" in capsys.readouterr().out


def test_erro_inesperado_na_indexacao_nao_derruba_a_coleta(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = executar(["coletar", "--alertas"], Indexacao(erro=RuntimeError("banco caiu")))
    assert codigo == 0
    assert "Indexação falhou" in capsys.readouterr().out


def reclassificada() -> ResultadoDaReclassificacao:
    return ResultadoDaReclassificacao(
        alerta_id=2, url="https://x/2", titulo="Oriente Médio", ok=True, motivo=None
    )


def test_reclassificar_termina_indexando(capsys: pytest.CaptureFixture[str]) -> None:
    indexacao = Indexacao()
    codigo = executar(
        ["reclassificar", "2"], indexacao, reclassificar=lambda referencia: reclassificada()
    )
    assert codigo == 0
    assert indexacao.chamadas == [("indexar", False)]
    assert "Indexação" in capsys.readouterr().out


def test_reclassificar_que_falha_nao_indexa() -> None:
    indexacao = Indexacao()

    def falha(referencia: str) -> ResultadoDaReclassificacao:
        return ResultadoDaReclassificacao(
            alerta_id=2, url="", titulo="", ok=False, motivo="RespostaInvalida"
        )

    codigo = executar(["reclassificar", "2"], indexacao, reclassificar=falha)

    assert codigo == 1
    assert indexacao.chamadas == []


def test_coletar_postos_nao_indexa() -> None:
    indexacao = Indexacao()
    postos = ResultadoDaColetaDePostos(
        execucao_id=2,
        completa=True,
        motivo_interrupcao=None,
        paginas_esperadas=1,
        paginas_lidas=1,
        postos_com_endereco=1,
        postos_com_telefone=1,
    )

    codigo = executar_comando(
        ["coletar", "--postos"],
        rodada=rodada_falsa,
        rodada_de_postos=lambda: postos,
        indexar=indexacao.indexar,
    )

    assert codigo == 0 and indexacao.chamadas == []


def test_coletar_vistos_nao_indexa() -> None:
    indexacao = Indexacao()
    resumo = ResumoDaColetaDeVistos(
        coleta_id=8,
        resultado=ResultadoDaColetaDeVistos.BLOQUEADA,
        motivo="HTTP 429",
        proxima_tentativa=ProximaTentativa.PROXIMA_SEGUNDA,
    )

    codigo = executar_comando(
        ["coletar", "--vistos"],
        rodada=rodada_falsa,
        rodada_de_postos=sem_postos,
        rodada_de_vistos=lambda: resumo,
        indexar=indexacao.indexar,
    )

    assert codigo == 1 and indexacao.chamadas == []
