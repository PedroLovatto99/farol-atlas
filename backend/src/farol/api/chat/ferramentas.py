"""`ResolvedorDePaises` e `ConsultaDeNivel` do chat, sobre as mesmas funções do painel e do mapa."""

import re
import unicodedata

from sqlalchemy.orm import Session

from farol.chat import (
    AlertaQueRege,
    NivelConsultado,
    PaisEncontrado,
    ResultadoDaResolucao,
)
from farol.dominio import (
    AlertaRepositorio,
    ExecucaoRepositorio,
    Territorio,
    TerritorioRepositorio,
    TipoExecucao,
    TipoTerritorio,
)
from farol.mapa import montar_painel, nomes_para_titulo

# Nomes que, sozinhos, servem a mais de um território: o chat nunca escolhe, pergunta qual deles
_AMBIGUOS: dict[str, tuple[str, ...]] = {
    "congo": ("CG", "CD"),
    "guine": ("GN", "GQ", "GW"),
    "coreia": ("KP", "KR"),
    "ilhas virgens": ("VG", "VI"),
}


def _normalizar(texto: str) -> str:
    """Sem acento, em minúsculas e com um espaço entre as palavras (como o `titulo_cita`)."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.lower().split())


def _padrao(nome: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![a-z0-9]){re.escape(nome)}(?![a-z0-9])")


class ResolvedorDePaisesDoSite:
    """Acha países e territórios em um texto, com os nomes da busca do site.

    Usa `nomes_para_titulo` (nome base, `termos_busca` e `rotulo_busca`), sem acento, sem diferença
    de maiúscula e por palavra inteira. Quando mais de um nome casa no mesmo trecho, vale o mais
    longo ("Guiné-Bissau" não é "Guiné"). Lê os territórios uma vez, ao nascer.
    """

    def __init__(self, sessao: Session) -> None:
        territorios = [
            t
            for t in TerritorioRepositorio(sessao).listar_todos()
            if t.tipo is not TipoTerritorio.NEUTRO
        ]
        self._territorios = {t.codigo: t for t in territorios}
        self._nomes = {
            t.codigo: sorted(
                # um nome ambíguo nunca resolve sozinho para um território, mesmo se for termo dele
                {_normalizar(n) for n in nomes_para_titulo(t) if n} - _AMBIGUOS.keys(),
                key=len,
                reverse=True,
            )
            for t in territorios
        }

    def _achado(self, territorio: Territorio) -> PaisEncontrado:
        return PaisEncontrado(
            codigo=territorio.codigo, nome=territorio.nome_pt, soberano=territorio.soberano_codigo
        )

    def resolver(self, texto: str) -> ResultadoDaResolucao:
        restante = _normalizar(texto)
        # nomes mais longos primeiro; o trecho já usado sai do texto para não casar de novo
        casamentos: list[tuple[int, str]] = []
        for codigo, nomes in self._nomes.items():
            for nome in nomes:
                if nome and _padrao(nome).search(restante):
                    casamentos.append((len(nome), codigo))
                    break
        encontrados: list[str] = []
        for _, codigo in sorted(casamentos, key=lambda c: (-c[0], c[1])):
            for nome in self._nomes[codigo]:
                padrao = _padrao(nome)
                if padrao.search(restante):
                    restante = padrao.sub(" ", restante)
                    encontrados.append(codigo)
                    break
        ambiguos = tuple(
            tuple(self._achado(self._territorios[c]) for c in candidatos if c in self._territorios)
            for palavra, candidatos in _AMBIGUOS.items()
            if _padrao(palavra).search(restante)
        )
        return ResultadoDaResolucao(
            encontrados=tuple(self._achado(self._territorios[c]) for c in sorted(encontrados)),
            ambiguos=ambiguos,
        )


class ConsultaDeNivelDoSite:
    """O nível de um território, exatamente como o painel o monta (`montar_painel`)."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def consultar(self, codigo: str) -> NivelConsultado:
        visao = montar_painel(self._sessao, codigo)
        ultima = ExecucaoRepositorio(self._sessao).ultima_completa(TipoExecucao.ALERTAS)
        regente = next((a for a in visao.alertas if a.define_nivel), None)
        alerta_que_rege = None
        if regente is not None:
            alerta = AlertaRepositorio(self._sessao).obter_por_url(regente.url)
            if alerta is not None:
                alerta_que_rege = AlertaQueRege(
                    id=alerta.id,
                    titulo=regente.titulo,
                    data=regente.modificado_em or regente.publicado_em,
                    url=regente.url,
                )
        return NivelConsultado(
            codigo=visao.codigo,
            nome=visao.nome,
            nivel=visao.nivel.value,
            regioes=tuple(r.nome for r in visao.regioes),
            so_regional=visao.regiao_unica_do_alerta,
            alerta_que_rege=alerta_que_rege,
            observacao=visao.observacao,
            atualizado_em=ultima.finalizada_em if ultima is not None else None,
            dados_obtidos=ultima is not None,
        )
