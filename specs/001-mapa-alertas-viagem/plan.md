# Implementation Plan: Mapa de alertas de viagem para brasileiros

**Branch**: `001-mapa-alertas-viagem` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-mapa-alertas-viagem/spec.md`

## Summary

Um site (frontend React) mostra um globo com o nível de alerta do Itamaraty para cada país e um painel com alertas, postos brasileiros e o posto responsável. Os dados vêm de um backend FastAPI que lê um banco PostgreSQL. Um worker coleta o histórico de alertas do Portal Consular uma vez por dia, usa um LLM só para **classificar** cada alerta novo ou alterado (países, nível, regiões, "situação normalizada") e coleta mensalmente endereço e telefone dos postos. O nível de cada território é calculado no backend pelo alerta mais recente que o cita, entre os da última coleta completa. Nesta feature o LLM serve apenas ao classificador: sem RAG, chat, Chroma nem embeddings.

Detalhes: [research.md](research.md) (conferências, lacunas e decisões), [data-model.md](data-model.md), [contracts/](contracts/) e [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.13 (backend e worker); TypeScript com `strict: true` (frontend)

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2, Alembic, pydantic-settings, APScheduler, requests, BeautifulSoup4, protego, LangChain 1.x (`init_chat_model`; `langchain-google-genai`; `langchain-ollama` em desenvolvimento)
- Frontend: React, Vite, Tailwind CSS 4, MapLibre GL JS 6 (ESM, WebGL2), `@tabler/icons-react`, `flag-icons`, `openapi-typescript`
- Geometria (grupo de desenvolvimento, fora da imagem): shapely, pycountry, mapshaper

**Storage**: PostgreSQL 18 (migrações Alembic); arquivo estático `territorios.geojson` servido pelo frontend

**Testing**: pytest (PostgreSQL de teste separado; fixtures reais do gov.br; modelo falso da LangChain), Vitest + Testing Library (API simulada; mapa substituído por um falso; regras em funções puras)

**Target Platform**: Docker Compose (Windows para desenvolvimento, Linux para produção); imagens multi-arquitetura incluindo arm64. Navegadores com WebGL2.

**Project Type**: web-service + web-application, com um worker agendado na mesma imagem do backend

**Performance Goals**: descobrir o nível de qualquer país em até 10 s (SC-001); `/mapa` em uma chamada com número fixo de consultas, independente do número de países (princípio III)

**Constraints**: 360 px de largura; sem requisição por país no carregamento; dados com no máximo 24 h de atraso quando a coleta funciona (SC-004); aviso de dados desatualizados após 3 dias; operação gratuita (princípio VII)

**Scale/Scope**: 198 países do Itamaraty, cerca de 270 territórios desenháveis, 209 postos, dezenas a poucas centenas de alertas no histórico, uma coleta por dia; público pequeno (site pessoal)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Resultado | Como o plano atende |
|---|---|---|
| I. Qualidade por ferramenta | Passa, com a mitigação decidida | Ruff, mypy, ESLint (`no-explicit-any`) e `strict: true` configurados. Sem CI nesta feature, "nenhuma mudança aceita se falhar" depende de um comando local por lado e de um hook `pre-push` opcional em `.githooks`. Ver Complexity Tracking. |
| II. TDD | Passa | Cada regra de negócio, rota e extrator tem teste antes do código (tarefas ordenadas assim). Gov.br vem de fixtures; LLM é falso; testes de interface verificam comportamento. |
| III. Arquitetura (v1.0.1) | Passa | Camadas e import-linter (`research.md` D1); DTOs Pydantic só na API; tipos gerados do OpenAPI; backend só JSON, com `/docs` e `/redoc` **só em desenvolvimento** por `API_DOCS_HABILITADA` (D2); sem N+1 e testes de limite de consultas; mapa em uma chamada e `GET /paises/{codigo}` só quando o usuário seleciona um país (D8); frontend por funcionalidade; mapa atrás de `MapaProps`. |
| IV. Coleta responsável | Passa | `protego` por host, User-Agent com contato, pausa de 2 s, parada e registro do motivo em verificação humana ou bloqueio (D5). |
| V. Informação confiável | Passa | Sem dado confirmado ⇒ "não verificado" (regra do nível em `data-model.md`); fonte e data em alertas, em endereço/telefone (`contato_coletado_em`, `contato_fonte_url`) **e nos postos do seed** (linha de fonte e data no painel, lida de `fonte_dados`, que também cumpre a atribuição CC BY-SA da Wikipédia, FR-011a); nível só com alertas confirmados por coleta completa; aviso de site não oficial; classificador não segue instruções do texto. |
| VI. Acessível e celular | Passa | Legenda em texto, borda regional com item de legenda, destaque de posto por tamanho e contorno, `prefers-reduced-motion`, 360 px. |
| VII. Simples e gratuito | Passa | Tudo sobe com `docker compose`. Gemini no plano gratuito (cota a confirmar), Ollama local, Oracle Cloud ARM e Vercel gratuitos. Modelo configurável; falha do classificador deixa o alerta pendente sem derrubar o site. (O requisito de o **chat** continuar respondendo com outro provedor pertence à especificação do chat.) |
| VIII. Segurança | Passa | Todas as rotas são GET de leitura; segredos só por variável de ambiente; CORS por variável; bancos com porta publicada só em `127.0.0.1` no desenvolvimento (constituição v1.0.2; teste automatizado do compose; em produção, sem porta publicada); entradas validadas por Pydantic (o `codigo` do caminho tem padrão); textos externos nunca viram HTML sem sanitizar; `pip-audit` e `npm audit` nos comandos de verificação. Limite de perguntas por IP e tempo máximo de resposta são do chat. |
| Idioma | Passa | Interface, documentação, nomes e comentários em português. |

**Re-checagem após o desenho (Fase 1)**: sem violações. A constituição foi emendada para v1.0.1 (dois esclarecimentos no princípio III) e v1.0.2 (portas do banco em desenvolvimento, princípio VIII) a pedido do usuário; esta checagem usa a v1.0.2.

## Project Structure

### Documentation (this feature)

```text
specs/001-mapa-alertas-viagem/
├── plan.md              # Este arquivo
├── research.md          # Fase 0: conferências, lacunas, decisões e riscos
├── data-model.md        # Fase 1: tabelas, estados e regra do nível
├── quickstart.md        # Fase 1: subir, rodar e validar
├── contracts/
│   ├── openapi.yaml             # API v1 (desenho)
│   ├── mapa-props.md            # Interface do componente de mapa
│   ├── geometria-territorios.md # Arquivo de geometria
│   └── classificador-saida.md   # Saída do classificador
├── checklists/requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks; não criado aqui)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml            # uv, ruff, mypy, import-linter, poe (tarefa "verificar")
├── uv.lock
├── Dockerfile
├── .dockerignore
├── alembic.ini
├── alembic/versions/
├── scripts/
│   └── gerar_geometria.py    # derivado de prototipos/mapa/montar_dados.py
├── src/farol/
│   ├── infra/                # configuração (pydantic-settings), banco (engine e sessão), cliente HTTP, relógio, logs
│   ├── dominio/              # modelos ORM, enums, repositórios, seed
│   ├── coleta/               # cliente educado, extratores (alertas, lista, repartições, postos), serviços de coleta
│   ├── classificacao/        # cadeia LangChain, schema de saída, validação, serviço
│   ├── mapa/                 # regra do nível, montagem do mapa e do painel (dataclasses)
│   ├── api/                  # app FastAPI, rotas (controllers), DTOs Pydantic, CORS
│   └── worker/               # APScheduler, jobs, comando de coleta única
└── tests/
    ├── fixtures/govbr/       # páginas reais salvas (já existem; acrescentar subpáginas de postos e página 2 da lista)
    ├── unidade/
    ├── integracao/           # banco de teste
    └── contrato/             # OpenAPI gerado == contracts/openapi.yaml; saída do classificador

frontend/
├── package.json
├── Dockerfile
├── .dockerignore
├── vite.config.ts            # server.watch.usePolling
├── public/geo/territorios.geojson
└── src/
    ├── servicos/api/         # tipos gerados (openapi-typescript) e cliente
    ├── estado/               # useReducer + contexto: seleção, posto expandido, níveis marcados
    ├── funcionalidades/
    │   ├── mapa/             # MapaProps, adaptador MapLibre, funções puras (cor, enquadramento, marcadores)
    │   ├── painel/           # painel do país, postos expansíveis, link do Google Maps
    │   ├── busca/            # campo de busca e sugestões
    │   ├── legenda/          # legenda e filtro por nível, "Sobre as fronteiras deste mapa"
    │   └── aviso/            # data da atualização, dados desatualizados, site não oficial
    ├── compartilhado/        # tokens do tema (cores), ícones, bandeiras, hooks de mídia
    └── testes/               # mapa falso e API simulada

dados/                        # já existe: postos/*.csv e README; acrescentar postos/fonte.yaml, territorios/observacoes.yaml e territorios/territorios.json (gerado)
ferramentas/testar_coleta.py  # já existe; base do módulo coleta
prototipos/mapa/              # já existe; referência de visual e comportamento
docker-compose.yml            # postgres, migracao, api, worker, frontend (+ postgres-teste no perfil "teste")
.env.example                  # inclui API_DOCS_HABILITADA=true (só desenvolvimento)
.gitattributes                # * text=auto eol=lf
.gitignore                    # já existe; completar
.githooks/pre-push            # opcional: chama as verificações; ativar com: git config core.hooksPath .githooks
```

**Structure Decision**: aplicação web com `backend/` (monolito modular por domínio, API e worker na mesma imagem) e `frontend/` (por funcionalidade). Os módulos `coleta`, `classificacao` e `mapa` são independentes entre si; `api` e `worker` ficam no topo; `dominio` guarda modelos e repositórios; `infra` é a base (`research.md` D1). O que será reaproveitado:

| Arquivo existente | Uso |
|---|---|
| `dados/postos/*.csv` | Seed de postos, de países sem posto e dos 198 países |
| `ferramentas/testar_coleta.py` | Seletores e funções de download/extração viram o módulo `coleta` |
| `prototipos/mapa/template_globo.html` | Referência de visual e comportamento (cores, painel, marcadores, enquadramento) |
| `prototipos/mapa/montar_dados.py` | Base de `gerar_geometria.py`, com os ajustes de Malvinas e Taiwan |
| `backend/tests/fixtures/govbr/` | Fixtures dos testes de coleta e do classificador |

## Ordem de entrega sugerida (insumo para /speckit-tasks)

1. Esqueleto: repositório (`.gitignore`, `.gitattributes`, `.env.example`), Docker, compose, backend e frontend vazios com as verificações passando.
2. Dados e domínio: modelos, migrações, seed (198 países, postos, responsáveis), geometria. Entrega o P1 com tudo "não verificado".
3. Coleta de alertas e classificador, com testes sobre as fixtures. A lista é completa se não houver link de próxima página (R2).
4. Regra do nível e `GET /mapa`: o P1 passa a mostrar níveis reais.
5. `GET /paises/{codigo}` e painel (P2).
6. Postos no mapa e destaque (P3), busca (P4), filtro (P5).
7. **Última fase:** coleta mensal de postos, medindo a cobertura (R1). É melhor esforço e não bloqueia as histórias P1 a P5, que funcionam com o fallback para a cidade.

## Complexity Tracking

> Preencher apenas onde a Constitution Check tem violação ou interpretação que precisa de decisão do usuário.

| Item | Por que ocorre | Alternativa mais simples rejeitada porque |
|---|---|---|
| **Sem CI nesta feature** (princípios I e VIII: "nenhuma mudança é aceita se falhar", "dependências conferidas a cada mudança") | Decisão do pedido: a integração contínua entra depois. | Colocar CI agora foge do escopo pedido. Mitigação decidida: um comando por lado (`uv run poe verificar`, `npm run verificar`) e um hook `pre-push` opcional em `.githooks`, ativado com `git config core.hooksPath .githooks`. Não substitui a CI. |
| **Header + itens na classificação** (o pedido descreve "alerta × país") | Alertas que não são de viagem e classificações que falharam não têm país; um registro por classificação (`classificacao`) mais um item por território (`nivel_territorio`) resolve isso. | Uma tabela só obrigaria linhas com país nulo. Não é violação de princípio, só mudança de forma do pedido. |
