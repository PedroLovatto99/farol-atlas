"""Saída do classificador de alertas e a validação depois da resposta do modelo.

Contrato: specs/001-mapa-alertas-viagem/contracts/classificador-saida.md. O modelo só preenche
este esquema; qualquer coisa fora dele (nível desconhecido, campo extra, código que não existe no
mapa) invalida a resposta inteira e o alerta fica pendente.
"""

from collections.abc import Collection

from pydantic import BaseModel, ConfigDict, Field

from farol.dominio import NivelAlerta, separar_nivel_do_pais


class RespostaInvalida(Exception):
    """A resposta do modelo não passa na validação; o motivo vai para `classificacao.erro`."""


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegiaoClassificada(_Estrito):
    nome: str = Field(description='Região dentro do país, ex.: "Sul do Líbano"')
    nivel: NivelAlerta


class TerritorioClassificado(_Estrito):
    codigo: str = Field(description="Código ISO-2 do país (ou de dependência) citado no alerta")
    nivel_pais: NivelAlerta | None = Field(
        default=None,
        description="Nível para o país inteiro; nulo se o alerta só vale para regiões do país",
    )
    regioes: list[RegiaoClassificada] = Field(default_factory=list)


class Classificacao(_Estrito):
    e_alerta_de_viagem: bool = Field(
        description="Falso para aviso de fraude, notícia, orientação geral etc."
    )
    territorios: list[TerritorioClassificado] = Field(
        default_factory=list, description="Vazio se e_alerta_de_viagem for falso"
    )


def normalizar_regioes(resposta: Classificacao) -> Classificacao:
    """Passa para o nível do país as "regiões" que são o país inteiro ("demais regiões do país").

    O prompt já pede isso, mas o modelo erra; a regra de verdade fica aqui, em código.
    """
    territorios = []
    for territorio in resposta.territorios:
        nivel_pais, nomeadas = separar_nivel_do_pais(
            territorio.nivel_pais, [(r.nome, r.nivel) for r in territorio.regioes]
        )
        territorios.append(
            TerritorioClassificado(
                codigo=territorio.codigo,
                nivel_pais=nivel_pais,
                regioes=[RegiaoClassificada(nome=nome, nivel=nivel) for nome, nivel in nomeadas],
            )
        )
    return resposta.model_copy(update={"territorios": territorios})


def validar_resposta(resposta: Classificacao, permitidos: Collection[str]) -> Classificacao:
    """Confere a resposta já no formato do esquema. Levanta `RespostaInvalida` se algo falhar."""
    if not resposta.e_alerta_de_viagem:
        if resposta.territorios:
            raise RespostaInvalida("não é alerta de viagem, mas veio território: exige lista vazia")
        return resposta
    if not resposta.territorios:
        raise RespostaInvalida(
            "é alerta de viagem, mas não veio nenhum território: exige ao menos um"
        )

    vistos: set[str] = set()
    for territorio in resposta.territorios:
        codigo = territorio.codigo
        if codigo not in permitidos:
            raise RespostaInvalida(f"código {codigo!r} não existe no mapa")
        if codigo in vistos:
            raise RespostaInvalida(f"território repetido: {codigo!r}")
        vistos.add(codigo)
        if territorio.nivel_pais is None and not territorio.regioes:
            raise RespostaInvalida(f"{codigo}: sem nível para o país e sem nenhuma região")
        for regiao in territorio.regioes:
            if not regiao.nome.strip():
                raise RespostaInvalida(f"{codigo}: região sem nome")
    return resposta
