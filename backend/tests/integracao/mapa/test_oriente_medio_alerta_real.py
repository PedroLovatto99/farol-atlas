"""O alerta "Oriente Médio" de 04/07/2026 (Líbano e Palestina), da coleta ao mapa e ao painel.

O Itamaraty escreve "Não viajar: Sul do Líbano" e "Evitar viagens não essenciais: Líbano (demais
regiões do país)". O país inteiro fica em "evitar" (laranja) e o Sul ganha só a borda vermelha.
Nenhum teste acessa a rede: o modelo é um classificador de mentira que devolve o que o Gemini
devolveu de verdade (as "demais regiões do país" como se fossem uma região).

A Palestina declara em observacoes.yaml que Gaza e a Cisjordânia cobrem o território inteiro: a cor
é o nível menos grave entre elas (evite) e a borda, a da região mais grave (não viaje).
"""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.orm import Session

from farol.classificacao import (
    Classificacao as Resposta,
)
from farol.classificacao import (
    EntradaDoAlerta,
    ServicoDeClassificacao,
)
from farol.coleta import extrair_alerta, hash_do_alerta
from farol.dominio import Alerta, ExecucaoColeta, NivelAlerta, TipoExecucao
from farol.dominio.seed import executar
from farol.mapa import NivelExibido, NivelRegional, montar_mapa, montar_painel

if TYPE_CHECKING:
    from tests.conftest import RelogioFalso

RAIZ = Path(__file__).resolve().parents[4]
DADOS = RAIZ / "dados"
FIXTURES = RAIZ / "backend" / "tests" / "fixtures" / "govbr"
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)

# o que o Gemini 3.6 Flash respondeu para esse alerta (conferido no banco de desenvolvimento)
RESPOSTA_DO_GEMINI = {
    "e_alerta_de_viagem": True,
    "territorios": [
        {
            "codigo": "LB",
            "nivel_pais": None,
            "regioes": [
                {"nome": "Sul do Líbano", "nivel": "nao_viajar"},
                {"nome": "demais regiões do país", "nivel": "evitar"},
            ],
        },
        {
            "codigo": "PS",
            "nivel_pais": None,
            "regioes": [
                {"nome": "Faixa de Gaza", "nivel": "nao_viajar"},
                {"nome": "Cisjordânia", "nivel": "evitar"},
            ],
        },
    ],
}


class ClassificadorDeMentira:
    nome_do_modelo = "teste:gemini-gravado"

    def classificar(self, entrada: EntradaDoAlerta, territorios: Mapping[str, str]) -> Resposta:
        return Resposta.model_validate(RESPOSTA_DO_GEMINI)


@pytest.fixture
def libano_classificado(sessao: Session, relogio: "RelogioFalso") -> Session:
    """O alerta real, classificado pelo serviço e confirmado por uma coleta completa."""
    executar(sessao, DADOS, AGORA)
    execucao = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS,
        iniciada_em=AGORA - timedelta(minutes=5),
        finalizada_em=AGORA,
        paginas_esperadas=1,
        paginas_lidas=1,
        lista_lida_inteira=True,
        completa=True,
    )
    sessao.add(execucao)
    sessao.flush()

    extraido = extrair_alerta((FIXTURES / "alerta_2.html").read_text(encoding="utf-8"))
    hash_do_texto = hash_do_alerta(extraido.titulo, extraido.texto)
    alerta = Alerta(
        url="https://www.gov.br/mre/alerta_2",
        titulo=extraido.titulo,
        texto=extraido.texto,
        html_corpo=extraido.html_corpo,
        categoria=extraido.categoria,
        publicado_em=extraido.publicado_em,
        modificado_em=extraido.modificado_em,
        hash=hash_do_texto,
        primeira_coleta_em=AGORA,
        ultima_coleta_em=AGORA,
        pagina_lida=True,
        confirmado_execucao_id=execucao.id,
        confirmado_hash=hash_do_texto,
        confirmado_titulo=extraido.titulo,
        confirmado_data_ref=extraido.modificado_em or extraido.publicado_em,
    )
    sessao.add(alerta)
    sessao.flush()

    resultado = ServicoDeClassificacao(
        sessao, ClassificadorDeMentira(), relogio
    ).classificar_pendentes()
    assert resultado.classificados == 1
    sessao.expire_all()
    return sessao


def test_libano_fica_em_evitar_e_so_o_sul_ganha_a_borda_vermelha(
    libano_classificado: Session, relogio: "RelogioFalso"
) -> None:
    libano = next(
        t for t in montar_mapa(libano_classificado, relogio).territorios if t.codigo == "LB"
    )

    assert libano.nivel is NivelExibido.EVITAR
    assert [(r.nome, r.nivel) for r in libano.regioes] == [
        ("Sul do Líbano", NivelRegional.NAO_VIAJAR)
    ]


def test_painel_do_libano_tem_o_nivel_do_pais_no_topo_e_so_as_regioes_nomeadas(
    libano_classificado: Session,
) -> None:
    painel = montar_painel(libano_classificado, "LB")

    assert painel.nivel is NivelExibido.EVITAR
    assert [(r.nome, r.nivel) for r in painel.regioes] == [
        ("Sul do Líbano", NivelRegional.NAO_VIAJAR)
    ]
    assert (
        painel.regiao_unica_do_alerta is False
    )  # há nível para o país: nada de "vale só para a região"
    assert [a.define_nivel for a in painel.alertas] == [True]


def test_a_classificacao_gravada_do_libano_guarda_o_nivel_do_pais(
    libano_classificado: Session,
) -> None:
    [alerta] = libano_classificado.query(Alerta).all()
    [classificacao] = alerta.classificacoes
    libano = next(n for n in classificacao.niveis if n.territorio_codigo == "LB")

    assert libano.nivel_pais is NivelAlerta.EVITAR
    assert libano.regioes == [{"nome": "Sul do Líbano", "nivel": "nao_viajar"}]


def test_palestina_fica_em_evitar_com_a_borda_de_gaza(
    libano_classificado: Session, relogio: "RelogioFalso"
) -> None:
    palestina = next(
        t for t in montar_mapa(libano_classificado, relogio).territorios if t.codigo == "PS"
    )

    assert palestina.nivel is NivelExibido.EVITAR
    assert [(r.nome, r.nivel) for r in palestina.regioes] == [
        ("Faixa de Gaza", NivelRegional.NAO_VIAJAR)
    ]


def test_painel_da_palestina_tem_evite_no_topo_e_lista_as_duas_regioes(
    libano_classificado: Session,
) -> None:
    painel = montar_painel(libano_classificado, "PS")

    assert painel.nivel is NivelExibido.EVITAR
    assert [(r.nome, r.nivel) for r in painel.regioes] == [
        ("Faixa de Gaza", NivelRegional.NAO_VIAJAR),
        ("Cisjordânia", NivelRegional.EVITAR),
    ]
    assert painel.regiao_unica_do_alerta is False


def test_a_classificacao_gravada_da_palestina_continua_so_regional(
    libano_classificado: Session,
) -> None:
    """A declaração vale na leitura: o que o modelo disse não é reescrito."""
    [alerta] = libano_classificado.query(Alerta).all()
    [classificacao] = alerta.classificacoes
    palestina = next(n for n in classificacao.niveis if n.territorio_codigo == "PS")

    assert palestina.nivel_pais is None
