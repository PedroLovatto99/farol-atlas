"""A página real do artigo (1,5 MB), da coleta ao painel, ao globo e à linha de comando do dono.

No estilo de `tests/integracao/mapa/test_oriente_medio_alerta_real.py`: a fixture inteira passa por
`ServicoDeColetaDeVistos` (Wikipédia falsa servindo a página real, tradutor falso e o seed completo
do mapa no banco de teste) e depois por `montar_visto_do_pais`, `montar_vistos_do_mapa`, a API e os
comandos do dono. Nenhum teste acessa a rede nem um modelo de linguagem.
"""

import io
from collections.abc import Iterator
from contextlib import nullcontext, redirect_stdout
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from farol.api.app import criar_app, sessao_da_requisicao
from farol.api.dependencias import relogio_da_requisicao
from farol.dominio import ColetaVistos, MotivoOutraSituacao, RequisitoVistoRepositorio
from farol.infra import Configuracoes
from farol.vistos import (
    OrigemDoVisto,
    ResumoDaColetaDeVistos,
    ServicoDeColetaDeVistos,
    ServicoDoDono,
    SituacaoDeVisto,
    SituacaoNoGlobo,
    TipoDePermanencia,
    montar_visto_do_pais,
    montar_vistos_do_mapa,
)
from farol.vistos.fonte import TABELA_PRINCIPAL, LinhaDaFonte
from farol.worker import executar_comando

if TYPE_CHECKING:
    from tests.conftest import RelogioFalso, TradutorFalso, WikipediaFalsa
    from tests.integracao.vistos.conftest import Cenario

PAISES_RECONHECIDOS = 228  # códigos do mapa ligados a alguma linha, com Kosovo e Malvinas
TERRITORIOS_SEM_O_BRASIL = 237
OITO_DO_RG = {"AR", "BO", "CL", "CO", "EC", "PY", "PE", "UY"}
FONTE = "https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens"


class Coletado:
    """A primeira coleta da página real e o que dá para consultar sobre ela."""

    def __init__(
        self,
        sessao: Session,
        relogio: "RelogioFalso",
        tradutor: "TradutorFalso",
        wikipedia: "WikipediaFalsa",
    ) -> None:
        self.sessao = sessao
        self.relogio = relogio
        self.tradutor = tradutor
        self.wikipedia = wikipedia
        self.resumo = self.coletar()

    def coletar(self) -> ResumoDaColetaDeVistos:
        return ServicoDeColetaDeVistos(
            self.sessao, self.wikipedia, self.relogio, self.tradutor
        ).coletar()

    def http(self) -> TestClient:
        app = criar_app(
            Configuracoes(database_url=SecretStr("postgresql+psycopg://x:y@nao-existe/z"))
        )

        def fornecer_sessao() -> Iterator[Session]:
            yield self.sessao

        app.dependency_overrides[sessao_da_requisicao] = fornecer_sessao
        app.dependency_overrides[relogio_da_requisicao] = lambda: self.relogio
        return TestClient(app, raise_server_exceptions=False)

    def pais(self, codigo: str) -> dict[str, Any]:
        resposta = self.http().get(f"/api/v1/paises/{codigo}")
        assert resposta.status_code == 200, codigo
        corpo: dict[str, Any] = resposta.json()
        return corpo

    def visto(self, codigo: str) -> dict[str, Any]:
        visto = self.pais(codigo)["visto"]
        assert visto is not None, f"{codigo} devia ter a seção de visto"
        assert isinstance(visto, dict)
        return visto

    def globo(self) -> dict[str, dict[str, Any]]:
        corpo = self.http().get("/api/v1/vistos").json()
        return {t["codigo"]: t for t in corpo["territorios"]}


@pytest.fixture
def coletado(
    mapa_completo: Session,
    relogio: "RelogioFalso",
    tradutor_falso: "TradutorFalso",
    wikipedia: "WikipediaFalsa",
) -> Coletado:
    return Coletado(mapa_completo, relogio, tradutor_falso, wikipedia)


# --------------------------------------------------------------------------- a coleta
def test_a_pagina_inteira_gera_uma_coleta_valida_com_228_paises_reconhecidos(
    coletado: Coletado,
) -> None:
    resumo = coletado.resumo

    assert resumo.valida, resumo.motivo
    assert resumo.paises_reconhecidos == PAISES_RECONHECIDOS
    assert resumo.minimo == 150  # o piso da primeira coleta
    assert resumo.revisao_fonte == 1380975986
    assert (resumo.aplicadas, resumo.sem_mudanca, resumo.retidas) == (228, 0, ())
    assert len(coletado.sessao.query(ColetaVistos).all()) == 1


def test_nenhum_nome_nem_rotulo_desconhecido_fica_pendente(coletado: Coletado) -> None:
    resumo = coletado.resumo

    assert resumo.nomes_nao_reconhecidos == ()  # SC-009
    assert resumo.rotulos_nao_reconhecidos == ()  # SC-010
    assert resumo.regras_para_reconfirmar == ()
    assert resumo.pendencias.total == 0
    assert ServicoDoDono(coletado.sessao, coletado.relogio).listar_pendentes().total == 0


def test_toda_observacao_foi_traduzida_uma_unica_vez(coletado: Coletado) -> None:
    textos = coletado.tradutor.textos

    assert textos
    assert len(textos) == len(set(textos))  # nenhum texto repetido entre os lotes
    assert coletado.resumo.traducoes_falhas == 0
    assert coletado.resumo.traducoes_novas == len(textos)


# --------------------------------------------------------------------------- cobertura
def test_todo_territorio_com_painel_tem_visto_e_a_cobertura_passa_de_95_por_cento(
    coletado: Coletado,
) -> None:
    mapa = montar_vistos_do_mapa(coletado.sessao, coletado.relogio)
    sem_o_brasil = [t for t in mapa.territorios if t.codigo != "BR"]

    assert len(sem_o_brasil) == TERRITORIOS_SEM_O_BRASIL
    # ligação: 237 de 237 (100%), nenhum "sem informação"
    assert [t.codigo for t in sem_o_brasil if t.situacao is SituacaoNoGlobo.SEM_INFORMACAO] == []

    # SC-001: países com dado, ou seja, com rótulo conhecido (≥ 95%)
    com_rotulo_desconhecido = [
        r.territorio_codigo
        for r in RequisitoVistoRepositorio(coletado.sessao).listar_todos()
        if r.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    ]
    com_dado = len(sem_o_brasil) - len(com_rotulo_desconhecido)
    assert com_rotulo_desconhecido == []
    assert com_dado / len(sem_o_brasil) >= 0.95


def test_nenhum_territorio_sem_dado_aparece_com_categoria(coletado: Coletado) -> None:
    # SC-002: toda categoria mostrada vem de um registro (o do território ou o do soberano)
    for codigo, territorio in coletado.globo().items():
        if codigo == "BR" or territorio["situacao"] == "sem_informacao":
            continue
        visto = montar_visto_do_pais(coletado.sessao, codigo, coletado.relogio)
        assert visto is not None
        assert visto.dado_de is not None
        assert visto.rotulo_original
        assert visto.situacao.value == territorio["situacao"]


# --------------------------------------------------------------------------- os casos da spec
def test_argentina_isenta_com_rg_e_os_oito_do_rg(coletado: Coletado) -> None:
    argentina = coletado.visto("AR")
    globo = coletado.globo()

    assert argentina["situacao"] == "isento"
    assert argentina["aceita_rg"] is True
    assert {c for c, t in globo.items() if t["aceita_rg"]} == OITO_DO_RG  # nem as Malvinas
    for codigo in ("VE", "GY"):
        assert coletado.visto(codigo)["aceita_rg"] is False
        assert coletado.visto(codigo)["situacao"] == "isento"


def test_estados_unidos_exigem_visto_e_a_fonte_nao_informa_permanencia(
    coletado: Coletado,
) -> None:
    visto = coletado.visto("US")

    assert visto["situacao"] == "visto_exigido"
    assert visto["permanencia"] is None


def test_oma_tem_autorizacao_eletronica_com_o_rotulo_combinado_visivel(
    coletado: Coletado,
) -> None:
    visto = coletado.visto("OM")

    assert visto["situacao"] == "autorizacao_eletronica"
    assert visto["rotulo_original"] == "Visa not required / eVisa"


def test_australia_exige_visto(coletado: Coletado) -> None:
    assert coletado.visto("AU")["situacao"] == "visto_exigido"


def test_jamaica_varia_conforme_o_motivo_da_viagem(coletado: Coletado) -> None:
    visto = coletado.visto("JM")

    assert visto["varia_conforme_motivo"] is True
    assert visto["permanencia"]["tipo"] == TipoDePermanencia.VARIA_CONFORME_MOTIVO.value
    assert visto["observacoes"]  # a nota que explica a variação, com tradução


def test_etiopia_mostra_a_permanencia_como_a_fonte_escreveu(coletado: Coletado) -> None:
    permanencia = coletado.visto("ET")["permanencia"]

    assert permanencia == {"tipo": "original", "texto": "up to 90 days"}


def test_santa_helena_fica_em_outra_situacao_com_o_rotulo_a_vista(coletado: Coletado) -> None:
    visto = coletado.visto("SH")

    assert visto["situacao"] == SituacaoDeVisto.OUTRA_SITUACAO.value
    assert visto["motivo_outra_situacao"] == "rotulo_conhecido"
    assert visto["rotulo_original"] == "Visa not required / eVisa / Permission required"


# --------------------------------------------------------------------------- dependências
def test_hong_kong_tem_entrada_propria(coletado: Coletado) -> None:
    visto = coletado.visto("HK")

    assert (visto["situacao"], visto["origem"], visto["soberano_nome"]) == (
        "isento",
        OrigemDoVisto.PROPRIO.value,
        None,
    )


def test_guernsey_usa_a_entrada_do_reino_unido(coletado: Coletado) -> None:
    guernsey, reino_unido = coletado.visto("GG"), coletado.visto("GB")

    assert guernsey["origem"] == OrigemDoVisto.SOBERANO.value
    assert guernsey["soberano_nome"] == "Reino Unido"
    assert guernsey["situacao"] == reino_unido["situacao"] == "autorizacao_eletronica"
    assert guernsey["dado_de"] == reino_unido["dado_de"]


def test_kosovo_tem_o_painel_da_servia_e_o_visto_da_propria_linha(coletado: Coletado) -> None:
    kosovo = coletado.pais("XK")

    assert (kosovo["nome"], kosovo["bandeira"]) == ("Sérvia", "RS")  # identidade da 001
    assert kosovo["visto"]["territorio_nome"] == "Kosovo"
    assert kosovo["visto"]["origem"] == OrigemDoVisto.PROPRIO.value
    assert kosovo["visto"]["soberano_nome"] is None
    assert kosovo["visto"]["rotulo_original"] == "Visa not required"
    assert [o["texto_original"] for o in kosovo["visto"]["observacoes"]] == ["90 days"]


def test_malvinas_tem_o_painel_da_argentina_e_o_visto_da_propria_linha_sem_rg(
    coletado: Coletado,
) -> None:
    malvinas = coletado.pais("FK")

    assert (malvinas["nome"], malvinas["bandeira"]) == ("Argentina", "AR")  # identidade da 001
    assert malvinas["visto"]["territorio_nome"] == "Ilhas Malvinas"
    assert malvinas["visto"]["situacao"] == "isento"
    assert malvinas["visto"]["aceita_rg"] is False
    assert malvinas["visto"]["origem"] == OrigemDoVisto.PROPRIO.value
    [permissao] = malvinas["visto"]["observacoes"]
    assert permissao["texto_original"].startswith("A visitor permit is normally issued")
    assert coletado.visto("AR")["aceita_rg"] is True  # só a Argentina aceita o RG


def test_as_malvinas_nunca_exibem_rg_nem_no_painel_nem_no_globo(coletado: Coletado) -> None:
    assert coletado.visto("FK")["aceita_rg"] is False
    assert coletado.globo()["FK"]["aceita_rg"] is False
    assert coletado.globo()["FK"]["situacao"] == "isento"


def test_taiwan_sai_como_taiwan_china_com_visto_proprio(coletado: Coletado) -> None:
    taiwan = coletado.pais("TW")

    assert taiwan["nome"] == "Taiwan (China)"
    assert taiwan["visto"]["origem"] == OrigemDoVisto.PROPRIO.value
    assert taiwan["visto"]["soberano_nome"] is None


def test_porto_rico_segue_a_regra_das_dependencias(coletado: Coletado) -> None:
    visto = coletado.visto("PR")
    estados_unidos = coletado.visto("US")

    # a fonte tem linha própria para Porto Rico: vale a entrada dele
    assert visto["origem"] == OrigemDoVisto.PROPRIO.value
    assert visto["situacao"] == estados_unidos["situacao"] == "visto_exigido"


def test_o_brasil_nao_tem_secao_de_visto_nem_no_painel_nem_no_globo(coletado: Coletado) -> None:
    assert coletado.pais("BR")["visto"] is None
    assert coletado.globo()["BR"]["situacao"] == "nao_se_aplica"


def test_o_painel_e_o_globo_concordam_em_todo_territorio(coletado: Coletado) -> None:
    globo = coletado.globo()

    for codigo in sorted(globo):
        visto = coletado.pais(codigo)["visto"]
        if codigo == "BR":
            assert visto is None
            continue
        assert visto["situacao"] == globo[codigo]["situacao"], codigo
        assert visto["aceita_rg"] is globo[codigo]["aceita_rg"], codigo
        assert visto["fonte"]["url"] == FONTE


# --------------------------------------------------------------------------- a segunda coleta
def test_segunda_coleta_com_a_mesma_pagina_nao_retem_nada_nem_traduz_de_novo(
    coletado: Coletado,
) -> None:
    lotes = len(coletado.tradutor.lotes)
    primeira = coletado.relogio.agora()
    coletado.relogio.avancar(days=7)

    segunda = coletado.coletar()

    assert segunda.valida, segunda.motivo
    assert (segunda.aplicadas, segunda.sem_mudanca) == (0, PAISES_RECONHECIDOS)
    assert segunda.retidas == ()
    assert segunda.traducoes_novas == 0
    assert len(coletado.tradutor.lotes) == lotes  # o tradutor nem foi chamado
    assert segunda.pendencias.total == 0
    # o dado foi confirmado de novo: a data do dado de cada país é a da segunda coleta
    assert coletado.visto("AR")["dado_de"] > primeira.isoformat().replace("+00:00", "Z")[:19]
    assert coletado.visto("AR")["dado_de"].startswith("2026-10-30T12:00:00")


# --------------------------------------------------------------------------- o dono
def executar_o_comando(
    cenario: "Cenario", *argumentos: str, resumo: ResumoDaColetaDeVistos | None = None
) -> tuple[int, str]:
    """Roda um comando do worker com o serviço real do dono e devolve (código, saída).

    `resumo` é o que a rodada de vistos devolveria em `coletar --vistos` (a coleta já foi feita).
    """
    saida = io.StringIO()

    def sem_coleta() -> Any:
        raise AssertionError("este comando não devia coletar alertas nem postos")

    def rodada_de_vistos() -> ResumoDaColetaDeVistos:
        assert resumo is not None
        return resumo

    with redirect_stdout(saida):
        codigo = executar_comando(
            list(argumentos),
            rodada=sem_coleta,
            rodada_de_postos=sem_coleta,
            rodada_de_vistos=rodada_de_vistos,
            dono=lambda: nullcontext(ServicoDoDono(cenario.sessao, cenario.relogio)),
        )
    return codigo, saida.getvalue()


def test_o_dono_ve_o_que_espera_depois_de_uma_semana_de_mudancas_na_fonte(
    cenario_completo: "Cenario",
) -> None:
    cenario = cenario_completo
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.editar("Algeria", rotulo="Visa not required", permanencia="90 days")
    cenario.editar("Albania", rotulo="Super visa")
    cenario.editar("Jamaica", notas="Outra nota.")
    cenario.acrescentar(
        LinhaDaFonte(TABELA_PRINCIPAL, None, "Atlantis", "Visa not required", "", "")
    )
    resumo = cenario.coletar(agendada=True)
    cenario.semana_seguinte()

    codigo_da_coleta, coleta = executar_o_comando(cenario, "coletar", "--vistos", resumo=resumo)
    codigo, saida = executar_o_comando(cenario, "vistos", "pendentes")

    print()
    print("--- coletar --vistos (segunda semana) ---")
    print(coleta)
    print("--- vistos pendentes ---")
    print(saida)
    assert codigo_da_coleta == 0
    assert "  DZ  Visto exigido → Isento de visto" in coleta.splitlines()
    assert codigo == 0
    linhas = saida.splitlines()
    assert "Mudanças retidas (1)" in linhas
    assert any(
        linha.split()[:1] == ["DZ"] and "Visto exigido → Isento de visto" in linha
        for linha in linhas
    )
    assert "Nomes não reconhecidos (1)" in linhas
    assert any(linha.split()[:2] == ["atlantis", "(Atlantis)"] for linha in linhas)
    assert "Rótulos não reconhecidos (1)" in linhas
    assert any(linha.split()[:3] == ["super", "visa", "(Albania)"] for linha in linhas)
    assert "Regras por país a reconfirmar (1)" in linhas
    assert any(linha.strip().startswith("JM  a nota mudou; hash esperado") for linha in linhas)

    # confirmar a Argélia aplica o candidato e esvazia a lista de retidas
    codigo, confirmado = executar_o_comando(cenario, "vistos", "confirmar", "DZ")
    assert codigo == 0
    assert "Confirmado: DZ (Visto exigido → Isento de visto)" in confirmado
    argelia = montar_visto_do_pais(cenario.sessao, "DZ", cenario.relogio)
    assert argelia is not None
    assert argelia.situacao is SituacaoDeVisto.ISENTO
    _, depois = executar_o_comando(cenario, "vistos", "pendentes")
    assert "Mudanças retidas (0)" in depois.splitlines()


def test_o_comando_coletar_vistos_resume_a_pagina_real_e_vistos_pendentes_vem_vazio(
    coletado: Coletado,
) -> None:
    saida = io.StringIO()

    def sem_coleta() -> Any:
        raise AssertionError("este comando não devia coletar alertas nem postos")

    with redirect_stdout(saida):
        codigo = executar_comando(
            ["coletar", "--vistos"],
            rodada=sem_coleta,
            rodada_de_postos=sem_coleta,
            rodada_de_vistos=lambda: coletado.resumo,
        )
        codigo_pendentes = executar_comando(
            ["vistos", "pendentes"],
            rodada=sem_coleta,
            rodada_de_postos=sem_coleta,
            dono=lambda: nullcontext(ServicoDoDono(coletado.sessao, coletado.relogio)),
        )

    print()
    print(saida.getvalue())
    linhas = saida.getvalue().splitlines()
    assert (codigo, codigo_pendentes) == (0, 0)
    assert linhas[:3] == [
        "Coleta de vistos VÁLIDA: 228 países reconhecidos (mínimo 150)",
        "Artigo: revisão 1380975986, última edição em 19/10/2026 05:08 UTC",
        "Dados aplicados: 228 | sem mudança: 0 | retidos: 0",
    ]
    assert linhas[3] == "Nomes não reconhecidos: 0 | rótulos não reconhecidos: 0"
    assert linhas[-4:] == [
        "Mudanças retidas (0)",
        "Nomes não reconhecidos (0)",
        "Rótulos não reconhecidos (0)",
        "Regras por país a reconfirmar (0)",
    ]
