"""Retenção por país (FR-010a): o que a coleta aplica e o que fica esperando o dono.

`decidir_retencao` é uma função pura. Compara o que o site mostra (`exibido`) com o que a coleta de
hoje leu (`lido`, já passado pelo dicionário) e diz o que fazer. As regras:

1. Primeira coleta válida: aplica tudo, não há dado anterior.
2. Fonte igual à exibida (mesmo hash): a mudança, se houver, vem do dicionário; já foi decidida
   pelo dono ao atualizá-lo, então aplica sem reter (12g).
3. Fonte mudada: retém se o país passa para uma categoria **menos exigente** (isento < visto na
   chegada < autorização < visto exigido; vindo de "Outra situação" ou de "sem informação" para
   qualquer categoria da ordem também conta) **ou** se passa a aceitar o RG. Qualquer outra mudança
   (mais exigente, "Outra situação", prazo, observações) aplica.
4. A linha do país sair da fonte é uma mudança para "sem informação" e também fica retida: o país
   mantém o último dado válido, com a data dele, até o dono confirmar. Se a linha voltar com o
   valor exibido, a retenção fecha como `revertida`, sem confirmação; um vandalismo que apaga
   linhas e é desfeito nunca deixa país sem informação.
5. Havendo uma retenção aberta (pendente ou rejeitada) do país: se a fonte voltou ao valor exibido,
   ela fecha como `revertida`; se a fonte ainda traz o valor retido, nada novo (a pendente só
   atualiza a coleta; a rejeitada não retém de novo); se a fonte trouxe outro valor, fecha como
   `superada` e a decisão recomeça.
"""

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from farol.dominio import CategoriaDeVisto, EstadoDaRetencao, MotivoOutraSituacao
from farol.vistos.dicionario import ORDEM_DE_EXIGENCIA

# O "hash lido" de uma retenção cuja mudança é a linha ter saído da fonte (não há fonte para o hash)
HASH_SEM_LINHA = hashlib.sha256(b"a fonte nao traz linha para o pais").hexdigest()


class AcaoDaRetencao(StrEnum):
    SEM_MUDANCA = "sem_mudanca"  # nada a gravar; o registro só renova a data da leitura
    APLICAR = "aplicar"  # o candidato passa a ser o dado exibido
    RETER = "reter"  # abre uma mudança pendente (inclusive a saída da linha); mantém o dado antigo
    ATUALIZAR_RETIDA = "atualizar_retida"  # a pendente continua; só aponta para a coleta nova
    MANTER_REJEITADA = "manter_rejeitada"  # a rejeição segue valendo; nada novo


@dataclass(frozen=True)
class Situacao:
    """O que importa de um visto para decidir: a fonte (hash) e o que o dicionário derivou dela."""

    categoria: CategoriaDeVisto
    hash_fonte: str
    aceita_rg: bool = False
    motivo_outra: MotivoOutraSituacao | None = None
    varia_conforme_motivo: bool = False
    permanencia_tipo: str = "nenhuma"
    permanencia_texto: str | None = None

    def mesmos_derivados(self, outra: "Situacao") -> bool:
        """Tudo o que vem do dicionário e das regras do código, sem olhar para o hash."""
        return (
            self.categoria,
            self.aceita_rg,
            self.motivo_outra,
            self.varia_conforme_motivo,
            self.permanencia_tipo,
            self.permanencia_texto,
        ) == (
            outra.categoria,
            outra.aceita_rg,
            outra.motivo_outra,
            outra.varia_conforme_motivo,
            outra.permanencia_tipo,
            outra.permanencia_texto,
        )


@dataclass(frozen=True)
class Aberta:
    """A retenção aberta do país: pendente (espera o dono) ou rejeitada (o dono disse que não)."""

    estado: EstadoDaRetencao
    hash_fonte_lido: str


@dataclass(frozen=True)
class DecisaoDeRetencao:
    acao: AcaoDaRetencao
    encerrar: EstadoDaRetencao | None = None  # `revertida` ou `superada`: fecha a retenção aberta


def _para_menos_exigente(exibido: Situacao, lido: Situacao) -> bool:
    if lido.aceita_rg and not exibido.aceita_rg:
        return True  # passar a aceitar o RG retém como a categoria (12h)
    if lido.categoria not in ORDEM_DE_EXIGENCIA:
        return False  # "Outra situação" é aplicada
    if exibido.categoria not in ORDEM_DE_EXIGENCIA:
        return True  # de "Outra situação" para uma categoria da ordem (12d)
    return ORDEM_DE_EXIGENCIA.index(lido.categoria) < ORDEM_DE_EXIGENCIA.index(exibido.categoria)


def _decidir_sem_retencao_aberta(
    exibido: Situacao | None,
    lido: Situacao | None,
    *,
    primeira_coleta: bool,
    fonte_ja_lida: bool,
) -> AcaoDaRetencao:
    if lido is None:
        # a linha não está na fonte: sem registro nada muda; com registro, a saída fica retida
        return AcaoDaRetencao.SEM_MUDANCA if exibido is None else AcaoDaRetencao.RETER
    if primeira_coleta:
        return AcaoDaRetencao.APLICAR  # 12e
    if exibido is None:
        # de "sem informação": categoria da ordem retém (12d), exceto se a linha já estava na fonte
        # e só o dicionário passou a reconhecê-la; "Outra situação" aplica
        if fonte_ja_lida or lido.categoria not in ORDEM_DE_EXIGENCIA:
            return AcaoDaRetencao.APLICAR
        return AcaoDaRetencao.RETER
    if exibido.hash_fonte == lido.hash_fonte:
        # a fonte não mudou: só o dicionário pode ter mudado o que se deriva dela (12g)
        return (
            AcaoDaRetencao.SEM_MUDANCA if exibido.mesmos_derivados(lido) else AcaoDaRetencao.APLICAR
        )
    return AcaoDaRetencao.RETER if _para_menos_exigente(exibido, lido) else AcaoDaRetencao.APLICAR


def _fonte_voltou_ao_exibido(exibido: Situacao | None, lido: Situacao | None) -> bool:
    if exibido is None or lido is None:
        return exibido is None and lido is None
    return exibido.hash_fonte == lido.hash_fonte


def decidir_retencao(
    exibido: Situacao | None,
    lido: Situacao | None,
    *,
    primeira_coleta: bool = False,
    aberta: Aberta | None = None,
    fonte_ja_lida: bool = False,
) -> DecisaoDeRetencao:
    """Decide o que fazer com um país depois de uma coleta válida.

    `exibido` é nulo quando o país não tem registro ("sem informação"); `lido` é nulo quando a
    fonte não traz linha para ele. `fonte_ja_lida` só vale para um país sem registro: a linha dele
    já estava na fonte (como nome pendente de revisão) e só o dicionário passou a reconhecê-la.
    """
    acao = _decidir_sem_retencao_aberta(
        exibido, lido, primeira_coleta=primeira_coleta, fonte_ja_lida=fonte_ja_lida
    )
    if aberta is None or primeira_coleta:
        return DecisaoDeRetencao(acao)
    if _fonte_voltou_ao_exibido(exibido, lido):
        return DecisaoDeRetencao(acao, EstadoDaRetencao.REVERTIDA)
    hash_lido = lido.hash_fonte if lido is not None else HASH_SEM_LINHA
    if acao is AcaoDaRetencao.RETER and hash_lido == aberta.hash_fonte_lido:
        if aberta.estado is EstadoDaRetencao.PENDENTE:
            return DecisaoDeRetencao(AcaoDaRetencao.ATUALIZAR_RETIDA)
        return DecisaoDeRetencao(AcaoDaRetencao.MANTER_REJEITADA)
    return DecisaoDeRetencao(acao, EstadoDaRetencao.SUPERADA)
