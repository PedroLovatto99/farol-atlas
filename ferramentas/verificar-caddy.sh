#!/usr/bin/env bash
# Sobe o Caddy de produção (deploy/Caddyfile) na frente de uma API de mentira e confere, com
# requisições de verdade, o que o Caddyfile promete:
#   - um X-Forwarded-For forjado pelo visitante NÃO chega à API (só o IP visto pelo Caddy);
#   - os cabeçalhos de segurança saem em toda resposta e o HSTS não leva preload;
#   - um corpo de pedido maior que 1 KB é recusado (413);
#   - a resposta é comprimida para quem aceita.
# Precisa só de Docker e curl; nada é publicado fora de 127.0.0.1. Uso: ferramentas/verificar-caddy.sh
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUFIXO="$$"
REDE="farol-verificar-caddy-${SUFIXO}"
API="farol-verificar-api-${SUFIXO}"
CADDY="farol-verificar-caddy-${SUFIXO}"
PORTA="${PORTA_DA_VERIFICACAO:-18080}"
ESPERA_MAXIMA="${ESPERA_MAXIMA:-90}"  # segundos, por etapa de espera
export MSYS_NO_PATHCONV=1  # Git Bash no Windows: não converter os caminhos dos volumes

limpar() {
  docker rm -f "$API" "$CADDY" >/dev/null 2>&1 || true
  docker network rm "$REDE" >/dev/null 2>&1 || true
}
ARQUIVO="$(mktemp)"
trap 'limpar; rm -f "$ARQUIVO"' EXIT

# O curl do Windows não escreve bem num pipe: a resposta (cabeçalhos e corpo) vai para um arquivo
ARQUIVO_PARA_CURL="$ARQUIVO"
if command -v cygpath >/dev/null 2>&1; then
  ARQUIVO_PARA_CURL="$(cygpath -m "$ARQUIVO")"
fi
buscar() {
  curl -sS -i -o "$ARQUIVO_PARA_CURL" "$@"
  sed "s/$(printf "\r")//" <"$ARQUIVO"
}

falhar() {
  echo "FALHOU: $1" >&2
  docker logs "$CADDY" 2>&1 | tail -20 >&2 || true
  exit 1
}

CAMINHO_DO_CADDYFILE="$RAIZ/deploy/Caddyfile"
if command -v cygpath >/dev/null 2>&1; then
  CAMINHO_DO_CADDYFILE="$(cygpath -m "$CAMINHO_DO_CADDYFILE")"
fi

docker network create "$REDE" >/dev/null

# API de mentira: devolve em JSON os cabeçalhos que recebeu, com um texto longo para comprimir
# (ATRASO_DA_API=N faz a API demorar N s para começar a ouvir: simula o CI lento)
docker run -d --name "$API" --network "$REDE" --network-alias api   -e ATRASO_DA_API="${ATRASO_DA_API:-0}" python:3.13-slim python -c '
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

class Eco(BaseHTTPRequestHandler):
    def _responder(self):
        corpo = json.dumps({"cabecalhos": dict(self.headers), "texto": "farol " * 400}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)
    do_GET = do_POST = _responder
    def log_message(self, *_):
        pass

time.sleep(int(os.environ.get("ATRASO_DA_API", "0")))
HTTPServer(("0.0.0.0", 8000), Eco).serve_forever()
' >/dev/null

# DOMINIO em http:// faz o Caddy servir só HTTP, sem pedir certificado
docker run -d --name "$CADDY" --network "$REDE" -p "127.0.0.1:${PORTA}:80" \
  -e DOMINIO="http://localhost" \
  -v "${CAMINHO_DO_CADDYFILE}:/etc/caddy/Caddyfile:ro" caddy:2 >/dev/null

# Espera até ${ESPERA_MAXIMA}s por uma condição, avisando qual etapa estourou o tempo. No CI as
# imagens precisam ser baixadas e tudo sobe mais devagar que num PC: 90 s por etapa.
esperar() {
  local etapa="$1"
  shift
  local inicio=$SECONDS
  until "$@" >/dev/null 2>&1; do
    if [ $((SECONDS - inicio)) -ge "$ESPERA_MAXIMA" ]; then
      falhar "etapa '${etapa}' não ficou pronta em ${ESPERA_MAXIMA} s"
    fi
    sleep 1
  done
  echo "pronto: ${etapa} ($((SECONDS - inicio)) s)"
}

api_responde() {
  docker exec "$API" python -c     "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/saude', timeout=2)"
}
caddy_encaminha() {
  curl -fsS -H "Host: localhost" "http://127.0.0.1:${PORTA}/api/v1/saude"
}

# 1ª etapa: a API de mentira responde por si só; 2ª: o Caddy já a vê saudável e encaminha
esperar "API de teste respondendo" api_responde
esperar "Caddy encaminhando para a API" caddy_encaminha

# 1. X-Forwarded-For forjado
corpo="$(curl -fsS -H "Host: localhost" -H "X-Forwarded-For: 6.6.6.6, 7.7.7.7" \
  -H "X-Real-IP: 8.8.8.8" "http://127.0.0.1:${PORTA}/api/v1/mapa")"
case "$corpo" in
  *6.6.6.6* | *7.7.7.7*) falhar "o Caddy repassou o X-Forwarded-For forjado: $corpo" ;;
esac
case "$corpo" in
  *8.8.8.8*) falhar "o Caddy repassou o X-Real-IP forjado: $corpo" ;;
esac
encaminhado="$(printf '%s' "$corpo" | python3 -c 'import json,sys; c=json.load(sys.stdin)["cabecalhos"]; print({k.lower():v for k,v in c.items()}.get("x-forwarded-for",""))')"
case "$encaminhado" in
  "" | *,*) falhar "X-Forwarded-For deveria ter um endereço só, veio: '$encaminhado'" ;;
esac
echo "ok: X-Forwarded-For forjado descartado (a API recebe só '$encaminhado')"
# 2. cabeçalhos de segurança
resposta="$(buscar -H "Host: localhost" "http://127.0.0.1:${PORTA}/api/v1/mapa")"
cabecalhos="$(printf '%s\n' "$resposta" | sed '/^$/q')"
for esperado in \
  "strict-transport-security: max-age=31536000" \
  "x-content-type-options: nosniff" \
  "referrer-policy: no-referrer" \
  "content-security-policy: default-src 'none'; frame-ancestors 'none'"; do
  printf '%s\n' "$cabecalhos" | grep -qix "${esperado}" || falhar "faltou o cabeçalho: ${esperado}"
done
if printf '%s\n' "$cabecalhos" | grep -qi "preload"; then
  falhar "o HSTS não deve levar preload"
fi
echo "ok: cabeçalhos de segurança"

# 3. corpo grande demais
codigo="$(head -c 2048 /dev/zero | tr '\0' 'x' | buscar -X POST -H "Host: localhost" \
  --data-binary @- "http://127.0.0.1:${PORTA}/api/v1/mapa" | head -n 1 | cut -d' ' -f2)"
[ "$codigo" = 413 ] || falhar "corpo de 2 KB deveria dar 413, deu '$codigo'"
echo "ok: corpo acima de 1 KB recusado (413)"

# 4. compressão
compactado="$(buscar -H "Host: localhost" -H "Accept-Encoding: gzip" \
  "http://127.0.0.1:${PORTA}/api/v1/mapa" | sed '/^$/q')"
printf '%s\n' "$compactado" | grep -qi '^content-encoding: ' || falhar "a resposta não saiu comprimida"
echo "ok: compressão"

# 5. reinício da API (deploy): o pedido feito com a API fora não leva 503 na hora, o Caddy espera
# (com ATRASO_DA_API a API também demoraria ao reiniciar: esse teste só vale sem o atraso)
if [ "${ATRASO_DA_API:-0}" != 0 ]; then
  echo "pulado: reinício da API (ATRASO_DA_API definido)"
  exit 0
fi
docker stop -t 0 "$API" >/dev/null
( sleep 3 && docker start "$API" >/dev/null ) &
inicio=$SECONDS
codigo="$(curl -sS -m 30 -w '
%{http_code}' -H "Host: localhost"   "http://127.0.0.1:${PORTA}/api/v1/saude" | tail -n 1)"
espera=$((SECONDS - inicio))
wait
[ "$codigo" = 200 ] || falhar "pedido durante o reinício da API deu '$codigo' (esperado 200 após ${espera} s)"
echo "ok: reinício da API (o pedido esperou ${espera} s e voltou 200)"
