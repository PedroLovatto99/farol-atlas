"""Script de backup: dump pelo compose, compactado, só as últimas N cópias, sem apagar em falha.

Roda o script de verdade, com um `docker` de mentira no PATH. Precisa do bash; sem ele, não roda.
"""

import gzip
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[4]
SCRIPT = RAIZ / "ferramentas" / "backup-banco.sh"
BASH_DO_GIT = Path(r"C:\Program Files\Git\bin\bash.exe")

DOCKER_FALSO = """#!/usr/bin/env bash
echo "$@" >> "$DOCKER_REGISTRO"
if [ "${DOCKER_FALHA:-}" = 1 ]; then
  echo "pg_dump: erro de conexão" >&2
  exit 1
fi
printf '%s' "${DOCKER_SAIDA-CREATE TABLE alerta (id int);}"
"""


def _bash() -> str | None:
    if os.name == "nt":  # no Windows, o bash que serve é o do Git (o outro é o do WSL)
        return str(BASH_DO_GIT) if BASH_DO_GIT.exists() else None
    return shutil.which("bash")


pytestmark = pytest.mark.skipif(_bash() is None, reason="sem bash")


@pytest.fixture
def ambiente(tmp_path: Path) -> dict[str, str]:
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    docker = bin_falso / "docker"
    docker.write_text(DOCKER_FALSO, encoding="utf-8", newline="\n")
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
    return {
        **os.environ,
        "PATH": f"{bin_falso.as_posix()}{os.pathsep}{os.environ['PATH']}",
        "DESTINO_BACKUP": (tmp_path / "copias").as_posix(),
        "DOCKER_REGISTRO": (tmp_path / "docker.log").as_posix(),
    }


def rodar(ambiente: dict[str, str], **extra: str) -> subprocess.CompletedProcess[str]:
    bash = _bash()
    assert bash is not None
    return subprocess.run(
        [bash, SCRIPT.as_posix()],
        env={**ambiente, **extra},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def copias(ambiente: dict[str, str]) -> list[Path]:
    return sorted(Path(ambiente["DESTINO_BACKUP"]).glob("farol-*.sql.gz"))


def criar_antigas(ambiente: dict[str, str], quantidade: int) -> list[Path]:
    destino = Path(ambiente["DESTINO_BACKUP"])
    destino.mkdir(parents=True, exist_ok=True)
    criadas = []
    for n in range(quantidade):
        arquivo = destino / f"farol-20260101-00000{n}.sql.gz"
        arquivo.write_bytes(gzip.compress(b"antigo"))
        os.utime(arquivo, (1_700_000_000 + n, 1_700_000_000 + n))  # n maior = mais novo
        criadas.append(arquivo)
    return criadas


def test_gera_um_dump_compactado_pelo_compose_de_producao(ambiente: dict[str, str]) -> None:
    resultado = rodar(ambiente)
    assert resultado.returncode == 0, resultado.stderr
    [copia] = copias(ambiente)
    assert gzip.decompress(copia.read_bytes()) == b"CREATE TABLE alerta (id int);"
    chamada = Path(ambiente["DOCKER_REGISTRO"]).read_text(encoding="utf-8")
    assert "compose -f docker-compose.prod.yml exec -T postgres" in chamada
    assert "pg_dump" in chamada


def test_o_nome_leva_a_data_e_a_hora(ambiente: dict[str, str]) -> None:
    rodar(ambiente)
    [copia] = copias(ambiente)
    assert copia.name.startswith("farol-")
    assert len(copia.name) == len("farol-20261030-120000.sql.gz")


def test_guarda_so_as_ultimas_n(ambiente: dict[str, str]) -> None:
    antigas = criar_antigas(ambiente, 5)
    resultado = rodar(ambiente, COPIAS_A_MANTER="3")
    assert resultado.returncode == 0, resultado.stderr
    restantes = {c.name for c in copias(ambiente)}
    assert len(restantes) == 3
    assert antigas[4].name in restantes  # a mais nova das antigas fica
    assert antigas[3].name in restantes
    assert antigas[0].name not in restantes  # as mais velhas saem
    assert antigas[1].name not in restantes
    assert antigas[2].name not in restantes


def test_padrao_e_manter_catorze(ambiente: dict[str, str]) -> None:
    criar_antigas(ambiente, 16)
    rodar(ambiente)
    assert len(copias(ambiente)) == 14


def test_falha_do_dump_nao_apaga_nada_e_nao_deixa_arquivo(ambiente: dict[str, str]) -> None:
    antigas = criar_antigas(ambiente, 3)
    resultado = rodar(ambiente, DOCKER_FALHA="1", COPIAS_A_MANTER="1")
    assert resultado.returncode != 0
    assert set(copias(ambiente)) == set(antigas)
    assert list(Path(ambiente["DESTINO_BACKUP"]).glob(".*parcial")) == []


def test_dump_vazio_e_erro_e_nao_apaga_nada(ambiente: dict[str, str]) -> None:
    antigas = criar_antigas(ambiente, 3)
    resultado = rodar(ambiente, DOCKER_SAIDA="", COPIAS_A_MANTER="1")
    assert resultado.returncode != 0
    assert set(copias(ambiente)) == set(antigas)


@pytest.mark.parametrize("valor", ["0", "abc", "-1", "1.5"])
def test_quantidade_invalida_e_recusada(ambiente: dict[str, str], valor: str) -> None:
    resultado = rodar(ambiente, COPIAS_A_MANTER=valor)
    assert resultado.returncode == 2
    assert copias(ambiente) == []


def test_o_script_nao_tem_senha_escrita() -> None:
    texto = SCRIPT.read_text(encoding="utf-8")
    assert "PGPASSWORD" not in texto
    assert "POSTGRES_PASSWORD" not in texto
