"""Parágrafos de alerta e de visto a partir das visões do painel (contracts/textos-do-chat.md).

Ordem (FR-003): frase direta, dados, observação da fonte, fonte e data, avisos.
"""

from farol.chat import textos
from farol.chat.portas import (
    AlertaLido,
    MapaLido,
    PainelLido,
    Paragrafo,
    PermanenciaLida,
    Trecho,
    VistoLido,
)


def _simples(texto: str) -> Paragrafo:
    return (Trecho(texto),)


def _datas_do_alerta(alerta: AlertaLido) -> str:
    datas = f"publicado em {textos.data(alerta.publicado_em)}"
    if alerta.modificado_em is not None:
        datas += f"; modificado em {textos.data(alerta.modificado_em)}"
    return f" ({datas})"


def _dados_dos_alertas(painel: PainelLido) -> list[Paragrafo]:
    for alerta in painel.alertas:
        link = Trecho(alerta.titulo, alerta.url)
        if painel.nivel == "nao_verificado" and alerta.pendente:
            return [(Trecho("Confira o alerta original: "), link)]
        if painel.nivel != "nao_verificado" and alerta.define_nivel:
            datas = Trecho(_datas_do_alerta(alerta))
            return [(Trecho("Alerta que define o nível: "), link, datas)]
    return []


def paragrafos_do_alerta(painel: PainelLido, mapa: MapaLido) -> tuple[Paragrafo, ...]:
    paragrafos = [
        _simples(
            textos.frase_do_alerta(
                painel.nivel, painel.nome, painel.regiao_unica_do_alerta, mapa.dados_obtidos
            )
        )
    ]
    if painel.regioes:
        regioes = "; ".join(
            f'{r.nome} ("{textos.ROTULOS_DE_NIVEL[r.nivel]}")' for r in painel.regioes
        )
        paragrafos.append(_simples(f"Regiões com nível próprio: {regioes}."))
    paragrafos += _dados_dos_alertas(painel)
    if painel.observacao:
        paragrafos.append(_simples(f"Observação: {painel.observacao}"))

    data = f", atualizado em {textos.data(mapa.atualizado_em)}" if mapa.atualizado_em else ""
    paragrafos.append(
        (
            Trecho("Fonte: "),
            Trecho(textos.NOME_DO_PORTAL, textos.URL_DO_PORTAL_CONSULAR),
            Trecho(f"{data}."),
        )
    )
    if mapa.desatualizado:
        paragrafos.append(_simples(textos.AVISO_ALERTA_DESATUALIZADO))
    return tuple(paragrafos)


def _permanencia(permanencia: PermanenciaLida) -> str | None:
    if permanencia.tipo == "prazos_divergentes":
        return textos.PERMANENCIA_DIVERGENTE
    if permanencia.tipo == "varia_conforme_motivo":
        return textos.PERMANENCIA_VARIA
    return permanencia.texto


def paragrafos_do_visto(visto: VistoLido, nome_do_painel: str) -> tuple[Paragrafo, ...]:
    pais = visto.territorio_nome or nome_do_painel
    paragrafos = [
        _simples(textos.frase_do_visto(visto.situacao, pais, visto.aceita_rg)),
        _simples(f'Categoria: "{textos.ROTULOS_DE_VISTO[visto.situacao]}"'),
    ]
    if visto.rotulo_original is not None:
        paragrafos.append(_simples(f"Na fonte: {visto.rotulo_original}"))
    if visto.varia_conforme_motivo:
        paragrafos.append(_simples(textos.VARIA_CONFORME_O_MOTIVO))
    permanencia = _permanencia(visto.permanencia) if visto.permanencia else None
    if permanencia is not None:
        paragrafos.append(_simples(f"Permanência: {permanencia}"))
    if visto.origem == "soberano":
        entrada = (
            f"Vale a entrada do soberano: {visto.soberano_nome}."
            if visto.soberano_nome
            else "Vale a entrada do soberano."
        )
        paragrafos.append(_simples(f"Sem entrada própria na fonte para este território. {entrada}"))
    for observacao in visto.observacoes:
        if observacao.traducao is None:
            texto = f"Observação da fonte (não traduzido): {observacao.texto_original}"
        else:
            texto = f"Observação da fonte (tradução automática): {observacao.traducao}"
        paragrafos.append(_simples(texto))

    fonte = visto.fonte
    licenca = f"{fonte.licenca}, não oficial" if fonte.licenca else "não oficial"
    data = f", dado de {textos.data(visto.dado_de)}" if visto.dado_de else ""
    paragrafos.append(
        (Trecho("Fonte: "), Trecho(fonte.nome, fonte.url), Trecho(f" ({licenca}){data}."))
    )
    paragrafos.append(_simples(textos.AVISO_NAO_OFICIAL))
    if visto.desatualizado:
        paragrafos.append(_simples(textos.AVISO_VISTO_DESATUALIZADO))
    return tuple(paragrafos)
