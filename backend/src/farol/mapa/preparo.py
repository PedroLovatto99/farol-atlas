"""Converte linhas do banco na entrada da regra do nível. Compartilhado por mapa e painel."""

from farol.dominio import (
    Alerta,
    NivelAlerta,
    NivelTerritorio,
    Posto,
    Territorio,
    separar_nivel_do_pais,
)
from farol.mapa.nivel import AlertaParaNivel, ItemDoAlerta, RegiaoDoAlerta


def base_do_nome(nome: str) -> str:
    """ "Groenlândia (Dinamarca)" -> "Groenlândia"."""
    return nome.split(" (")[0].strip()


def nomes_para_titulo(territorio: Territorio) -> tuple[str, ...]:
    """Como o título de um alerta pode citar o território (identifica o país de um pendente)."""
    nomes = [base_do_nome(territorio.nome_pt), *territorio.termos_busca]
    if territorio.rotulo_busca:
        nomes.append(base_do_nome(territorio.rotulo_busca))
    return tuple(dict.fromkeys(n for n in nomes if n))


def grupo_do_posto(posto: Posto) -> str:
    """Postos na mesma coordenada dividem o ícone no mapa (FR-018d)."""
    return f"{float(posto.latitude)},{float(posto.longitude)}"


def _item_do_alerta(nivel: NivelTerritorio) -> ItemDoAlerta:
    """ "Demais regiões do país" gravada como região (classificação antiga) vale como o país."""
    nivel_pais, regioes = separar_nivel_do_pais(
        nivel.nivel_pais, [(r["nome"], NivelAlerta(r["nivel"])) for r in nivel.regioes]
    )
    return ItemDoAlerta(
        nivel.territorio_codigo,
        nivel_pais,
        tuple(RegiaoDoAlerta(nome, n) for nome, n in regioes),
    )


def alerta_para_nivel(alerta: Alerta) -> AlertaParaNivel:
    classificacao = alerta.classificacao_vigente()
    itens: tuple[ItemDoAlerta, ...] | None
    if classificacao is None:
        itens = None  # pendente: sem classificação válida para o conteúdo confirmado
    elif not classificacao.e_alerta_de_viagem:
        itens = ()
    else:
        itens = tuple(_item_do_alerta(n) for n in classificacao.niveis)
    return AlertaParaNivel(
        id=alerta.id,
        titulo=alerta.confirmado_titulo or alerta.titulo,
        data_ref=alerta.confirmado_data_ref or alerta.publicado_em,
        itens=itens,
    )
