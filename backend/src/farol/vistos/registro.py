"""Conversões entre o candidato da coleta, o registro do banco e o JSON da mudança retida.

O JSON de `mudanca_retida.candidato` é o registro completo que seria aplicado: confirmar grava este
conteúdo em `requisito_visto`. Funções puras, sem sessão: servem ao serviço de coleta e ao do dono.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from farol.dominio import CategoriaDeVisto, MotivoOutraSituacao, RequisitoVisto
from farol.vistos.consolidacao import Candidato, Observacao
from farol.vistos.retencao import Situacao

# O candidato de uma retenção cuja mudança é a linha ter saído da fonte: confirmar apaga o registro
CANDIDATO_SEM_LINHA: dict[str, Any] = {"sem_informacao": True}

# `hash -> {"traducao", "traduzido_em", "modelo"}`: o que já se sabe traduzido
Traducoes = Mapping[str, Mapping[str, Any]]


def observacao_em_json(
    observacao: Observacao, traducoes: Traducoes | None = None
) -> dict[str, Any]:
    """A observação como fica no banco; usa a tradução já conhecida do mesmo texto, se houver."""
    sabida = (traducoes or {}).get(observacao.hash, {})
    return {
        "texto": observacao.texto,
        "hash": observacao.hash,
        "traducao": sabida.get("traducao"),
        "traduzido_em": sabida.get("traduzido_em"),
        "modelo": sabida.get("modelo"),
    }


def traducoes_conhecidas(observacoes: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """As traduções já feitas nas observações gravadas, por hash do texto."""
    return {
        o["hash"]: {k: o.get(k) for k in ("traducao", "traduzido_em", "modelo")}
        for o in observacoes
        if o.get("traducao") is not None
    }


def completar_traducoes(
    observacoes: Sequence[Mapping[str, Any]], traducoes: Traducoes
) -> list[dict[str, Any]]:
    """Uma cópia das observações, com a tradução conhecida nas que ainda estão sem ela."""
    completas = []
    for observacao in observacoes:
        copia = dict(observacao)
        sabida = traducoes.get(copia["hash"])
        if copia.get("traducao") is None and sabida is not None:
            copia.update(sabida)
        completas.append(copia)
    return completas


def situacao_do_requisito(requisito: RequisitoVisto) -> Situacao:
    return Situacao(
        categoria=requisito.categoria,
        hash_fonte=requisito.hash_fonte,
        aceita_rg=requisito.aceita_rg,
        motivo_outra=requisito.motivo_outra,
        varia_conforme_motivo=requisito.varia_conforme_motivo,
        permanencia_tipo=requisito.permanencia_tipo,
        permanencia_texto=requisito.permanencia_texto,
    )


def situacao_do_candidato(candidato: Candidato) -> Situacao:
    return Situacao(
        categoria=candidato.categoria,
        hash_fonte=candidato.hash_fonte,
        aceita_rg=candidato.aceita_rg,
        motivo_outra=candidato.motivo_outra,
        varia_conforme_motivo=candidato.varia_conforme_motivo,
        permanencia_tipo=candidato.permanencia.tipo.value,
        permanencia_texto=candidato.permanencia.texto,
    )


def candidato_em_json(candidato: Candidato, traducoes: Traducoes) -> dict[str, Any]:
    """O registro completo que seria aplicado, em JSON (guardado na mudança retida)."""
    return {
        "categoria": candidato.categoria.value,
        "motivo_outra": candidato.motivo_outra.value if candidato.motivo_outra else None,
        "rotulo_original": candidato.rotulo_original,
        "linhas_fonte": [linha.como_dicionario() for linha in candidato.linhas_fonte],
        "hash_fonte": candidato.hash_fonte,
        "aceita_rg": candidato.aceita_rg,
        "varia_conforme_motivo": candidato.varia_conforme_motivo,
        "permanencia_tipo": candidato.permanencia.tipo.value,
        "permanencia_texto": candidato.permanencia.texto,
        "observacoes": [observacao_em_json(o, traducoes) for o in candidato.observacoes],
    }


def preencher_requisito(
    requisito: RequisitoVisto, dados: Mapping[str, Any], lido_em: datetime, coleta_id: int
) -> None:
    """Grava no registro o conteúdo de um candidato (JSON) e a coleta que o leu."""
    motivo = dados["motivo_outra"]
    requisito.categoria = CategoriaDeVisto(dados["categoria"])
    requisito.motivo_outra = MotivoOutraSituacao(motivo) if motivo else None
    requisito.rotulo_original = dados["rotulo_original"]
    requisito.linhas_fonte = list(dados["linhas_fonte"])
    requisito.hash_fonte = dados["hash_fonte"]
    requisito.aceita_rg = dados["aceita_rg"]
    requisito.varia_conforme_motivo = dados["varia_conforme_motivo"]
    requisito.permanencia_tipo = dados["permanencia_tipo"]
    requisito.permanencia_texto = dados["permanencia_texto"]
    requisito.observacoes = [dict(o) for o in dados["observacoes"]]
    requisito.lido_em = lido_em
    requisito.coleta_id = coleta_id
