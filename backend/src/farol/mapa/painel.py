"""Monta a visão de `GET /paises/{codigo}`: o painel de um país ou dependência.

Reaproveita a regra do nível (`nivel.py`). Número fixo de consultas (princípio III): última coleta
completa (1), territórios (1), alertas confirmados com classificações e níveis (3, só se já houve
coleta completa), postos (1) e fonte dos postos (1).

Dependências: o painel traz os alertas e os postos do próprio território e do soberano (FR-031).
Kosovo e Malvinas abrem o painel do soberano: nome, bandeira e dados dele, com a observação no
topo (FR-030, FR-034); isso já vem de `identidade_do_soberano` no cadastro do território.
"""

from sqlalchemy.orm import Session

from farol.dominio import (
    CODIGO_DO_BRASIL,
    Alerta,
    AlertaRepositorio,
    ExecucaoRepositorio,
    FonteDadosRepositorio,
    NivelAlerta,
    Posto,
    PostoRepositorio,
    Territorio,
    TerritorioRepositorio,
    TipoExecucao,
    TipoTerritorio,
)
from farol.mapa.nivel import (
    AlertaParaNivel,
    ItemDoAlerta,
    NivelDoTerritorio,
    TerritorioParaNivel,
    calcular_niveis,
    titulo_cita,
)
from farol.mapa.preparo import alerta_para_nivel, base_do_nome, grupo_do_posto, nomes_para_titulo
from farol.mapa.visoes import (
    AlertaDoPais,
    FonteDeDados,
    FontePostos,
    PostoNoPainel,
    VisaoDoPainel,
)

CHAVE_FONTE_DOS_POSTOS = "postos"


class TerritorioNaoEncontrado(Exception):
    """Código desconhecido ou área neutra: não há painel (FR-016, FR-032)."""


def _item_do_alerta(alerta: AlertaParaNivel, codigos: list[str]) -> ItemDoAlerta | None:
    """O que o alerta diz sobre o território; na falta, o que diz sobre o soberano."""
    for codigo in codigos:
        for item in alerta.itens or ():
            if item.territorio == codigo:
                return item
    return None


def _posto_no_painel(posto: Posto, nomes: dict[str, str]) -> PostoNoPainel:
    return PostoNoPainel(
        id=posto.id,
        tipo=posto.tipo,
        cidade=posto.cidade,
        pais=base_do_nome(nomes[posto.territorio_codigo]),
        grupo=grupo_do_posto(posto),
        endereco=posto.endereco,
        telefone_plantao=posto.telefone_plantao,
        contato_coletado_em=posto.contato_coletado_em,
        contato_fonte_url=posto.contato_fonte_url,
    )


def _escolher_postos(
    cadeia: list[Territorio], modelos: list[Posto], nomes: dict[str, str]
) -> tuple[tuple[PostoNoPainel, ...], PostoNoPainel | None, bool]:
    """Postos, posto responsável e "sem posto indicado" do primeiro da cadeia (território, depois
    soberano) que tenha algum deles."""
    for t in cadeia:
        proprios = tuple(
            _posto_no_painel(p, nomes) for p in modelos if p.territorio_codigo == t.codigo
        )
        if proprios:
            return proprios, None, False
        if t.posto_responsavel_id is not None:
            responsavel = next((p for p in modelos if p.id == t.posto_responsavel_id), None)
            if responsavel is not None:
                return (), _posto_no_painel(responsavel, nomes), False
        if t.sem_posto_indicado:
            return (), None, True
    return (), None, False


def _alertas_do_painel(
    alertas: list[AlertaParaNivel],
    modelos: dict[int, Alerta],
    codigos: list[str],
    nomes: list[str],
    nivel: NivelDoTerritorio,
) -> tuple[AlertaDoPais, ...]:
    """Todos os alertas de viagem que citam o território, do mais recente ao mais antigo."""
    linhas: list[tuple[AlertaParaNivel, AlertaDoPais]] = []
    for alerta in alertas:
        if alerta.itens is None:  # pendente: o título é o que identifica o país (FR-008)
            if not titulo_cita(alerta.titulo, nomes):
                continue
            normalizada = False
        else:
            item = _item_do_alerta(alerta, codigos)
            if item is None:
                continue
            normalizada = item.nivel_pais is NivelAlerta.NORMALIZADA
        modelo = modelos[alerta.id]
        linhas.append(
            (
                alerta,
                AlertaDoPais(
                    titulo=alerta.titulo,
                    url=modelo.url,
                    publicado_em=modelo.publicado_em,
                    modificado_em=modelo.modificado_em,
                    define_nivel=alerta.id == nivel.alerta_id,
                    situacao_normalizada=normalizada,
                    pendente=alerta.itens is None,
                ),
            )
        )
    linhas.sort(key=lambda par: (par[0].data_ref, par[1].define_nivel, par[0].id), reverse=True)
    return tuple(dto for _, dto in linhas)


def montar_painel(sessao: Session, codigo: str) -> VisaoDoPainel:
    todos = {t.codigo: t for t in TerritorioRepositorio(sessao).listar_todos()}
    territorio = todos.get(codigo)
    if territorio is None or territorio.tipo is TipoTerritorio.NEUTRO:
        raise TerritorioNaoEncontrado(codigo)
    soberano = todos.get(territorio.soberano_codigo) if territorio.soberano_codigo else None
    envolvidos: list[Territorio] = [territorio] + ([soberano] if soberano else [])
    codigos = [t.codigo for t in envolvidos]
    nomes = [n for t in envolvidos for n in nomes_para_titulo(t)]

    # --- nível e alertas
    dados_obtidos = ExecucaoRepositorio(sessao).ultima_completa(TipoExecucao.ALERTAS) is not None
    modelos = (
        {a.id: a for a in AlertaRepositorio(sessao).listar_confirmados_ativos()}
        if dados_obtidos
        else {}
    )
    alertas = [alerta_para_nivel(a) for a in modelos.values()]
    nivel = calcular_niveis(
        [
            TerritorioParaNivel(
                t.codigo, t.soberano_codigo, nomes_para_titulo(t), t.regioes_cobrem_o_pais
            )
            for t in envolvidos
        ],
        alertas,
        houve_coleta_completa=dados_obtidos,
    )[territorio.codigo]

    # --- postos (FR-011, FR-013, FR-014): o território usa o que é dele (postos, ou posto
    # responsável, ou "sem posto indicado"); só quando não tem nada herda do soberano
    eh_brasil = territorio.codigo == CODIGO_DO_BRASIL
    ids_responsaveis = [t.posto_responsavel_id for t in envolvidos if t.posto_responsavel_id]
    modelos_de_postos = (
        [] if eh_brasil else PostoRepositorio(sessao).listar_para_painel(codigos, ids_responsaveis)
    )
    nomes_dos_paises = {c: t.nome_pt for c, t in todos.items()}
    postos, responsavel, sem_posto_indicado = _escolher_postos(
        [] if eh_brasil else envolvidos, modelos_de_postos, nomes_dos_paises
    )

    fonte = (
        FonteDadosRepositorio(sessao).obter(CHAVE_FONTE_DOS_POSTOS)
        if postos or responsavel
        else None
    )
    return VisaoDoPainel(
        codigo=territorio.codigo,
        nome=territorio.nome_pt,
        tipo=territorio.tipo,
        soberano=territorio.soberano_codigo,
        bandeira=territorio.codigo_bandeira,
        identidade_do_soberano=territorio.identidade_do_soberano,
        nivel=nivel.nivel,
        regioes=nivel.regioes,
        regiao_unica_do_alerta=nivel.so_regional,
        observacao=territorio.observacao,
        observacao_no_topo=territorio.identidade_do_soberano,
        eh_brasil=eh_brasil,
        alertas=_alertas_do_painel(alertas, modelos, codigos, nomes, nivel),
        postos=postos,
        posto_responsavel=responsavel,
        sem_posto_indicado=sem_posto_indicado,
        fonte_postos=(
            FontePostos(
                conferido_em=fonte.conferido_em,
                fontes=tuple(
                    FonteDeDados(f["nome"], f["url"], f.get("licenca")) for f in fonte.fontes
                ),
            )
            if fonte is not None
            else None
        ),
    )
