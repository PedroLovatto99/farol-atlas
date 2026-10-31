#!/usr/bin/env bash
# Backup do PostgreSQL de produção: pg_dump pelo docker compose, compactado, mantendo só as últimas N.
#
# Uso (na VM, a partir de qualquer pasta):  ferramentas/backup-banco.sh
#
# Variáveis opcionais:
#   DESTINO_BACKUP   pasta das cópias            (padrão: <raiz do repositório>/backups)
#   COPIAS_A_MANTER  quantas cópias guardar      (padrão: 14)
#   ARQUIVO_COMPOSE  arquivo do compose          (padrão: docker-compose.prod.yml)
#
# Agendamento por cron: veja docs/deploy.md. O arquivo gerado é farol-AAAAMMDD-HHMMSS.sql.gz;
# a restauração está descrita no mesmo documento. Sai com erro (e não apaga cópias antigas) se o
# dump falhar ou vier vazio.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINO="${DESTINO_BACKUP:-$RAIZ/backups}"
MANTER="${COPIAS_A_MANTER:-14}"
ARQUIVO_COMPOSE="${ARQUIVO_COMPOSE:-docker-compose.prod.yml}"

case "$MANTER" in
  '' | *[!0-9]* | 0) echo "COPIAS_A_MANTER deve ser um número inteiro maior que zero" >&2; exit 2 ;;
esac

umask 077  # o dump tem todos os dados: só o dono lê
mkdir -p "$DESTINO"
NOME="farol-$(date +%Y%m%d-%H%M%S).sql.gz"
PARCIAL="$DESTINO/.$NOME.parcial"
trap 'rm -f "$PARCIAL"' EXIT

cd "$RAIZ"
# O usuário e o banco vêm do próprio contêiner do postgres; nada de senha neste script
docker compose -f "$ARQUIVO_COMPOSE" exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip -9 >"$PARCIAL"

gzip -t "$PARCIAL"
if [ "$(gzip -dc "$PARCIAL" | wc -c)" -eq 0 ]; then
  echo "o dump veio vazio; nada foi guardado" >&2
  exit 1
fi
mv "$PARCIAL" "$DESTINO/$NOME"

# Guarda as N mais novas (por data de modificação) e apaga o resto
ls -1t "$DESTINO"/farol-*.sql.gz | tail -n +"$((MANTER + 1))" | while IFS= read -r antiga; do
  rm -f -- "$antiga"
done

echo "backup: $DESTINO/$NOME ($(wc -c <"$DESTINO/$NOME") bytes)"
