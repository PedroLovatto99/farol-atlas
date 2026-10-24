# Quickstart: validar o mapa de alertas de viagem

Guia para subir o sistema e conferir que a feature funciona de ponta a ponta. Detalhes de tabelas e rotas ficam em [data-model.md](data-model.md) e em [contracts/](contracts/); aqui só há comandos e resultados esperados.

## Pré-requisitos

- Docker Desktop com Compose v2 (Windows, macOS ou Linux).
- Para rodar verificações fora do Docker: [uv](https://docs.astral.sh/uv/) (Python 3.13 é instalado por ele) e Node.js LTS.
- Uma chave da API Gemini **ou** o Ollama rodando no host com um modelo local. Sem nenhum dos dois, tudo sobe, mas os alertas novos ficam pendentes (os países citados aparecem como "não verificado").

## 1. Configurar

```powershell
Copy-Item .env.example .env
# editar .env: CONTATO_COLETA (seu contato, vai no User-Agent), GOOGLE_API_KEY (ou OLLAMA_BASE_URL e LLM_CLASSIFICADOR)
```

O `.env` nunca é commitado. O `.env.example` lista todas as variáveis, sem valores reais.

## 2. Subir tudo

```powershell
docker compose up --build
```

Sobem `postgres`, `migracao` (Alembic + seed; termina sozinho), `api`, `worker` e `frontend`.

| Conferência | Esperado |
|---|---|
| `http://localhost:8000/api/v1/saude` | `{"banco":"ok", …}` |
| `http://localhost:8000/docs` | Documentação interativa, **só em desenvolvimento** (`API_DOCS_HABILITADA=true`). Com a variável `false`, responde **404**. |
| `http://localhost:8000/api/v1/openapi.json` | JSON do contrato |
| `http://localhost:5173` | O mapa em globo, tudo "não verificado" (ainda não houve coleta) |
| Porta 5432 | Publicada **só em `127.0.0.1`** (cliente local); nenhuma porta de banco em outro endereço. O banco de teste usa `127.0.0.1:5433`. Se já houver um PostgreSQL local nessas portas, defina `PORTA_POSTGRES` e `PORTA_POSTGRES_TESTE` no `.env` (e a mesma porta em `DATABASE_URL_TESTE`). |

## 3. Rodar uma coleta de desenvolvimento

```powershell
docker compose exec worker python -m farol.worker coletar --alertas
docker compose exec worker python -m farol.worker coletar --postos   # opcional, demora (pausa entre requisições)
```

A coleta respeita o `robots.txt`, pausa entre requisições e para ao cair em verificação humana. O resumo mostra páginas esperadas e lidas, se foi completa e o motivo de qualquer interrupção.

## 4. Roteiro de validação (mapeia para a spec)

| # | Passo | Resultado esperado | Spec |
|---|---|---|---|
| 1 | Abrir o site | Cada país colorido pelo nível; legenda em texto; data da última atualização; aviso de site não oficial com link para o Itamaraty | P1, FR-001 a FR-006 |
| 2 | Antes de qualquer coleta completa | Todos os países "não verificado", nenhum "sem alerta" | FR-002, SC-003 |
| 3 | País que o alerta mais recente marca como normalizado (Bolívia nas fixtures) | "Sem alerta", mesmo com alertas antigos mais graves | FR-007 |
| 4 | Líbano com só "não viaje" marcado na legenda | Líbano aparece por causa do Sul do Líbano | FR-027 |
| 5 | Tocar num país com postos | O mapa se aproxima; painel com bandeira, nível, regiões, alertas com datas e links, postos expansíveis com "Abrir no Google Maps" e, abaixo da lista, a linha "Postos: Itamaraty e Wikipédia (CC BY-SA), conferidos em 21/10/2026" com links | P2 |
| 6 | Tocar na Líbia | Painel orienta procurar o Itamaraty | FR-014 |
| 7 | Tocar no Brasil, Kosovo e nas Malvinas | Painel próprio sem postos; painel da Sérvia e da Argentina com a observação no topo | FR-015, FR-030, FR-034 |
| 8 | Aproximar além do zoom 3.5 | Ícones de embaixada, consulado e escritório; país sem posto com linha tracejada até o responsável | P3 |
| 9 | Expandir um posto no painel | Ícone maior, com contorno, à frente dos outros; só um por vez; recolher ou fechar tira o destaque | FR-018a, FR-018b |
| 10 | Digitar "groenlandia" na busca | Sugere "Groenlândia (Dinamarca)"; ao escolher, o mapa vai até lá e abre o painel | P4 |
| 11 | Desmarcar níveis na legenda | Países esmaecidos (não cinza, não escondidos), ainda tocáveis; mensagem com botão se desmarcar todos | P5 |
| 12 | Janela com 360 px de largura | Todas as funções utilizáveis; painel vira gaveta | FR-042 |
| 13 | Ativar "reduzir movimento" no sistema | Mapa e painel sem animação | FR-039 |
| 14 | Com coletas falhando (ex.: sem internet no worker) por mais de 3 dias (nos testes, com o relógio ajustado) | Continua mostrando o resultado da última coleta completa, com a data; aviso de dados desatualizados | FR-040, FR-041 |

## 5. Verificações (rodam localmente, sem CI)

```powershell
cd backend;  uv run poe verificar    # ruff (lint e formato), mypy, lint-imports, pytest, pip-audit
cd frontend; npm run verificar       # eslint, prettier --check, tsc, vitest, npm audit
```

Os testes de banco precisam do PostgreSQL de teste:

```powershell
docker compose --profile teste up -d postgres-teste
```

Todas as verificações têm de passar sem erros antes de qualquer mudança ser aceita (princípios I e II).

Hook `pre-push` **opcional** (chama os dois comandos acima antes de cada push), ativado por quem quiser:

```powershell
git config core.hooksPath .githooks
``` Os testes não acessam a internet: o gov.br vem de `backend/tests/fixtures/govbr/` e o LLM é um modelo falso.

## 6. Regerar a geometria (só quando as regras de território mudarem)

```powershell
cd backend; uv run python scripts/gerar_geometria.py <natural-earth-preprocessado.geojson> ../dados/postos ../frontend/public/geo/territorios.geojson ../dados/territorios/territorios.json
```

## 7. Modelo local no desenvolvimento (opcional)

Com o Ollama no host, defina `LLM_CLASSIFICADOR=ollama:<modelo>` e `OLLAMA_BASE_URL=http://host.docker.internal:11434` no `.env`.
