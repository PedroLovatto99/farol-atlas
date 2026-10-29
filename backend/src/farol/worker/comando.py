"""Linha de comando do worker.

python -m farol.worker                      fica de pé e coleta no horário agendado
python -m farol.worker coletar --alertas    uma rodada agora (coleta + classificação) e sai
python -m farol.worker coletar --postos     coleta endereço e telefone dos postos agora e sai
python -m farol.worker coletar --vistos     coleta os vistos da Wikipédia agora e sai
python -m farol.worker reclassificar <id|url>   chama o modelo de novo para um alerta e sai

Meios do dono para os vistos (dentro do contêiner do worker; não há rota HTTP nem tela):

python -m farol.worker vistos pendentes                    o que espera o dono
python -m farol.worker vistos confirmar <codigo>|--todos   aplica a(s) mudança(s) retida(s)
python -m farol.worker vistos rejeitar <codigo>            rejeita a mudança retida
python -m farol.worker vistos ignorar-nome "<nome>" --motivo "<texto>"

Códigos de saída: 0 feito (em `coletar`, coleta completa ou válida); 1 coleta que não foi completa
ou válida; 2 uso errado ou configuração (por exemplo `CONTATO_COLETA` ausente).
"""

import argparse
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, TextIO

from sqlalchemy.orm import Session

from farol.classificacao import (
    AlertaNaoEncontrado,
    ResultadoDaReclassificacao,
)
from farol.coleta import ResultadoDaColetaDePostos
from farol.dominio import (
    CategoriaDeVisto,
    ColetaVistosRepositorio,
    ExecucaoRepositorio,
    ResultadoDaColetaDeVistos,
    TipoExecucao,
)
from farol.infra import (
    FUSO_DE_BRASILIA,
    RelogioDoSistema,
    abrir_sessao,
    configurar_logs,
    obter_configuracoes,
    obter_logger,
)
from farol.vistos import (
    ErroDoDono,
    ItemPendente,
    MudancaPendente,
    PendenciasDoDono,
    ProximaTentativa,
    RegraPendente,
    ResumoDaColetaDeVistos,
    ServicoDoDono,
)
from farol.worker.agenda import preparar_agendador, retomada_de_vistos
from farol.worker.jobs import (
    ClassificadorIndisponivel,
    ContatoInvalido,
    ResultadoDaRodada,
    reclassificar_real,
    rodada_real,
    rodada_real_de_postos,
    rodada_real_de_vistos,
)

_log = obter_logger("farol.worker")

R = ResultadoDaColetaDeVistos


class MeiosDoDono(Protocol):
    """O que os comandos `vistos ...` pedem ao serviço do dono (o `ServicoDoDono` cumpre)."""

    def listar_pendentes(self) -> PendenciasDoDono: ...

    def confirmar(self, codigo: str) -> MudancaPendente: ...

    def confirmar_todos(self) -> tuple[str, ...]: ...

    def rejeitar(self, codigo: str) -> None: ...

    def ignorar_nome(self, nome: str, motivo: str) -> None: ...


def _montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m farol.worker", description=__doc__)
    comandos = parser.add_subparsers(dest="comando")
    coletar = comandos.add_parser("coletar", help="roda uma coleta agora e sai")
    alvo = coletar.add_mutually_exclusive_group(required=True)
    alvo.add_argument("--alertas", action="store_true", help="alertas do Portal Consular")
    alvo.add_argument("--postos", action="store_true", help="endereço e telefone dos postos")
    alvo.add_argument("--vistos", action="store_true", help="vistos para brasileiros (Wikipédia)")
    reclassificar = comandos.add_parser(
        "reclassificar", help="refaz a classificação de um alerta (não coleta nada)"
    )
    reclassificar.add_argument("alerta", help="id do alerta no banco ou a URL dele")

    vistos = comandos.add_parser("vistos", help="meios do dono para os vistos (não coleta nada)")
    acoes = vistos.add_subparsers(dest="acao", required=True)
    acoes.add_parser("pendentes", help="lista tudo o que espera o dono")
    confirmar = acoes.add_parser("confirmar", help="aplica a(s) mudança(s) retida(s)")
    quais = confirmar.add_mutually_exclusive_group(required=True)
    quais.add_argument("codigo", nargs="?", help="código do território com mudança retida")
    quais.add_argument("--todos", action="store_true", help="confirma todas as retidas")
    rejeitar = acoes.add_parser("rejeitar", help="rejeita a mudança retida de um território")
    rejeitar.add_argument("codigo", help="código do território com mudança retida")
    ignorar = acoes.add_parser("ignorar-nome", help="ignora de propósito um nome pendente")
    ignorar.add_argument("nome", help="o nome, como na fonte")
    ignorar.add_argument("--motivo", required=True, help="por que o nome é ignorado")
    return parser


def _resumo_da_reclassificacao(resultado: ResultadoDaReclassificacao) -> str:
    if resultado.ok:
        return f"Alerta {resultado.alerta_id} reclassificado: {resultado.titulo}\n{resultado.url}"
    return (
        f"Alerta {resultado.alerta_id} NÃO reclassificado: {resultado.motivo}\n"
        "A classificação que valia continua valendo."
    )


def _reclassificar(
    referencia: str, reclassificar: Callable[[str], ResultadoDaReclassificacao]
) -> int:
    try:
        resultado = reclassificar(referencia)
    except AlertaNaoEncontrado:
        print(f"Não há alerta com o id ou a URL {referencia!r}.")
        return 2
    except ClassificadorIndisponivel as erro:
        print(f"Não foi possível reclassificar: {erro}")
        return 2
    print(_resumo_da_reclassificacao(resultado))
    return 0 if resultado.ok else 1


def _resumo(resultado: ResultadoDaRodada) -> str:
    coleta, classificacao = resultado.coleta, resultado.classificacao
    linhas = [
        f"Coleta {'completa' if coleta.completa else 'INCOMPLETA'}: "
        f"{coleta.paginas_lidas} de {coleta.paginas_esperadas} páginas lidas",
        f"Alertas novos ou alterados: {len(coleta.para_classificar)}"
        f" | removidos: {coleta.removidos}",
        f"Classificação: {classificacao.classificados} ok, {classificacao.falhas} com falha",
    ]
    if coleta.motivo_interrupcao:
        linhas.insert(1, f"Motivo: {coleta.motivo_interrupcao}")
    return "\n".join(linhas)


def _resumo_de_postos(resultado: ResultadoDaColetaDePostos) -> str:
    linhas = [
        f"Coleta de postos {'completa' if resultado.completa else 'INCOMPLETA'}: "
        f"{resultado.paginas_lidas} de {resultado.paginas_esperadas} páginas lidas",
        f"Postos com endereço: {resultado.postos_com_endereco}"
        f" | com telefone: {resultado.postos_com_telefone}",
    ]
    if resultado.motivo_interrupcao:
        linhas.insert(1, f"Motivo: {resultado.motivo_interrupcao}")
    return "\n".join(linhas)


# --------------------------------------------------------------------------- vistos: texto
_NOME_DO_RESULTADO = {
    R.VALIDA: "VÁLIDA",
    R.REJEITADA: "REJEITADA",
    R.ADIADA: "ADIADA",
    R.FALHOU: "FALHOU",
    R.BLOQUEADA: "BLOQUEADA",
}
_NOME_DA_CATEGORIA = {
    CategoriaDeVisto.ISENTO: "Isento de visto",
    CategoriaDeVisto.VISTO_NA_CHEGADA: "Visto na chegada",
    CategoriaDeVisto.AUTORIZACAO_ELETRONICA: "Autorização ou visto eletrônico",
    CategoriaDeVisto.VISTO_EXIGIDO: "Visto exigido",
    CategoriaDeVisto.OUTRA_SITUACAO: "Outra situação",
}
SEM_INFORMACAO = "Sem informação de visto"
SEM_DATA = "—"


def _nome_da_categoria(categoria: CategoriaDeVisto | None, aceita_rg: bool) -> str:
    """O nome da situação como o site mostra; nulo é "sem informação"."""
    if categoria is None:
        return SEM_INFORMACAO
    if categoria is CategoriaDeVisto.ISENTO and aceita_rg:
        return "Isento, entrada com RG"
    return _NOME_DA_CATEGORIA[categoria]


def _exibido_e_lido(mudanca: MudancaPendente) -> str:
    exibido = _nome_da_categoria(mudanca.categoria_exibida, mudanca.aceita_rg_exibido)
    lido = _nome_da_categoria(mudanca.categoria_lida, mudanca.aceita_rg_lido)
    return f"{exibido} → {lido}"


def _data(instante: datetime | None) -> str:
    if instante is None:
        return SEM_DATA
    return instante.astimezone(FUSO_DE_BRASILIA).strftime("%d/%m/%Y")


def _plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _quando_tentar_de_novo(proxima: ProximaTentativa) -> str:
    if proxima is ProximaTentativa.AMANHA:
        return "Próxima tentativa: amanhã, às 05:13 (America/Sao_Paulo)."
    return "Próxima tentativa: na próxima segunda-feira, às 05:13 (America/Sao_Paulo)."


def _resumo_de_vistos(resumo: ResumoDaColetaDeVistos) -> str:
    nome = _NOME_DO_RESULTADO[resumo.resultado]
    if not resumo.valida:
        return (
            f"Coleta de vistos {nome}: {resumo.motivo}\n"
            f"{_quando_tentar_de_novo(resumo.proxima_tentativa)}"
        )
    edicao = (
        resumo.ultima_edicao_fonte.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC")
        if resumo.ultima_edicao_fonte
        else SEM_DATA
    )
    linhas = [
        f"Coleta de vistos {nome}: {resumo.paises_reconhecidos} países reconhecidos "
        f"(mínimo {resumo.minimo})",
        f"Artigo: revisão {resumo.revisao_fonte}, última edição em {edicao}",
        f"Dados aplicados: {resumo.aplicadas} | sem mudança: {resumo.sem_mudanca}"
        f" | retidos: {len(resumo.retidas)}",
    ]
    if resumo.retidas:
        linhas.append("Retidos (esperam confirmação; veja `vistos pendentes`):")
        for retida in resumo.retidas:
            exibido = _nome_da_categoria(retida.categoria_exibida, retida.aceita_rg_exibido)
            lido = _nome_da_categoria(retida.categoria_lida, retida.aceita_rg_lido)
            linhas.append(f"  {retida.codigo}  {exibido} → {lido}")
    linhas.append(
        f"Nomes não reconhecidos: {len(resumo.nomes_nao_reconhecidos)}"
        f" | rótulos não reconhecidos: {len(resumo.rotulos_nao_reconhecidos)}"
    )
    if resumo.nomes_nao_reconhecidos:
        linhas.append(f"  Nomes: {', '.join(resumo.nomes_nao_reconhecidos)}")
    if resumo.rotulos_nao_reconhecidos:
        linhas.append(f"  Rótulos: {', '.join(resumo.rotulos_nao_reconhecidos)}")
    if resumo.regras_para_reconfirmar:
        linhas.append(
            f"Regras por país a reconfirmar: {', '.join(resumo.regras_para_reconfirmar)}"
            " (veja `vistos pendentes`)"
        )
    linhas.append(
        f"Traduções: {resumo.traducoes_novas} novas "
        f"({_plural(resumo.lotes_de_traducao, 'lote', 'lotes')}), "
        f"{resumo.traducoes_falhas} {'falha' if resumo.traducoes_falhas == 1 else 'falhas'}"
    )
    return "\n".join(linhas)


def _onde_apareceu(item: ItemPendente) -> str:
    nomes = [str(c.get("nome_na_fonte", "")) for c in item.contexto if isinstance(c, dict)]
    return f"({', '.join(n for n in nomes if n)})" if any(nomes) else ""


def _linhas_de_itens(titulo: str, itens: Sequence[ItemPendente]) -> list[str]:
    return [
        f"{titulo} ({len(itens)})",
        *(f"  {item.valor}  {_onde_apareceu(item)}".rstrip() for item in itens),
    ]


def _linha_da_regra(regra: RegraPendente) -> str:
    return (
        f"  {regra.codigo}  a nota mudou; hash esperado {regra.hash_esperado}, "
        f'hash novo {regra.hash_lido}; texto novo: "{regra.texto}"'
    )


def _pendentes(pendencias: PendenciasDoDono) -> str:
    retidas = pendencias.retidas
    linhas = [f"Mudanças retidas ({len(retidas)})"]
    if retidas:
        largura = max(len("exibido → lido"), *(len(_exibido_e_lido(m)) for m in retidas))
        linhas.append(
            f"  {'código':<6}  {'exibido → lido':<{largura}}  {'desde':<10}  dado exibido de"
        )
        linhas.extend(
            f"  {m.codigo:<6}  {_exibido_e_lido(m):<{largura}}  {_data(m.desde):<10}  "
            f"{_data(m.dado_exibido_de)}"
            for m in retidas
        )
    linhas += _linhas_de_itens("Nomes não reconhecidos", pendencias.nomes)
    linhas += _linhas_de_itens("Rótulos não reconhecidos", pendencias.rotulos)
    linhas.append(f"Regras por país a reconfirmar ({len(pendencias.regras)})")
    linhas.extend(_linha_da_regra(r) for r in pendencias.regras)
    return "\n".join(linhas)


# --------------------------------------------------------------------------- vistos: comandos
def _executar_do_dono(
    escolhido: argparse.Namespace, dono: Callable[[], AbstractContextManager[MeiosDoDono]]
) -> int:
    """`vistos pendentes|confirmar|rejeitar|ignorar-nome`. O que o serviço recusa sai com 2."""
    try:
        with dono() as meios:
            if escolhido.acao == "pendentes":
                texto = _pendentes(meios.listar_pendentes())
            elif escolhido.acao == "confirmar" and escolhido.todos:
                codigos = meios.confirmar_todos()
                texto = (
                    f"Confirmadas {_plural(len(codigos), 'mudança', 'mudanças')}: "
                    f"{', '.join(codigos)}"
                    if codigos
                    else "Não há mudanças retidas para confirmar."
                )
            elif escolhido.acao == "confirmar":
                mudanca = meios.confirmar(escolhido.codigo)
                texto = f"Confirmado: {mudanca.codigo} ({_exibido_e_lido(mudanca)})"
            elif escolhido.acao == "rejeitar":
                meios.rejeitar(escolhido.codigo)
                texto = (
                    f"Rejeitada a mudança de {escolhido.codigo.strip().upper()}. "
                    "Vale enquanto a fonte mantiver o mesmo valor lido."
                )
            else:
                meios.ignorar_nome(escolhido.nome, escolhido.motivo)
                texto = f"Nome ignorado: {escolhido.nome} ({escolhido.motivo.strip()})"
    except ErroDoDono as erro:
        print(erro)
        return 2
    print(texto)
    return 0


def executar_comando(
    argumentos: Sequence[str],
    *,
    rodada: Callable[[], ResultadoDaRodada],
    rodada_de_postos: Callable[[], ResultadoDaColetaDePostos],
    reclassificar: Callable[[str], ResultadoDaReclassificacao] | None = None,
    rodada_de_vistos: Callable[[], ResumoDaColetaDeVistos] | None = None,
    dono: Callable[[], AbstractContextManager[MeiosDoDono]] | None = None,
) -> int:
    """Executa um comando de execução única. Devolve o código de saída."""
    escolhido = _montar_parser().parse_args(list(argumentos))
    if escolhido.comando == "reclassificar" and reclassificar is not None:
        return _reclassificar(escolhido.alerta, reclassificar)
    if escolhido.comando == "vistos" and dono is not None:
        return _executar_do_dono(escolhido, dono)
    if escolhido.comando != "coletar":
        raise SystemExit(2)  # sem comando: quem chama sobe o agendador
    try:
        if escolhido.postos:
            resultado_de_postos = rodada_de_postos()
            print(_resumo_de_postos(resultado_de_postos))
            return 0 if resultado_de_postos.completa else 1
        if escolhido.vistos:
            if rodada_de_vistos is None:
                raise SystemExit(2)
            resumo_de_vistos = rodada_de_vistos()
            print(_resumo_de_vistos(resumo_de_vistos))
            return 0 if resumo_de_vistos.valida else 1
        resultado = rodada()
    except ContatoInvalido as erro:
        print(f"Não foi possível coletar: {erro}")
        return 2
    print(_resumo(resultado))
    return 0 if resultado.coleta.completa else 1


@contextmanager
def _dono_real() -> Iterator[ServicoDoDono]:
    """O serviço do dono numa sessão que confirma ao sair sem erro e desfaz se houver."""
    with abrir_sessao() as sessao:
        yield ServicoDoDono(sessao, RelogioDoSistema())


@dataclass(frozen=True)
class SituacaoDeVistosNaPartida:
    ultima_coleta_valida: datetime | None  # a que o site mostra; nulo se nunca houve
    ultima_tentativa_bloqueada: bool  # a última tentativa, de qualquer tipo, foi bloqueada
    retomada: datetime | None  # a tentativa de "amanhã" que a última tentativa deixou pendente


def situacao_de_vistos_na_partida(sessao: Session) -> SituacaoDeVistosNaPartida:
    """O que o worker precisa saber dos vistos ao subir.

    A coleta da partida depende da última coleta VÁLIDA (tentativas que falharam, foram adiadas ou
    rejeitadas não contam) e de a última tentativa não ter sido BLOQUEADA: depois de um bloqueio,
    a próxima tentativa é a da agenda semanal. A retomada vem da última tentativa, seja qual for.
    """
    coletas = ColetaVistosRepositorio(sessao)
    valida = coletas.ultima_valida()
    tentativa = coletas.ultima_tentativa()
    return SituacaoDeVistosNaPartida(
        ultima_coleta_valida=(valida.finalizada_em or valida.iniciada_em) if valida else None,
        ultima_tentativa_bloqueada=(
            tentativa is not None and tentativa.resultado is ResultadoDaColetaDeVistos.BLOQUEADA
        ),
        retomada=(
            retomada_de_vistos(
                tentativa.resultado,
                tentativa.adiamentos_seguidos,
                tentativa.falhas_seguidas,
                tentativa.iniciada_em,
            )
            if tentativa
            else None
        ),
    )


def servir_agenda() -> None:
    """Fica de pé coletando no horário (e na partida, se a última coleta estiver velha)."""
    configuracoes = obter_configuracoes()
    with abrir_sessao() as sessao:
        execucoes = ExecucaoRepositorio(sessao)
        tentativa = execucoes.ultima_tentativa(TipoExecucao.ALERTAS)
        tentativa_de_postos = execucoes.ultima_tentativa(TipoExecucao.POSTOS)
        ultima = tentativa.iniciada_em if tentativa is not None else None
        ultima_de_postos = tentativa_de_postos.iniciada_em if tentativa_de_postos else None
        vistos = situacao_de_vistos_na_partida(sessao)

    def rodada() -> None:
        resultado = rodada_real(configuracoes)
        _log.info("rodada concluída\n%s", _resumo(resultado))

    def rodada_de_postos() -> None:
        resultado = rodada_real_de_postos(configuracoes)
        _log.info("rodada de postos concluída\n%s", _resumo_de_postos(resultado))

    def rodada_de_vistos() -> ProximaTentativa:
        resumo = rodada_real_de_vistos(configuracoes, agendada=True)
        _log.info("rodada de vistos concluída\n%s", _resumo_de_vistos(resumo))
        return resumo.proxima_tentativa

    agendador = preparar_agendador(
        rodada,
        ultima_tentativa=ultima,
        agora=RelogioDoSistema().agora(),
        limite_horas=configuracoes.limite_horas_partida,
        rodada_de_postos=rodada_de_postos,
        ultima_tentativa_de_postos=ultima_de_postos,
        rodada_de_vistos=rodada_de_vistos,
        ultima_coleta_valida_de_vistos=vistos.ultima_coleta_valida,
        ultima_tentativa_de_vistos_bloqueada=vistos.ultima_tentativa_bloqueada,
        retomada_de_vistos=vistos.retomada,
    )
    _log.info(
        "worker iniciado: alertas todo dia às 06:17, postos todo dia 1 às 05:43 e vistos "
        "toda segunda às 05:13 (America/Sao_Paulo)"
    )
    agendador.start()  # bloqueia até receber o sinal de parada


def configurar_saida_em_utf8(saida: TextIO) -> None:
    """Os resumos têm "→" e "—", que o console padrão do Windows (cp1252) não codifica. A saída vai
    em UTF-8; o "?" (`errors="replace"`) fica só como último recurso, para um caractere que nem
    o UTF-8 consiga escrever não derrubar o comando com `UnicodeEncodeError`."""
    reconfigurar = getattr(saida, "reconfigure", None)
    if callable(reconfigurar):
        reconfigurar(encoding="utf-8", errors="replace")


def main(argumentos: Sequence[str]) -> int:
    configurar_saida_em_utf8(sys.stdout)
    configurar_saida_em_utf8(sys.stderr)
    configurar_logs()
    if not argumentos:
        servir_agenda()
        return 0
    configuracoes = obter_configuracoes()
    return executar_comando(
        argumentos,
        rodada=lambda: rodada_real(configuracoes),
        rodada_de_postos=lambda: rodada_real_de_postos(configuracoes),
        reclassificar=lambda referencia: reclassificar_real(configuracoes, referencia),
        rodada_de_vistos=lambda: rodada_real_de_vistos(configuracoes),
        dono=_dono_real,
    )
