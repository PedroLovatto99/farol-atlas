# Quickstart: como validar o chat (feature 003)

**Spec**: [spec.md](spec.md) | **Plano**: [plan.md](plan.md) | **Contratos**: [contracts/](contracts/) | **Dados**: [data-model.md](data-model.md)

Este guia é a **validação de ponta a ponta**: do que precisa estar de pé até o resultado esperado em cada cenário. Nenhum passo aqui exige colocar chave no repositório: as chaves vêm do `.env` (que o `.gitignore` ignora). Comandos a partir da raiz do repositório, salvo indicação.

## 0. Antes de escrever código (conferências)

| Conferência | Como | Esperado |
|---|---|---|
| Docker Desktop de pé | `docker version` | servidor responde |
| Base do `postgres:18` atual | `docker run --rm postgres:18 cat /etc/os-release` | `VERSION_CODENAME=trixie` (já confirmado no registro oficial e pelo banco local, que reporta `Debian 18.6-1.pgdg13+2`; confirmar na máquina) |
| Imagem do pgvector: mesma base e arm64 | `docker run --rm pgvector/pgvector:0.8.7-pg18-trixie cat /etc/os-release` e `docker buildx imagetools inspect pgvector/pgvector:0.8.7-pg18-trixie` | `trixie`; lista `linux/amd64` e `linux/arm64` (confirmado no Docker Hub: a tag existe com os dois) |
| O `create_agent` aceita modelo com fallback | teste de 15 minutos (primeira tarefa) | decide entre `with_fallbacks` e `ModelFallbackMiddleware` (research D2) |
| Cota real do projeto do chat | AI Studio → limites do projeto de `GOOGLE_API_KEY_CHAT` | pior dia: 2.000 chamadas ao modelo + 500 de embedding cabem? Se não, baixar `CHAT_LIMITE_POR_DIA` |

### 0.1 Conferir a ordenação (collation) do volume existente, **antes** e **depois** de trocar a imagem

A troca só é segura se a ordenação de texto do volume não mudar (mesma glibc). Com a base igual (`trixie`) não deve mudar; este passo prova. Rode no banco de desenvolvimento com a imagem **antiga** e repita com a **nova**:

```bash
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT datname, datcollate, datcollversion, pg_database_collation_actual_version(oid) AS versao_atual FROM pg_database ORDER BY 1"'
```

Esperado: `datcollversion` igual a `versao_atual` em todas as linhas, antes e depois, e nenhum `WARNING: ... collation version mismatch` em `docker compose logs postgres`.

**Se houver diferença** (ou o aviso), faça, nesta ordem, **depois de um backup** (`ferramentas/backup-banco.sh` na produção; `pg_dump` à mão no desenvolvimento):

```sql
-- conectado ao banco do projeto (use psql -d "$POSTGRES_DB")
REINDEX DATABASE CONCURRENTLY farol;              -- reconstrói os índices que dependem de ordenação de texto
ALTER DATABASE farol REFRESH COLLATION VERSION;   -- só depois do REINDEX, grava a versão nova
```

Repita para os bancos `postgres` e `template1` só se aparecerem na consulta com diferença (não guardam dado do projeto). Num servidor novo (produção ainda sem volume), nada disso é necessário. Em um servidor que **já tem** dados, o `docs/deploy.md` manda fazer o backup e rodar este passo ao trocar a imagem.

## 1. Banco com pgvector

```bash
docker compose --profile teste up -d postgres postgres-teste        # já com a imagem pgvector/pgvector:0.8.7-pg18-trixie
docker compose run --rm migracao                                    # alembic upgrade head (0005_chat)
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dx vector" -c "\d trecho_alerta" -c "\d contagem_chat"'
```

Esperado: extensão `vector` instalada; as duas tabelas existem; as tabelas da 001 e da 002 intactas (o teste de migrações confere). O volume do banco de desenvolvimento é reaproveitado (mesmo major 18, mesma base de Debian, conferência do 0.1 feita).

## 2. Verificações automáticas (as mesmas do CI, sem rede e sem modelo real)

```bash
cd backend
uv run poe verificar        # lint, formato, tipos, arquitetura (import-linter com o chat), testes (inclui o gabarito determinístico) e auditoria
cd ../frontend
npm run verificar           # lint, formato, tipos (com os tipos gerados da v1.2), testes e auditoria
```

Esperado: tudo verde. Dentro do `poe verificar`:
- *arquitetura*: `farol.chat` na camada de `mapa | coleta | classificacao | vistos`, sem importar nenhum deles;
- *testes de contrato*: o OpenAPI gerado equivale a [contracts/openapi.yaml](contracts/openapi.yaml), e a parte da 002 não mudou;
- *gabarito* (`tests/gabarito/chat/`): recuperação ≥ 90%, ferramenta certa, trava, recusas, injeção, histórico adulterado, citações idênticas ao texto do alerta, contagens sem texto.

Regenerar os tipos do frontend depois de mudar o contrato: `cd frontend && npm run gerar-tipos` (o script passa a ler o contrato da 003).

## 3. Indexar os alertas (worker)

```bash
docker compose up -d --build api worker
docker compose exec worker python -m farol.worker indexar --status   # antes: alertas elegíveis × indexados
docker compose exec worker python -m farol.worker indexar            # vetoriza (precisa de GOOGLE_API_KEY_CHAT ou GOOGLE_API_KEY)
docker compose exec worker python -m farol.worker indexar --status   # depois: tudo em dia
```

Esperado: com os 18 alertas do banco local, algumas dezenas a poucas centenas de trechos; segunda passada de `indexar` não vetoriza nada (idempotente). Com `COLETAS_AUTOMATICAS=false` o worker continua ocioso e a indexação é só manual, como acima.

**Trocar o modelo de embeddings** (por exemplo, para outro modelo ou outra dimensão): mude `EMBEDDINGS_MODELO` e/ou `EMBEDDINGS_DIMENSOES` no `.env`, reinicie `api` e `worker` e rode:

```bash
docker compose exec worker python -m farol.worker indexar --status      # avisa: "o índice só tem vetores de <modelo antigo>; rode reindexar"
docker compose exec worker python -m farol.worker reindexar             # refaz tudo no modelo novo e só então apaga os vetores antigos
docker compose exec worker python -m farol.worker indexar --status      # em dia
```

Esperado: durante a troca o chat continua respondendo (os alertas ainda sem vetores do modelo novo entram pela busca textual) e **nunca** compara vetores de modelos ou dimensões diferentes; depois do `reindexar`, `trecho_alerta` só tem linhas do modelo novo (ou das duas, com `--manter-antigos`).

## 4. Perguntar pela linha de comando (SSE)

Com a API de pé (`http://localhost:8000`), o `.env` com `CORS_ORIGENS` do frontend e a chave do chat:

```bash
curl -N -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"pergunta":"O que fazer se eu já estou no Irã?","historico":[]}'
```

Esperado: eventos `progresso` (`identificando_pais`, `buscando_nos_alertas`, `montando_resposta`) e, no fim, **um** `resposta` com `situacao: "resposta"`, `citacoes` de alerta (título, data, `url` do gov.br, `vigor` e `trecho` idêntico ao texto do alerta) e `avisos`. Variações para conferir os contratos:

| Pergunta | Esperado |
|---|---|
| "Qual o nível de alerta da Rússia?" | cartão `nivel`, citação do alerta que rege; se "sem alerta", aviso de que isso não é recomendação; nunca "seguro" |
| "Preciso de visto para o Japão?" | cartão `visto` (mesmos dados de `GET /paises/JP`), citação Wikipédia (CC BY-SA, fonte não oficial) e o aviso de conferir com o consulado |
| "Qual o telefone do consulado em Lisboa?" | cartão `postos`; o que faltar aparece como "não consta" |
| histórico "nível da Rússia" + "E para a Argentina?" | país da pergunta atual (AR); o histórico não vira fonte |
| "Quero uma receita de pão" | `situacao: "recusa"`, explicação do que o chat responde |
| "É seguro ir para a Tailândia?" | sem opinião própria: cartão de nível e o que o alerta diz |
| "Preciso de visto para o Congo?" | `pergunta_de_volta` (ambíguo), sem chamar o modelo |
| "Quais países têm alerta de não viajar?" | cartão `lista` (`assunto: nivel`) com **os mesmos países** do filtro "Não viaje" da legenda do mapa, o total, a fonte (Itamaraty) e a data; sem país detectado, **sem** pergunta de volta |
| "Quais países estão sem alerta?" | cartão `lista` com a ressalva de que ausência de alerta não é recomendação; nunca "seguros" |
| "Para onde posso ir só com o RG?" | cartão `lista` (`assunto: visto`, "Isento, entrada com RG") igual ao modo Vistos; Wikipédia (CC BY-SA, não oficial), data e o aviso de conferir com o consulado; **sem as Malvinas** |
| "Quais países são seguros?" ou "Países sem alerta e sem visto?" | `situacao: "recusa"`, explicando que lista por um critério de cada vez e não escolhe destinos, com a oferta das listas separadas |
| `{"pergunta":"x"*501,"historico":[]}` | `422`; não conta nos limites |

Conferir também com a chave do chat **ausente** ou inválida: o chat entra em contingência (cartões do painel e aviso) ou avisa que está fora do ar; `GET /mapa` segue normal (SC-008).

## 5. Limites

Para testar sem fazer 500 perguntas, suba a API com limites baixos no `.env`: `CHAT_LIMITE_POR_HORA_POR_IP=3` e `CHAT_LIMITE_POR_DIA=5`.

| Passo | Esperado |
|---|---|
| 4 perguntas seguidas do mesmo IP | a 4ª: `429`, `codigo: limite_por_hora`, `Retry-After`, `espera_segundos`; a pergunta não chega ao modelo |
| 5 perguntas no dia (de IPs diferentes ou limite por IP alto) e uma 6ª | `429`, `codigo: limite_do_dia`, `volta_em` = 00:00 de Brasília do dia seguinte |
| Derrubar o serviço de linguagem (chave inválida) e perguntar 3 vezes | `erro` `servico_indisponivel` (ou contingência); depois, a mesma pessoa **ainda tem** suas vagas (não contam) |
| Reiniciar a API e consultar `contagem_chat` | o contador do dia **sobreviveu**; a janela por IP recomeçou (por desenho) |
| Perguntar e então `GET /mapa` duas vezes | o contador de versão dos dados **não mudou** com a pergunta (o cache de leitura continua valendo) |

## 6. Interface

```bash
cd frontend && npm run dev     # ou docker compose up (frontend em http://localhost:5173)
```

| Cenário | Esperado |
|---|---|
| Abrir o chat nos modos Alertas e Vistos | abre nos dois; o modo, o filtro e o país selecionado não mudam |
| Desktop com um país aberto, abrir o chat | o painel do país vira a barra compacta (estado inalterado); fechar o chat devolve o painel como estava |
| Celular (360 px) | o chat é uma gaveta; legenda, linha de fonte e aviso voltam ao fechar; sem rolagem horizontal |
| Teclado | abrir pelo botão, foco no campo, enviar, "Ver trecho" abre/fecha, `Esc` fecha, foco volta ao botão |
| Leitor de tela | progresso anunciado; resposta nova anunciada; limite e erro como alerta |
| Movimento reduzido (`prefers-reduced-motion`) | sem animações |
| Recarregar a página | a conversa some; nada em `localStorage`/`sessionStorage` |
| Responder passando de 20 s | aviso e "Tentar de novo"; a pergunta não conta |

## 7. Produção, no PC (Caddy na frente)

```bash
bash ferramentas/verificar-caddy.sh                  # inclui as checagens do /chat: 10 KB passa, 20 KB dá 413, sem compressão, eventos sem retenção
```

E o teste de fumaça do compose de produção, num projeto à parte (`-p farol-prod-teste`, como em `docs/deploy.md`): `POST` em `https://localhost/api/v1/chat` com o modelo desligado (sem chave), pelo Caddy; ver os eventos chegando em ordem e o `429` depois do limite. `down -v` só nesse `-p`.

## 8. Avaliação com o modelo real (fora do CI)

```bash
cd backend
uv run poe avaliar-chat     # 60 perguntas contra GOOGLE_API_KEY_CHAT / LLM_CHAT, com os alertas de teste indexados
```

Esperado: relatório por tipo; recuperação ≥ 90% nas perguntas de conteúdo; **zero** violações das regras de linguagem (sem alerta ≠ seguro; sem informação ≠ isento; Malvinas sem RG); 100% de recusa nas fora do escopo; contagem de quantas vezes a trava e o verificador agiram. Rodar a cada mudança de prompt, de modelo ou de fatiamento.

## 9. Privacidade e recursos

- Depois de uma bateria de perguntas, `SELECT * FROM contagem_chat` mostra só contagens; `docker compose logs api worker` e o arquivo `worker.log` **não** contêm o texto de nenhuma pergunta ou resposta, nem IP ligado a conteúdo (SC-011). Há um teste que faz essa busca.
- Rastreamento externo desligado (`LANGSMITH_TRACING=false`); o teste de segurança falha se estiver ligado.
- Memória: `docker stats` na VM (ou no teste de fumaça) com o chat em uso; comparar com a estimativa de ~0,7 a 1 GB no total e registrar o número real em `docs/deploy.md`. Cinco perguntas simultâneas respondem em até 20 s sem deixar o site nem as coletas lentos (SC-013).
