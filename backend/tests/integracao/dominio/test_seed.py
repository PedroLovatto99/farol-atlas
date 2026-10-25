"""Seed: países, dependências, postos, responsáveis e fonte dos dados."""

import json
import shutil
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from farol.dominio import (
    FonteDados,
    Posto,
    Territorio,
    TipoTerritorio,
)
from farol.dominio.seed import ErroDeSeed, executar

DADOS = Path(__file__).resolve().parents[4] / "dados"
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


def contar(sessao: Session, modelo: type) -> int:
    return sessao.scalar(select(func.count()).select_from(modelo)) or 0


@pytest.fixture
def semeado(sessao: Session) -> Session:
    executar(sessao, DADOS, AGORA)
    return sessao


def territorio(sessao: Session, codigo: str) -> Territorio:
    encontrado = sessao.get(Territorio, codigo)
    assert encontrado is not None, codigo
    return encontrado


def test_exatamente_198_territorios_na_lista_do_itamaraty(semeado: Session) -> None:
    total = semeado.scalar(
        select(func.count()).select_from(Territorio).where(Territorio.na_lista_itamaraty.is_(True))
    )
    assert total == 198


def test_209_postos(semeado: Session) -> None:
    assert contar(semeado, Posto) == 209


def test_brasil_e_pais_com_nome_em_portugues(semeado: Session) -> None:
    brasil = territorio(semeado, "BR")
    assert brasil.tipo is TipoTerritorio.PAIS
    assert brasil.nome_pt == "Brasil"
    assert brasil.codigo_bandeira == "BR"


def test_paises_sem_posto_tem_responsavel_ou_sem_posto_indicado(semeado: Session) -> None:
    sem_posto = semeado.scalars(
        select(Territorio).where(
            (Territorio.posto_responsavel_id.is_not(None))
            | (Territorio.sem_posto_indicado.is_(True))
        )
    ).all()
    assert len(sem_posto) == 60
    iemen = territorio(semeado, "YE")
    responsavel = semeado.get(Posto, iemen.posto_responsavel_id)
    assert responsavel is not None
    assert responsavel.cidade == "Riade"
    assert iemen.icone_latitude is not None
    assert iemen.icone_longitude is not None


def test_responsavel_com_alias_de_cidade_cambera(semeado: Session) -> None:
    # A lista oficial grafa "Cambera"; o posto está cadastrado como "Camberra"
    com_camberra = [
        t
        for t in semeado.scalars(
            select(Territorio).where(Territorio.posto_responsavel_id.is_not(None))
        )
        if (p := semeado.get(Posto, t.posto_responsavel_id)) is not None and p.cidade == "Camberra"
    ]
    assert com_camberra, "algum país deveria ser atendido pelo posto de Camberra"


def test_san_marino_e_atendido_pela_embaixada_na_italia_e_nao_pela_santa_se(
    semeado: Session,
) -> None:
    responsavel = semeado.get(Posto, territorio(semeado, "SM").posto_responsavel_id)
    assert responsavel is not None
    assert responsavel.territorio_codigo == "IT"


def test_libia_nao_tem_posto_indicado(semeado: Session) -> None:
    libia = territorio(semeado, "LY")
    assert libia.sem_posto_indicado is True
    assert libia.posto_responsavel_id is None


def test_kosovo_e_malvinas_usam_a_identidade_do_soberano(semeado: Session) -> None:
    kosovo = territorio(semeado, "XK")
    assert kosovo.tipo is TipoTerritorio.DEPENDENCIA
    assert kosovo.soberano_codigo == "RS"
    assert kosovo.identidade_do_soberano is True
    assert kosovo.nome_pt == "Sérvia"
    assert kosovo.codigo_bandeira == "RS"
    assert kosovo.rotulo_busca == "Kosovo (Sérvia)"
    assert kosovo.termos_busca == ["Kosovo"]
    assert kosovo.observacao is not None
    assert "não reconhece" in kosovo.observacao

    malvinas = territorio(semeado, "FK")
    assert malvinas.soberano_codigo == "AR"
    assert malvinas.identidade_do_soberano is True
    assert malvinas.nome_pt == "Argentina"
    assert malvinas.codigo_bandeira == "AR"
    assert malvinas.rotulo_busca == "Malvinas (Argentina)"
    assert malvinas.termos_busca == ["Malvinas", "Ilhas Malvinas"]
    assert malvinas.observacao is not None
    assert "Reino Unido" in malvinas.observacao


def test_so_a_palestina_declara_que_as_regioes_cobrem_o_territorio_inteiro(
    semeado: Session,
) -> None:
    declarados = semeado.scalars(
        select(Territorio.codigo).where(Territorio.regioes_cobrem_o_pais.is_(True))
    ).all()
    assert list(declarados) == ["PS"]


def test_declaracao_de_regioes_para_codigo_desconhecido_falha_de_forma_ruidosa(
    sessao: Session, tmp_path: Path
) -> None:
    copia = tmp_path / "dados"
    shutil.copytree(DADOS, copia)
    arquivo = copia / "territorios" / "observacoes.yaml"
    arquivo.write_text(
        arquivo.read_text(encoding="utf-8") + "  ZZ:\n    regioes_cobrem_o_pais: true\n",
        encoding="utf-8",
    )
    with pytest.raises(ErroDeSeed, match="ZZ"):
        executar(sessao, copia, AGORA)


def test_demais_dependencias_tem_bandeira_propria_e_taiwan_nao_tem(semeado: Session) -> None:
    groenlandia = territorio(semeado, "GL")
    assert groenlandia.tipo is TipoTerritorio.DEPENDENCIA
    assert groenlandia.identidade_do_soberano is False
    assert groenlandia.codigo_bandeira == "GL"
    assert groenlandia.nome_pt == "Groenlândia (Dinamarca)"
    assert groenlandia.observacao is not None
    assert "Dinamarca" in groenlandia.observacao

    taiwan = territorio(semeado, "TW")
    assert taiwan.codigo_bandeira is None
    assert taiwan.soberano_codigo == "CN"
    assert taiwan.na_lista_itamaraty is True

    dependencias_com_identidade = semeado.scalars(
        select(Territorio.codigo).where(Territorio.identidade_do_soberano.is_(True))
    ).all()
    assert sorted(dependencias_com_identidade) == ["FK", "XK"]


def test_porto_rico_e_dependencia_dos_estados_unidos_atendida_por_miami(semeado: Session) -> None:
    porto_rico = territorio(semeado, "PR")
    assert porto_rico.tipo is TipoTerritorio.DEPENDENCIA
    assert porto_rico.soberano_codigo == "US"
    assert porto_rico.nome_pt == "Porto Rico (Estados Unidos)"
    assert porto_rico.codigo_bandeira == "PR"
    assert porto_rico.identidade_do_soberano is False
    assert porto_rico.na_lista_itamaraty is True
    assert porto_rico.observacao is not None
    assert "Estados Unidos" in porto_rico.observacao
    assert porto_rico.posto_responsavel_id is not None


def test_observacoes_das_dependencias_usam_a_preposicao_do_soberano(semeado: Session) -> None:
    groenlandia = territorio(semeado, "GL")
    assert groenlandia.observacao is not None
    assert groenlandia.observacao.startswith("Território da Dinamarca.")
    assert territorio(semeado, "PR").observacao is not None

    hong_kong = territorio(semeado, "HK")
    assert hong_kong.observacao is not None
    assert hong_kong.observacao.startswith("Região administrativa especial da China.")

    for codigo, observacao in semeado.execute(
        select(Territorio.codigo, Territorio.observacao).where(
            Territorio.tipo == TipoTerritorio.DEPENDENCIA
        )
    ).all():
        assert observacao and "{" not in observacao, codigo
        assert " de Estados Unidos" not in observacao, codigo


def test_busca_acha_christmas_e_cocos_pela_ilha_do_oceano_indico(semeado: Session) -> None:
    ilhas = territorio(semeado, "IOA")
    assert ilhas.nome_pt == "Ilha Christmas e Ilhas Cocos (Austrália)"
    assert {"Christmas", "Cocos"} <= set(ilhas.termos_busca)


def test_195_paises_e_43_dependencias(semeado: Session) -> None:
    linhas = semeado.execute(select(Territorio.tipo, func.count()).group_by(Territorio.tipo)).all()
    por_tipo = dict(linhas)
    assert por_tipo[TipoTerritorio.PAIS] == 195
    assert por_tipo[TipoTerritorio.DEPENDENCIA] == 43


def test_fonte_dos_postos_vem_do_fonte_yaml(semeado: Session) -> None:
    fonte = semeado.get(FonteDados, "postos")
    assert fonte is not None
    assert fonte.conferido_em == date(2026, 10, 21)
    assert [f["nome"] for f in fonte.fontes] == ["Itamaraty", "Wikipédia"]
    assert fonte.fontes[1]["licenca"] == "CC BY-SA"
    assert fonte.carregado_em == AGORA


def test_executar_duas_vezes_nao_duplica(sessao: Session) -> None:
    executar(sessao, DADOS, AGORA)
    antes = (contar(sessao, Territorio), contar(sessao, Posto), contar(sessao, FonteDados))
    executar(sessao, DADOS, AGORA)
    depois = (contar(sessao, Territorio), contar(sessao, Posto), contar(sessao, FonteDados))
    assert antes == depois


def test_executar_atualiza_a_fonte_quando_o_arquivo_muda(sessao: Session, tmp_path: Path) -> None:
    copia = tmp_path / "dados"
    shutil.copytree(DADOS, copia)
    executar(sessao, copia, AGORA)
    fonte_yaml = copia / "postos" / "fonte.yaml"
    fonte_yaml.write_text(
        fonte_yaml.read_text(encoding="utf-8").replace("2026-10-21", "2027-01-15"),
        encoding="utf-8",
    )
    executar(sessao, copia, AGORA)
    fonte = sessao.get(FonteDados, "postos")
    assert fonte is not None
    assert fonte.conferido_em == date(2027, 1, 15)


def test_responsavel_sem_posto_correspondente_falha_de_forma_ruidosa(
    sessao: Session, tmp_path: Path
) -> None:
    copia = tmp_path / "dados"
    shutil.copytree(DADOS, copia)
    csv_ = copia / "postos" / "jurisdicao_cumulativa.csv"
    csv_.write_text(
        csv_.read_text(encoding="utf-8").replace("Islamabade", "Atlantida"), encoding="utf-8"
    )
    with pytest.raises(ErroDeSeed, match="Atlantida"):
        executar(sessao, copia, AGORA)


def test_dependencia_com_soberano_desconhecido_falha_de_forma_ruidosa(
    sessao: Session, tmp_path: Path
) -> None:
    copia = tmp_path / "dados"
    shutil.copytree(DADOS, copia)
    arquivo = copia / "territorios" / "territorios.json"
    conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
    conteudo["dependencias"][0]["soberano_codigo"] = "ZZ"
    arquivo.write_text(json.dumps(conteudo), encoding="utf-8")
    with pytest.raises(ErroDeSeed, match="ZZ"):
        executar(sessao, copia, AGORA)
