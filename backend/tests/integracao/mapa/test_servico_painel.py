"""Serviço do painel: tudo o que o painel de um país precisa (FR-009 a FR-015, FR-030 a FR-035)."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from farol.dominio import (
    Alerta,
    Classificacao,
    ExecucaoColeta,
    NivelAlerta,
    NivelTerritorio,
    Posto,
    StatusClassificacao,
    Territorio,
    TipoExecucao,
    TipoTerritorio,
)
from farol.dominio.seed import executar
from farol.mapa import NivelExibido, TerritorioNaoEncontrado, VisaoDoPainel, montar_painel

DADOS = Path(__file__).resolve().parents[4] / "dados"
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
E, N, NORM = NivelAlerta.EVITAR, NivelAlerta.NAO_VIAJAR, NivelAlerta.NORMALIZADA

Item = tuple[str, NivelAlerta | None, list[tuple[str, NivelAlerta]]]


@pytest.fixture
def semeado(sessao: Session) -> Session:
    executar(sessao, DADOS, AGORA)
    return sessao


@pytest.fixture
def execucao(semeado: Session) -> ExecucaoColeta:
    completa = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS,
        iniciada_em=AGORA - timedelta(minutes=5),
        finalizada_em=AGORA,
        paginas_esperadas=10,
        paginas_lidas=10,
        lista_lida_inteira=True,
        completa=True,
    )
    semeado.add(completa)
    semeado.flush()
    return completa


def criar_alerta(
    sessao: Session,
    execucao: ExecucaoColeta,
    numero: int,
    titulo: str,
    data_ref: datetime,
    itens: list[Item] | None,
    *,
    publicado_em: datetime | None = None,
    modificado_em: datetime | None = None,
    removido: bool = False,
) -> Alerta:
    """Alerta confirmado. `itens=None` = pendente (sem classificação); `[]` = não é de viagem."""
    hash_do_alerta = f"{numero:064d}"
    alerta = Alerta(
        url=f"https://www.gov.br/mre/alerta-{numero}",
        titulo=titulo,
        texto="texto",
        publicado_em=publicado_em or data_ref,
        modificado_em=modificado_em,
        primeira_coleta_em=AGORA,
        ultima_coleta_em=AGORA,
        hash=hash_do_alerta,
        removido_em=AGORA if removido else None,
        confirmado_execucao_id=execucao.id,
        confirmado_hash=hash_do_alerta,
        confirmado_titulo=titulo,
        confirmado_data_ref=data_ref,
    )
    sessao.add(alerta)
    sessao.flush()
    if itens is not None:
        classificacao = Classificacao(
            alerta_id=alerta.id,
            alerta_hash=hash_do_alerta,
            status=StatusClassificacao.OK,
            e_alerta_de_viagem=bool(itens),
            modelo="modelo-falso",
            classificado_em=AGORA,
        )
        sessao.add(classificacao)
        sessao.flush()
        for codigo, nivel, regioes in itens:
            sessao.add(
                NivelTerritorio(
                    classificacao_id=classificacao.id,
                    territorio_codigo=codigo,
                    nivel_pais=nivel,
                    regioes=[{"nome": nome, "nivel": n.value} for nome, n in regioes],
                )
            )
        sessao.flush()
    return alerta


def painel(sessao: Session, codigo: str) -> VisaoDoPainel:
    return montar_painel(sessao, codigo)


# --------------------------------------------------------------------------- alertas
def test_lista_todos_os_alertas_do_mais_recente_ao_mais_antigo(
    semeado: Session, execucao: ExecucaoColeta
) -> None:
    criar_alerta(
        semeado, execucao, 1, "Peru (antigo)", datetime(2026, 3, 1, tzinfo=UTC), [("PE", N, [])]
    )
    criar_alerta(
        semeado, execucao, 2, "Peru (recente)", datetime(2026, 9, 1, tzinfo=UTC), [("PE", E, [])]
    )
    criar_alerta(
        semeado, execucao, 3, "Peru (meio)", datetime(2026, 6, 1, tzinfo=UTC), [("PE", N, [])]
    )

    visao = painel(semeado, "PE")

    assert [a.titulo for a in visao.alertas] == ["Peru (recente)", "Peru (meio)", "Peru (antigo)"]
    assert [a.define_nivel for a in visao.alertas] == [True, False, False]
    assert visao.nivel is NivelExibido.EVITAR  # o mais recente rege, mesmo menos grave que o antigo


def test_alerta_traz_titulo_link_e_datas(semeado: Session, execucao: ExecucaoColeta) -> None:
    criar_alerta(
        semeado,
        execucao,
        7,
        "Alerta de viagem – Peru",
        datetime(2026, 8, 17, tzinfo=UTC),
        [("PE", E, [])],
        publicado_em=datetime(2026, 6, 1, tzinfo=UTC),
        modificado_em=datetime(2026, 8, 17, tzinfo=UTC),
    )

    (alerta,) = painel(semeado, "PE").alertas

    assert alerta.titulo == "Alerta de viagem – Peru"
    assert alerta.url == "https://www.gov.br/mre/alerta-7"
    assert alerta.publicado_em == datetime(2026, 6, 1, tzinfo=UTC)
    assert alerta.modificado_em == datetime(2026, 8, 17, tzinfo=UTC)
    assert alerta.pendente is False


def test_nao_lista_alerta_que_nao_cita_o_pais_nem_o_que_nao_e_de_viagem_nem_o_removido(
    semeado: Session, execucao: ExecucaoColeta
) -> None:
    criar_alerta(semeado, execucao, 1, "Chile", datetime(2026, 5, 1, tzinfo=UTC), [("CL", E, [])])
    criar_alerta(semeado, execucao, 2, "Fraudes no Peru", datetime(2026, 5, 2, tzinfo=UTC), [])
    criar_alerta(
        semeado,
        execucao,
        3,
        "Peru",
        datetime(2026, 5, 3, tzinfo=UTC),
        [("PE", N, [])],
        removido=True,
    )

    assert painel(semeado, "PE").alertas == ()


def test_pais_sem_alerta_tem_lista_vazia_e_nivel_sem_alerta(
    semeado: Session, execucao: ExecucaoColeta
) -> None:
    visao = painel(semeado, "PE")
    assert visao.alertas == ()
    assert visao.nivel is NivelExibido.SEM_ALERTA


def test_sem_coleta_completa_o_painel_e_nao_verificado(semeado: Session) -> None:
    visao = painel(semeado, "PE")
    assert visao.nivel is NivelExibido.NAO_VERIFICADO
    assert visao.alertas == ()


def test_situacao_normalizada_e_marcada_no_alerta_que_rege(
    semeado: Session, execucao: ExecucaoColeta
) -> None:
    criar_alerta(
        semeado, execucao, 1, "Bolívia (antigo)", datetime(2026, 3, 1, tzinfo=UTC), [("BO", N, [])]
    )
    criar_alerta(
        semeado,
        execucao,
        2,
        "Bolívia normalizada",
        datetime(2026, 7, 10, tzinfo=UTC),
        [("BO", NORM, [])],
    )

    visao = painel(semeado, "BO")

    assert visao.nivel is NivelExibido.SEM_ALERTA
    assert [(a.titulo, a.situacao_normalizada, a.define_nivel) for a in visao.alertas] == [
        ("Bolívia normalizada", True, True),
        ("Bolívia (antigo)", False, False),
    ]


# --------------------------------------------------------------------------- regiões
def test_regioes_do_alerta_que_rege(semeado: Session, execucao: ExecucaoColeta) -> None:
    criar_alerta(
        semeado,
        execucao,
        1,
        "Oriente Médio",
        datetime(2026, 8, 17, tzinfo=UTC),
        [("LB", E, [("Sul do Líbano", N)]), ("SY", None, [("Norte da Síria", N)])],
    )

    libano = painel(semeado, "LB")
    assert libano.nivel is NivelExibido.EVITAR
    assert [(r.nome, r.nivel.value) for r in libano.regioes] == [("Sul do Líbano", "nao_viajar")]
    assert libano.regiao_unica_do_alerta is False

    siria = painel(semeado, "SY")
    assert siria.nivel is NivelExibido.SEM_ALERTA
    assert [r.nome for r in siria.regioes] == ["Norte da Síria"]
    assert siria.regiao_unica_do_alerta is True  # o alerta vale só para a região (FR-007)


def test_palestina_declara_que_as_regioes_cobrem_o_territorio(
    semeado: Session, execucao: ExecucaoColeta
) -> None:
    criar_alerta(
        semeado,
        execucao,
        1,
        "Oriente Médio",
        datetime(2026, 8, 17, tzinfo=UTC),
        [("PS", None, [("Faixa de Gaza", N), ("Cisjordânia", E)])],
    )

    palestina = painel(semeado, "PS")

    assert palestina.nivel is NivelExibido.EVITAR  # o menos grave entre as regiões
    assert [r.nome for r in palestina.regioes] == ["Faixa de Gaza", "Cisjordânia"]
    assert palestina.regiao_unica_do_alerta is False


def test_classificacao_antiga_com_demais_regioes_do_pais_tambem_vale_como_nivel_do_pais(
    semeado: Session, execucao: ExecucaoColeta
) -> None:
    """Linhas gravadas antes da normalização (a região "demais regiões do país") não enganam."""
    criar_alerta(
        semeado,
        execucao,
        1,
        "Oriente Médio",
        datetime(2026, 8, 17, tzinfo=UTC),
        [("LB", None, [("Sul do Líbano", N), ("demais regiões do país", E)])],
    )

    libano = painel(semeado, "LB")

    assert libano.nivel is NivelExibido.EVITAR
    assert [r.nome for r in libano.regioes] == ["Sul do Líbano"]
    assert libano.regiao_unica_do_alerta is False


def test_alerta_pendente_aparece_marcado_e_deixa_o_pais_nao_verificado(
    semeado: Session, execucao: ExecucaoColeta
) -> None:
    criar_alerta(
        semeado, execucao, 1, "Alerta de viagem – Peru", datetime(2026, 9, 1, tzinfo=UTC), None
    )

    visao = painel(semeado, "PE")

    assert visao.nivel is NivelExibido.NAO_VERIFICADO
    (alerta,) = visao.alertas
    assert alerta.pendente is True
    assert alerta.define_nivel is True
    assert alerta.url == "https://www.gov.br/mre/alerta-1"


# --------------------------------------------------------------------------- dependências
def test_dependencia_lista_os_alertas_proprios_e_os_do_soberano(
    semeado: Session, execucao: ExecucaoColeta
) -> None:
    criar_alerta(
        semeado, execucao, 1, "Dinamarca", datetime(2026, 5, 1, tzinfo=UTC), [("DK", E, [])]
    )
    criar_alerta(
        semeado, execucao, 2, "Groenlândia", datetime(2026, 3, 1, tzinfo=UTC), [("GL", NORM, [])]
    )

    visao = painel(semeado, "GL")

    assert visao.codigo == "GL"
    assert visao.nome == "Groenlândia (Dinamarca)"
    assert visao.tipo is TipoTerritorio.DEPENDENCIA
    assert visao.soberano == "DK"
    assert visao.bandeira == "GL"  # a própria bandeira (FR-031)
    assert visao.identidade_do_soberano is False
    assert visao.observacao_no_topo is False
    assert visao.nivel is NivelExibido.EVITAR  # o soberano é mais recente
    assert [a.titulo for a in visao.alertas] == ["Dinamarca", "Groenlândia"]
    assert visao.observacao is not None


def test_dependencia_usa_os_postos_do_soberano(semeado: Session, execucao: ExecucaoColeta) -> None:
    visao = painel(semeado, "GL")
    assert visao.postos
    assert {p.pais for p in visao.postos} == {"Dinamarca"}
    assert visao.fonte_postos is not None


# --------------------------------------------------------------------------- Kosovo e Malvinas
@pytest.mark.parametrize(
    ("codigo", "nome", "soberano"), [("XK", "Sérvia", "RS"), ("FK", "Argentina", "AR")]
)
def test_kosovo_e_malvinas_abrem_o_painel_do_soberano(
    semeado: Session, execucao: ExecucaoColeta, codigo: str, nome: str, soberano: str
) -> None:
    criar_alerta(semeado, execucao, 1, nome, datetime(2026, 5, 1, tzinfo=UTC), [(soberano, N, [])])

    visao = painel(semeado, codigo)

    assert visao.nome == nome
    assert visao.bandeira == soberano  # nunca XK nem FK
    assert visao.identidade_do_soberano is True
    assert visao.observacao_no_topo is True
    assert visao.observacao is not None
    assert visao.soberano == soberano
    assert visao.nivel is NivelExibido.NAO_VIAJAR
    assert [a.titulo for a in visao.alertas] == [nome]
    assert visao.postos  # os do soberano
    assert {p.pais for p in visao.postos} == {nome}
    assert visao.fonte_postos is not None


def test_so_kosovo_e_malvinas_trazem_a_observacao_no_topo(semeado: Session) -> None:
    for codigo in ("TW", "HK", "GL", "PE", "BR"):
        assert painel(semeado, codigo).observacao_no_topo is False


def test_taiwan_nao_tem_bandeira_e_traz_observacao(semeado: Session) -> None:
    visao = painel(semeado, "TW")
    assert visao.bandeira is None
    assert visao.observacao is not None
    assert visao.tipo is TipoTerritorio.DEPENDENCIA


# --------------------------------------------------------------------------- postos
def test_pais_com_postos_traz_postos_e_a_fonte(semeado: Session) -> None:
    visao = painel(semeado, "US")

    assert visao.eh_brasil is False
    assert len(visao.postos) > 5
    assert {p.pais for p in visao.postos} == {"Estados Unidos"}
    assert all(p.contato_coletado_em is None for p in visao.postos)  # nada coletado ainda
    assert visao.posto_responsavel is None
    assert visao.sem_posto_indicado is False

    washington = [p for p in visao.postos if p.cidade == "Washington"]
    assert len(washington) == 2
    assert washington[0].grupo == washington[1].grupo  # dividem o ícone
    assert visao.fonte_postos is not None
    assert visao.fonte_postos.conferido_em == date(2026, 10, 21)
    assert [(f.nome, f.licenca) for f in visao.fonte_postos.fontes] == [
        ("Itamaraty", None),
        ("Wikipédia", "CC BY-SA"),
    ]
    assert all(f.url.startswith("https://") for f in visao.fonte_postos.fontes)


def test_posto_traz_endereco_e_telefone_com_fonte_e_data_da_coleta(
    semeado: Session, execucao: ExecucaoColeta
) -> None:
    posto = painel(semeado, "US").postos[0]
    modelo = semeado.get(Posto, posto.id)
    assert modelo is not None
    modelo.endereco = "3006 Whitehaven St NW"
    modelo.telefone_plantao = "+1 202 555 0100"
    modelo.contato_coletado_em = AGORA
    modelo.contato_fonte_url = "https://www.gov.br/mre/washington"
    semeado.flush()

    atualizado = painel(semeado, "US").postos[0]

    assert atualizado.endereco == "3006 Whitehaven St NW"
    assert atualizado.telefone_plantao == "+1 202 555 0100"
    assert atualizado.contato_coletado_em == AGORA
    assert atualizado.contato_fonte_url == "https://www.gov.br/mre/washington"


def test_pais_sem_posto_indica_o_posto_responsavel_em_outro_pais(semeado: Session) -> None:
    visao = painel(semeado, "PR")  # Porto Rico, atendido por Miami

    assert visao.postos == ()
    assert visao.sem_posto_indicado is False
    assert visao.posto_responsavel is not None
    assert visao.posto_responsavel.cidade == "Miami"
    assert visao.posto_responsavel.pais == "Estados Unidos"
    assert visao.fonte_postos is not None  # o responsável também é dado de posto


def test_libia_orienta_procurar_o_itamaraty(semeado: Session) -> None:
    visao = painel(semeado, "LY")

    assert visao.sem_posto_indicado is True
    assert visao.postos == ()
    assert visao.posto_responsavel is None
    assert visao.fonte_postos is None  # nenhum posto na lista


def test_brasil_tem_painel_proprio_sem_postos(semeado: Session) -> None:
    visao = painel(semeado, "BR")

    assert visao.eh_brasil is True
    assert visao.nome == "Brasil"
    assert visao.postos == ()
    assert visao.posto_responsavel is None
    assert visao.fonte_postos is None
    assert visao.sem_posto_indicado is False


# --------------------------------------------------------------------------- não encontrado
@pytest.mark.parametrize("codigo", ["ZZ", "QQ", "-99", "xx", ""])
def test_codigo_desconhecido_levanta_nao_encontrado(semeado: Session, codigo: str) -> None:
    with pytest.raises(TerritorioNaoEncontrado):
        painel(semeado, codigo)


def test_area_neutra_levanta_nao_encontrado(semeado: Session) -> None:
    semeado.add(Territorio(codigo="EH", nome_pt="Saara Ocidental", tipo=TipoTerritorio.NEUTRO))
    semeado.flush()
    with pytest.raises(TerritorioNaoEncontrado):
        painel(semeado, "EH")
