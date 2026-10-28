# Quickstart: validar os vistos

Roteiro para conferir a feature de ponta a ponta. Detalhes de tabelas, rotas e comandos ficam em [data-model.md](data-model.md) e em [contracts/](contracts/); aqui só há comandos e resultados esperados. O que já vale da 001 (subir o Docker, `.env`, o banco de teste) está em [../001-mapa-alertas-viagem/quickstart.md](../001-mapa-alertas-viagem/quickstart.md).

## Pré-requisitos

- A stack da 001 de pé (`docker compose up --build`) e `CONTATO_COLETA` com o seu contato de verdade no `.env`. Para a Wikipédia, o contato recomendado é o link do repositório: `CONTATO_COLETA=https://github.com/PedroLovatto99/farol-atlas`.
- Para traduzir as observações: `GOOGLE_API_KEY` (ou `LLM_TRADUTOR=ollama:<modelo>` com o Ollama no host). **Novo:** `LLM_TRADUTOR` (formato "provedor:modelo", padrão o mesmo do classificador). Sem nenhum dos dois, a coleta funciona e as observações aparecem em inglês, avisando que não foram traduzidas.
- O banco de teste (`docker compose --profile teste up -d postgres-teste`) para os testes de integração.

## 1. Aplicar a migração

```powershell
docker compose run --rm migracao        # alembic upgrade head (inclui a 0003_vistos) e o seed
```

Esperado: as tabelas `coleta_vistos`, `requisito_visto`, `mudanca_retida` e `item_para_revisao` existem, vazias.

## 2. Antes de qualquer coleta de vistos

| Conferência | Esperado |
|---|---|
| `GET http://localhost:8000/api/v1/vistos` | `dados_obtidos: false`; todo território `sem_informacao`; o Brasil `nao_se_aplica` |
| `GET /api/v1/paises/AR` | `visto.situacao = "sem_informacao"` (e `visto` **nulo só em** `/paises/BR`) |
| Site, modo "Alertas" (padrão) | Igual à 001 |
| Site, modo "Vistos" | Globo todo cinza, Brasil em neutro claro, legenda com a linha "Vistos: ainda não há dados de visto" |

## 3. A primeira coleta

```powershell
docker compose exec worker python -m farol.worker coletar --vistos
```

Esperado: "Coleta de vistos VÁLIDA", cerca de 226 países reconhecidos, nomes e rótulos não reconhecidos: **0** (SC-010), e o código de saída 0 (`$LASTEXITCODE`). Se a última edição do artigo for de menos de 24 horas, a rodada é **adiada** (código de saída 1, com o motivo): repita no dia seguinte.

Depois conferir a cobertura (SC-001), que fica registrada no relatório da execução:

```powershell
docker compose exec postgres psql -U farol -d farol -c "select categoria, count(*) from requisito_visto group by 1 order by 2 desc"
```

## 4. Roteiro de validação (mapeia para a spec)

| # | Passo | Resultado esperado | Spec |
|---|---|---|---|
| 1 | Tocar na Argentina | Painel com a seção "Visto" abaixo do alerta: "Isento de visto", "Entrada com o RG", observações com a tradução e o original, link do artigo (CC BY-SA), data do dado e o aviso de fonte não oficial | P1, FR-001 a FR-009 |
| 2 | Tocar nos Estados Unidos | "Visto exigido"; sem campo de permanência | FR-002, FR-004 |
| 3 | Tocar na Tailândia, em Omã e na Austrália | Cada uma na categoria do `research.md` 3.1; Omã mostra o rótulo combinado "Visa not required / eVisa" e a categoria mais exigente; a Austrália ("Online visa required") aparece como **Visto exigido** | FR-007 |
| 4 | Tocar na Jamaica | Permanência "Varia conforme o motivo (ver observações)" e a nota "Varia conforme o motivo da viagem" | FR-007a |
| 5 | Tocar em Hong Kong, em Guernsey e em Kosovo | Hong Kong: entrada própria. Guernsey: a do Reino Unido, com a nota de herança. Kosovo: painel da Sérvia, com o visto da Sérvia | FR-013 |
| 6 | Tocar no Brasil | Sem seção de visto | FR-014 |
| 7 | Tocar na Etiópia ("up to 90 days") | Permanência em inglês, "não traduzido" | FR-004a |
| 8 | Tocar num país com observações, depois de uma coleta sem tradutor (derrube o tradutor) | Observação em inglês, avisando; categoria e prazo intactos | FR-005 |
| 9 | Alternar para "Vistos" | Cores de visto, legenda de visto, sem bordas regionais, linha "Vistos: Wikipédia (CC BY-SA), fonte não oficial, coletados em …" | P2, FR-021 a FR-025, FR-029 |
| 10 | Recarregar a página depois de escolher "Vistos" | Volta a "Alertas" (o modo não é lembrado) | FR-021 |
| 11 | No celular (360 px), com a legenda recolhida, em "Vistos" | A linha de fonte e data continua visível, sem cobrir o mapa, o aviso nem o "Sobre" | FR-029 |
| 12 | Legenda de vistos: desmarcar "Isento, entrada com RG" | Só os países de RG esmaecem; "Isento de visto" mostra o estado misto (texto "parcial") | FR-022a |
| 13 | Tocar num país nos dois modos | O mesmo painel | FR-026 |
| 14 | Ver o Brasil em "Vistos" | Cor neutra claramente diferente do cinza de "sem informação"; a legenda o explica | FR-023 |
| 15 | Parar a API (`docker compose stop api`), abrir o site em "Alertas" e escolher "Vistos" | Legenda com "Não foi possível carregar os vistos." e "Tentar de novo"; **nenhum país em cinza** (sem preenchimento) | O10 |
| 16 | Subir a API (`docker compose start api`) e tocar em "Tentar de novo" | Os vistos carregam e o globo é pintado | O10 |

## 5. Simular uma mudança retida (retenção por país)

O banco de desenvolvimento já tem os dados da primeira coleta. Faça o site "lembrar" de um valor mais exigente e deixe a próxima coleta trazer o valor real:

```powershell
docker compose exec postgres psql -U farol -d farol -c "update requisito_visto set categoria='visto_exigido', hash_fonte=repeat('0',64) where territorio_codigo='AR'"
docker compose exec worker python -m farol.worker coletar --vistos
docker compose exec worker python -m farol.worker vistos pendentes
```

Esperado: a Argentina aparece em "Mudanças retidas" (Visto exigido → Isento de visto) e o painel dela **continua** em "Visto exigido", com a data antiga. Depois:

```powershell
docker compose exec worker python -m farol.worker vistos confirmar AR     # o painel passa a "Isento de visto"
```

Para ver a rejeição, repita o `update` e rode `vistos rejeitar AR`: uma nova coleta com o mesmo valor da fonte **não** reabre a retenção.

## 6. Verificações (rodam localmente e no CI, sem segredos)

```powershell
cd backend;  uv run poe verificar      # ruff, mypy, lint-imports (8 contratos), pytest, pip-audit
cd frontend; npm run verificar         # eslint, prettier, tsc, vitest, npm audit
```

Os testes de integração precisam do PostgreSQL de teste (seção de pré-requisitos). Nenhum teste acessa a internet nem um LLM de verdade: o tradutor é um falso e a Wikipédia vem de `backend/tests/fixtures/wikipedia/`. Regerar os tipos do frontend depois de mudar o contrato: `cd frontend; npm run gerar-tipos`.

## 7. Atualizar a fixture (só quando o formato do artigo mudar)

Siga o `README.md` da pasta da fixture: uma requisição à página (nunca à API), atualizar a tabela de data, revisão e SHA-256, e rodar os testes. Se um teste do dicionário falhar por rótulo novo, o rótulo entra no `rotulos.yaml` **com o seu teste**, depois da sua aprovação.
