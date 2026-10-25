"""Serviço de classificação: classifica os alertas que ainda não têm classificação para o hash.

Uma classificação por (alerta, hash). Falha de rede, tempo esgotado ou resposta inválida gravam
`falhou` com o motivo e nada em `nivel_territorio`; o alerta fica pendente (o país aparece como
"não verificado") e a próxima rodada tenta de novo. O serviço nunca derruba o site nem a rodada.

`reclassificar` refaz a classificação de um alerta já classificado (por id ou URL), por exemplo
depois de mudar uma regra. Se a nova tentativa falhar, a classificação que valia continua valendo.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from farol.classificacao.cadeia import EntradaDoAlerta
from farol.classificacao.esquema import Classificacao, normalizar_regioes, validar_resposta
from farol.dominio import (
    Alerta,
    AlertaRepositorio,
    ClassificacaoRepositorio,
    NivelTerritorio,
    StatusClassificacao,
    TerritorioRepositorio,
    TipoTerritorio,
)
from farol.dominio import Classificacao as ClassificacaoSalva
from farol.infra import Relogio, obter_logger

TAMANHO_MAXIMO_DO_ERRO = 500

_log = obter_logger("farol.classificacao")


class Classificador(Protocol):
    nome_do_modelo: str

    def classificar(
        self, entrada: EntradaDoAlerta, territorios: Mapping[str, str]
    ) -> Classificacao: ...


@dataclass(frozen=True)
class ResultadoDaClassificacao:
    classificados: int
    falhas: int


class AlertaNaoEncontrado(Exception):
    """Nenhum alerta com esse id ou essa URL."""


@dataclass(frozen=True)
class ResultadoDaReclassificacao:
    alerta_id: int
    url: str
    titulo: str
    ok: bool
    motivo: str | None  # por que não reclassificou; nulo quando deu certo


class ServicoDeClassificacao:
    def __init__(self, sessao: Session, classificador: Classificador, relogio: Relogio) -> None:
        self._sessao = sessao
        self._classificador = classificador
        self._relogio = relogio
        self._alertas = AlertaRepositorio(sessao)
        self._classificacoes = ClassificacaoRepositorio(sessao)
        self._territorios = TerritorioRepositorio(sessao)

    def classificar_pendentes(self) -> ResultadoDaClassificacao:
        alertas = self._alertas.listar_para_classificar()
        if not alertas:
            return ResultadoDaClassificacao(0, 0)

        rotulos = self._rotulos()
        classificados = falhas = 0
        for alerta in alertas:
            if self._classificar(alerta, rotulos):
                classificados += 1
            else:
                falhas += 1
        self._sessao.flush()
        _log.info("classificação: %d ok, %d com falha", classificados, falhas)
        return ResultadoDaClassificacao(classificados, falhas)

    def reclassificar(self, referencia: str) -> ResultadoDaReclassificacao:
        """Chama o modelo de novo para um alerta (id ou URL), mesmo já classificado."""
        alerta = self._buscar(referencia)
        recusa = self._motivo_de_nao_poder_classificar(alerta)
        if recusa is not None:
            return self._resultado(alerta, recusa)
        assert alerta.hash is not None
        resposta, motivo = self._consultar_o_modelo(alerta, self._rotulos())
        if resposta is None:
            antiga = self._classificacoes.obter(alerta.id, alerta.hash)
            if antiga is None or antiga.status is not StatusClassificacao.OK:
                self._gravar(alerta, None, motivo)
        else:
            self._gravar(alerta, resposta, None)
        self._sessao.flush()
        return self._resultado(alerta, motivo)

    def _buscar(self, referencia: str) -> Alerta:
        referencia = referencia.strip()
        alerta = (
            self._alertas.obter_por_id(int(referencia))
            if referencia.isdecimal()
            else self._alertas.obter_por_url(referencia)
        )
        if alerta is None:
            raise AlertaNaoEncontrado(referencia)
        return alerta

    @staticmethod
    def _motivo_de_nao_poder_classificar(alerta: Alerta) -> str | None:
        if alerta.removido_em is not None:
            return "o alerta saiu da lista do Itamaraty"
        if not alerta.pagina_lida or alerta.hash is None or alerta.texto is None:
            return "a página do alerta ainda não foi lida"
        return None

    @staticmethod
    def _resultado(alerta: Alerta, motivo: str | None) -> ResultadoDaReclassificacao:
        return ResultadoDaReclassificacao(
            alerta_id=alerta.id,
            url=alerta.url,
            titulo=alerta.titulo,
            ok=motivo is None,
            motivo=motivo,
        )

    def _rotulos(self) -> dict[str, str]:
        return {
            t.codigo: t.rotulo_busca or t.nome_pt
            for t in self._territorios.listar_todos()
            if t.tipo is not TipoTerritorio.NEUTRO
        }

    def _consultar_o_modelo(
        self, alerta: Alerta, rotulos: Mapping[str, str]
    ) -> tuple[Classificacao | None, str | None]:
        """A resposta já normalizada e validada, ou o motivo de não ter servido."""
        assert alerta.texto is not None
        entrada = EntradaDoAlerta(
            titulo=alerta.titulo,
            categoria=alerta.categoria,
            publicado_em=alerta.publicado_em,
            modificado_em=alerta.modificado_em,
            texto=alerta.texto,
        )
        try:
            resposta = validar_resposta(
                normalizar_regioes(self._classificador.classificar(entrada, rotulos)),
                rotulos.keys(),
            )
        except Exception as erro:  # modelo externo: qualquer falha deixa o alerta pendente
            motivo = f"{type(erro).__name__}: {erro}"[:TAMANHO_MAXIMO_DO_ERRO]
            _log.warning("alerta %s sem classificação válida: %s", alerta.url, motivo)
            return None, motivo
        return resposta, None

    def _classificar(self, alerta: Alerta, rotulos: Mapping[str, str]) -> bool:
        assert alerta.hash is not None  # garantido pela consulta
        resposta, motivo = self._consultar_o_modelo(alerta, rotulos)
        self._gravar(alerta, resposta, motivo)
        return resposta is not None

    def _gravar(self, alerta: Alerta, resposta: Classificacao | None, erro: str | None) -> None:
        assert alerta.hash is not None
        salva = self._classificacoes.obter(alerta.id, alerta.hash)
        if salva is None:
            salva = ClassificacaoSalva(alerta_id=alerta.id, alerta_hash=alerta.hash)
            self._classificacoes.adicionar(salva)
        salva.status = (
            StatusClassificacao.OK if resposta is not None else StatusClassificacao.FALHOU
        )
        salva.e_alerta_de_viagem = resposta.e_alerta_de_viagem if resposta else None
        salva.modelo = self._classificador.nome_do_modelo
        salva.erro = erro
        salva.classificado_em = self._relogio.agora()
        salva.niveis = [
            NivelTerritorio(
                territorio_codigo=t.codigo,
                nivel_pais=t.nivel_pais,
                regioes=[{"nome": r.nome.strip(), "nivel": r.nivel.value} for r in t.regioes],
            )
            for t in (resposta.territorios if resposta else [])
        ]
