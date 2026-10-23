---

description: "Lista de tarefas da feature Mapa de alertas de viagem para brasileiros"
---

# Tasks: Mapa de alertas de viagem para brasileiros

**Input**: documentos de design em `specs/001-mapa-alertas-viagem/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Testes**: OBRIGATÓRIOS (constituição, princípio II - TDD). Toda regra de negócio, rota da API e extração de dados começa por um teste que falha. Testes não acessam a internet: o gov.br vem de `backend/tests/fixtures/govbr/` e o LLM é um modelo falso. Em cada fase, escreva os testes primeiro e confirme que falham antes de implementar.

**Organização**: tarefas agrupadas por história de usuário (P1 a P5 da spec), para implementar e testar cada uma de forma independente. A coleta mensal de postos é a **última fase** e não bloqueia P1 a P5.

**Fora desta lista (só se o usuário pedir)**: README do projeto e integração contínua (GitHub Actions). Commits também só quando o usuário pedir.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: história da spec (US1 = P1 ... US5 = P5)
- Caminhos relativos à raiz do repositório; módulos do backend em `backend/src/farol/`

## Convenções que valem para todas as tarefas

- Código Python com type hints; `mypy` e `ruff` sem erros. TypeScript com `strict: true` e sem `any` (use `unknown` e valide).
- Nomes, comentários e textos da interface em português.
- Módulos do backend só importam a interface pública de módulos das camadas abaixo (`import-linter`). Rotas não acessam o banco; repositórios (em `dominio`) são os únicos que fazem SQL.
- Listas carregam relacionamentos de uma vez (sem N+1).
- Textos externos (alertas, respostas do LLM) são dados: nunca viram HTML sem sanitizar.
- **Kosovo (`XK`) e Malvinas (`FK`) são um caso especial do mecanismo de dependências**: `tipo = dependencia`, nível pela regra das dependências, mas com `identidade_do_soberano`. Usam o nome, a bandeira e o painel do país soberano (Sérvia e Argentina), **nunca uma bandeira própria**, com a observação no topo do painel. A busca encontra "Kosovo" e "Malvinas" e abre o painel do soberano. Detalhes em `data-model.md` (seção "Kosovo e Malvinas").


---

## Phase 1: Setup (Infraestrutura compartilhada)

**Objetivo**: estrutura do repositório, ferramentas de qualidade, Docker e ambiente.

- [ ] T001 [P] Completar `.gitignore` na raiz (`.env`, `*.log`, `.DS_Store`, `Thumbs.db`, `desktop.ini`, `.idea/`, `node_modules/`, `dist/`, `coverage/`, `venv/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `amostras_coleta/`, `resultado_coleta.json`; manter `env/`) e criar `.gitattributes` com `* text=auto eol=lf`
- [ ] T002 [P] Criar `.env.example` na raiz com todas as variáveis documentadas e sem valores reais: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `DATABASE_URL_TESTE`, `CORS_ORIGENS`, `API_DOCS_HABILITADA=true` (só desenvolvimento), `CONTATO_COLETA`, `PAUSA_SEGUNDOS=2`, `LIMITE_HORAS_PARTIDA=20`, `LLM_CLASSIFICADOR=google_genai:gemini-3.6-flash`, `GOOGLE_API_KEY`, `OLLAMA_BASE_URL=http://host.docker.internal:11434`, `VITE_API_URL`
- [ ] T003 Criar o projeto Python em `backend/pyproject.toml` com `uv` (Python 3.13): dependências de execução (FastAPI, uvicorn, SQLAlchemy 2, Alembic, psycopg, pydantic-settings, APScheduler, requests, beautifulsoup4, protego, langchain, langchain-google-genai, langchain-ollama), grupo `dev` (pytest, ruff, mypy, import-linter, pip-audit, poethepoet) e grupo `geo` (shapely, pycountry); configurar ruff (lint e formato), mypy estrito e pytest; gerar `backend/uv.lock`; criar os pacotes vazios `backend/src/farol/{infra,dominio,coleta,classificacao,mapa,api,worker}/__init__.py`
- [ ] T004 Declarar em `backend/pyproject.toml` os contratos do import-linter: `layers` (`api | worker` acima de `mapa | coleta | classificacao`, acima de `dominio`, acima de `infra`) e `independence` entre `mapa`, `coleta` e `classificacao`; criar a tarefa `poe verificar` (ruff check, ruff format --check, mypy, lint-imports, pytest, pip-audit)
- [ ] T005 [P] Criar o projeto em `frontend/` com Vite, React e TypeScript (`strict: true`), Tailwind CSS 4, Vitest + Testing Library, ESLint com typescript-eslint (regra `no-explicit-any` como erro) e Prettier; scripts `dev`, `build`, `gerar-tipos` e `verificar` (eslint, prettier --check, tsc, vitest, npm audit) em `frontend/package.json`; `server.watch.usePolling: true` em `frontend/vite.config.ts`
- [ ] T006 [P] Criar `backend/Dockerfile` (imagem única para API e worker, base `python:3.13-slim`, `uv sync --frozen --no-dev`, funciona em amd64 e arm64) e `backend/.dockerignore` (`.venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`)
- [ ] T007 [P] Criar `frontend/Dockerfile` (servidor de desenvolvimento do Vite, base `node` LTS) e `frontend/.dockerignore` (`node_modules`, `dist`, `coverage`)
- [ ] T008 Criar `docker-compose.yml` na raiz com os serviços `postgres` (PostgreSQL 18, **sem porta publicada**, volume de dados), `migracao` (roda `alembic upgrade head` e o seed, depois termina), `api` (uvicorn `--reload`, `WATCHFILES_FORCE_POLLING=true`, porta 8000), `worker` (mesma imagem, comando do worker), `frontend` (porta 5173) e `postgres-teste` no perfil `teste` (porta só em `127.0.0.1`, dados em tmpfs); `api` e `worker` dependem de `migracao` concluída com sucesso; `extra_hosts: host.docker.internal:host-gateway`
- [ ] T009 [P] Criar o hook opcional `.githooks/pre-push` que roda `uv run poe verificar` (em `backend/`) e `npm run verificar` (em `frontend/`) e bloqueia o push se falharem; documentar a ativação (`git config core.hooksPath .githooks`) no `specs/001-mapa-alertas-viagem/quickstart.md` (não criar README)
- [ ] T010 Conferir que `uv run poe verificar` (backend) e `npm run verificar` (frontend) passam no esqueleto vazio e que `docker compose config` valida o `docker-compose.yml`

---

## Phase 2: Foundational (Pré-requisitos bloqueantes)

**Objetivo**: configuração, banco, modelos, migrações, seed dos 198 países e dos postos, geometria, esqueleto da API e base do frontend.

**⚠️ CRÍTICO**: nenhuma história começa antes desta fase terminar.


### Backend: infraestrutura e domínio

- [ ] T011 [P] Teste da configuração em `backend/tests/unidade/infra/test_config.py` (variáveis obrigatórias, `CORS_ORIGENS` em lista, `API_DOCS_HABILITADA` padrão `false`, segredos nunca no `repr`)
- [ ] T012 Implementar a configuração com pydantic-settings em `backend/src/farol/infra/config.py`
- [ ] T013 [P] Implementar `backend/src/farol/infra/banco.py` (engine e sessão SQLAlchemy a partir de `DATABASE_URL`, único ponto de configuração do banco), `backend/src/farol/infra/relogio.py` (relógio injetável) e `backend/src/farol/infra/logs.py` (log estruturado)
- [ ] T014 Criar `backend/tests/conftest.py`: sessão no PostgreSQL de teste (`DATABASE_URL_TESTE`) com migrações aplicadas e rollback por teste, relógio falso e contador de consultas SQL para os testes de limite
- [ ] T015 [P] Teste dos modelos e restrições em `backend/tests/integracao/dominio/test_modelos.py`: CHECK de `soberano_codigo` obrigatório para dependência, CHECK de endereço/telefone exigirem `contato_coletado_em` e `contato_fonte_url`, UNIQUE de `alerta.url`, UNIQUE `(alerta_id, alerta_hash)`, PK de `nivel_territorio`
- [ ] T016 [P] Criar os enums (`TipoTerritorio`, `TipoPosto`, `Nivel` do alerta, `StatusClassificacao`, `TipoExecucao`) em `backend/src/farol/dominio/enums.py`
- [ ] T017 Criar os modelos ORM `territorio`, `posto`, `alerta`, `classificacao`, `nivel_territorio` e `execucao_coleta` em `backend/src/farol/dominio/modelos.py`, conforme `data-model.md` (inclui `icone_latitude/longitude`, `pagina_lida`, `contato_*`)
- [ ] T018 Configurar o Alembic (`backend/alembic.ini`, `backend/alembic/env.py`) e criar a migração inicial em `backend/alembic/versions/` com todas as tabelas, enums e restrições
- [ ] T019 [P] Testes dos repositórios em `backend/tests/integracao/dominio/test_repositorios.py`: leituras de lista carregam relacionamentos de uma vez (contagem de consultas fixa, independente do número de linhas); última execução completa; alertas ativos com classificação vigente
- [ ] T020 Implementar os repositórios (único lugar com SQL) em `backend/src/farol/dominio/repositorios/` (`territorios.py`, `postos.py`, `alertas.py`, `classificacoes.py`, `execucoes.py`) e exportá-los pela interface pública de `backend/src/farol/dominio/__init__.py`

### Geometria e seed

- [ ] T021 [P] Testes da geometria em `backend/tests/unidade/geometria/test_gerar_geometria.py`, conforme `contracts/geometria-territorios.md`: os 198 países do Itamaraty têm feição `pais`; nenhum código fora do seed; `soberano` existe e é país; `FK` (Malvinas) não é neutro, é dependência de `AR` e usa o grupo `zoom` de `AR`; `XK` é dependência de `RS` e usa o grupo `zoom` de `RS`; `EH` e `AQ` são neutros; Taiwan é dependência da China sem bandeira; Guiana Francesa (`GF`) separada da França; ilhas que dividem o código do país viram dependência
- [ ] T022 Criar `backend/scripts/gerar_geometria.py` a partir de `prototipos/mapa/montar_dados.py`, aplicando as regras da spec (Malvinas fora de `NEUTRO`, Taiwan como dependência, Kosovo e Malvinas como dependências com o `zoom` do soberano) e removendo os alertas de exemplo; documentar no cabeçalho do script o pré-processamento do Natural Earth `ne_10m_admin_0_countries_bra` com mapshaper (precisão 0.0005, campos `nome`, `iso`, `soberano`); gerar `frontend/public/geo/territorios.geojson` (propriedades `codigo`, `soberano`, `tipo`, `titulo`, `zoom`) e `dados/territorios/territorios.json` (dependências, soberano, ponto do ícone dos países sem posto)
- [ ] T023 Baixar o Natural Earth, executar o pré-processamento e o script (`uv run --group geo`), conferir os testes T021 e versionar os dois arquivos gerados; atualizar `specs/001-mapa-alertas-viagem/contracts/geometria-territorios.md` com o segundo arquivo de saída
- [ ] T024 [P] Criar `dados/territorios/observacoes.yaml` com as observações curtas da spec: Kosovo (o Brasil não reconhece a independência), Malvinas (administradas pelo Reino Unido; o Brasil apoia os direitos argentinos e defende a negociação), Taiwan, Saara Ocidental, Antártida e dependências, mais, para Kosovo e Malvinas, `identidade_do_soberano`, `rotulo_busca` ("Kosovo (Sérvia)", "Malvinas (Argentina)") e `termos_busca` (`Kosovo`; `Malvinas`, `Ilhas Malvinas`)
- [ ] T025 Teste do seed em `backend/tests/integracao/dominio/test_seed.py`: exatamente 198 países com `na_lista_itamaraty`; 209 postos; 60 países com posto responsável resolvido (alias `Cambera→Camberra`); Líbia com `sem_posto_indicado`; Brasil presente; `XK` e `FK` são dependências de `RS` e `AR` com `identidade_do_soberano`, `nome_pt` do soberano ("Sérvia", "Argentina"), `codigo_bandeira` `RS` e `AR` (nunca `XK` nem `FK`), `rotulo_busca` e `termos_busca` conforme `data-model.md`; as demais dependências têm `identidade_do_soberano` falso e bandeira própria, e Taiwan tem `codigo_bandeira` nulo; execução repetida não duplica; código do CSV ausente em `territorio` falha de forma ruidosa
- [ ] T026 Implementar o seed idempotente em `backend/src/farol/dominio/seed.py` (CSVs de `dados/postos/`, `dados/territorios/territorios.json` e `observacoes.yaml`) e a chamada `python -m farol.dominio.seed`; ligar ao serviço `migracao` do `docker-compose.yml`

### Backend: esqueleto da API

- [ ] T027 [P] Testes do esqueleto em `backend/tests/integracao/api/test_app.py`: CORS aceita só as origens de `CORS_ORIGENS`; `/docs` e `/redoc` respondem 404 com `API_DOCS_HABILITADA=false` e 200 com `true`; `/api/v1/openapi.json` sempre disponível; `GET /api/v1/saude` devolve 200 com banco ok e 503 com banco indisponível; erros sempre em JSON
- [ ] T028 Implementar a fábrica do app em `backend/src/farol/api/app.py` (CORS por variável, docs condicionais, prefixo `/api/v1`, tratamento de erros em JSON), DTOs base (`Erro`, `Saude`) em `backend/src/farol/api/dtos.py` e a rota `backend/src/farol/api/rotas/saude.py` (estado do banco, última coleta completa e tentativa, alertas pendentes)
- [ ] T029 Criar `backend/src/farol/api/exportar_openapi.py` (grava o OpenAPI do app em arquivo) e a tarefa `poe exportar-openapi`

### Frontend: base

- [ ] T030 [P] Teste dos níveis em `frontend/src/compartilhado/niveis.test.ts`: rótulo, texto explicativo e gravidade de `sem_alerta`, `evitar`, `nao_viajar`, `nao_verificado`; padrão `nao_verificado`
- [ ] T031 Criar `frontend/src/compartilhado/niveis.ts` (rótulos e textos de nível, incluindo a frase de que ausência de alerta não significa recomendação de viagem) e `frontend/src/compartilhado/tema.css` com os tokens Tailwind de cor: sem alerta `#C0DD97`, evitar `#FAC775`, não viajar `#E24B4A`, não verificado `#D3D1C7`, neutro e Brasil `#F1EFE8`, borda regional `#A32D2D` (não viaje) e `#854F0B` (evite), linha até o posto responsável `#0C447C`, oceano `#DCE8F2`
- [ ] T032 Gerar os tipos da API com `openapi-typescript` em `frontend/src/servicos/api/esquema.d.ts` (script `gerar-tipos` aceita o caminho do OpenAPI; usar `specs/001-mapa-alertas-viagem/contracts/openapi.yaml` até o backend exportar o seu)
- [ ] T033 [P] Teste do cliente da API em `frontend/src/servicos/api/cliente.test.ts`: chamadas tipadas, erro HTTP vira erro tratado, resposta inválida não passa (valida em vez de usar `any`)
- [ ] T034 Implementar `frontend/src/servicos/api/cliente.ts` (`obterMapa`, `obterPais`, `obterSaude`, base `VITE_API_URL`)
- [ ] T035 [P] Criar os dublês de teste em `frontend/src/testes/`: `mapa-falso.tsx` (implementa `MapaProps`, expõe eventos de toque), `api-simulada.ts` (respostas de `/mapa` e `/paises/{codigo}`) e `dados-exemplo.ts`; configurar o setup do Vitest
- [ ] T036 [P] Teste do estado em `frontend/src/estado/reducer.test.ts`: selecionar território, limpar seleção, estado inicial com todos os níveis marcados
- [ ] T037 Implementar `frontend/src/estado/reducer.ts` (`useReducer`: território selecionado, postos expandidos, níveis marcados) e `frontend/src/estado/contexto.tsx`; sem biblioteca de estado global
- [ ] T038 [P] Criar os hooks `frontend/src/compartilhado/useMovimentoReduzido.ts` e `frontend/src/compartilhado/useTelaPequena.ts` (com testes ao lado) para `prefers-reduced-motion` e telas de até 700 px

**Checkpoint**: banco migrado e populado, geometria gerada, `/api/v1/saude` respondendo, frontend com tipos gerados e dublês de teste prontos.

---

## Phase 3: User Story 1 - Ver a situação do mundo no mapa (Priority: P1) 🎯 MVP

**Objetivo**: mapa-múndi com a cor do nível de cada país, destaque de região, legenda em texto, data da última atualização e aviso de site não oficial. Inclui a coleta dos alertas, o classificador, a regra do nível e `GET /mapa`.

**Teste independente**: com o banco de teste populado por alertas das fixtures, abrir o site e verificar cores, legenda, destaque regional, data, aviso e que país sem dado confirmado nunca aparece como "sem alerta" (`quickstart.md`, passos 1 a 4).


### Testes do backend (escrever primeiro e ver falhar)

- [ ] T039 [P] [US1] Teste do cliente educado em `backend/tests/unidade/coleta/test_cliente_educado.py`: respeita o `robots.txt` por host, User-Agent com `CONTATO_COLETA`, pausa configurável entre requisições, detecta verificação humana e HTTP 403/429, nunca insiste depois do bloqueio (base: funções de `ferramentas/testar_coleta.py`)
- [ ] T040 [P] [US1] Teste dos extratores em `backend/tests/unidade/coleta/test_extratores_alertas.py` com as fixtures: `lista_alertas.html` (18 itens, sem link de próxima página = lista completa), `alerta_1.html` a `alerta_3.html` (título, categoria, `datePublished`, `dateModified` do JSON-LD; `alerta_2` modificado em 2026-08-17; reserva "Publicado em"); caso sintético com link de próxima página que falha = lista incompleta
- [ ] T041 [P] [US1] Teste do serviço de coleta em `backend/tests/integracao/coleta/test_servico_alertas.py`: hash SHA-256 de título+texto com espaços normalizados; só novo ou alterado segue para classificação; remoção só em coleta completa; limites de 69% e 70% das páginas; link de próxima página que falha deixa a coleta incompleta; verificação humana interrompe e grava o motivo; execução registrada (início, fim, esperadas, lidas, completa, motivo); alerta com página não lida fica `pagina_lida=false`; alerta que volta à lista limpa `removido_em`
- [ ] T042 [P] [US1] Teste do schema do classificador em `backend/tests/unidade/classificacao/test_esquema.py`, conforme `contracts/classificador-saida.md`: código fora do conjunto permitido invalida a resposta inteira; território repetido invalida; `e_alerta_de_viagem=false` exige lista vazia; `true` exige ao menos um território; níveis fora do enum falham
- [ ] T043 [P] [US1] Teste do serviço de classificação em `backend/tests/integracao/classificacao/test_servico_classificacao.py` com `GenericFakeChatModel`: `alerta_1` (Bolívia) → `normalizada`; `alerta_2` (Oriente Médio) → vários territórios, `LB` com "Sul do Líbano" e `PS` com "Faixa de Gaza"; `alerta_3` (fraudes) → não é alerta de viagem; resposta com `ZZ` → falhou e alerta pendente; texto com "ignore as instruções" não altera o schema; só reclassifica quando o hash muda; grava modelo e erro
- [ ] T044 [P] [US1] Teste da regra do nível em `backend/tests/unidade/mapa/test_nivel.py`, conforme a regra de `data-model.md`: nunca houve coleta completa → todos `nao_verificado`; ninguém cita o país → `sem_alerta`; vale o alerta mais recente mesmo que um antigo fosse mais grave; `normalizada` → `sem_alerta` sem regiões; só regional → `sem_alerta` com região; data = `coalesce(modificado_em, publicado_em)`; empate → nível mais grave; dependência segue o mais recente entre o próprio alerta e o do soberano (março normalizada × maio "não viaje" e a ordem inversa); alerta pendente com país no título → `nao_verificado`; alerta pendente sem país no título não muda nada; alerta conhecido com página não lida mantém o nível
- [ ] T045 [P] [US1] Teste do serviço do mapa em `backend/tests/integracao/mapa/test_servico_mapa.py`: `dados_obtidos`, `atualizado_em`, `desatualizado` (mais de 3 dias, calculado no backend), territórios com nível e regiões em destaque (FR-004) (inclui `XK` e `FK` com `identidade_do_soberano`, `bandeira` do soberano, `rotulo_busca` e `termos_busca`), postos com `grupo` por coordenada (embaixada e consulado na mesma cidade dividem o grupo), países sem posto com ponto do ícone e posto responsável (Líbia sem responsável)
- [ ] T046 [P] [US1] Teste da rota em `backend/tests/integracao/api/test_rota_mapa.py`: `GET /api/v1/mapa` devolve o DTO do contrato; número de consultas ao banco limitado e **igual** com 5 ou com 200 territórios (sem N+1); nenhum objeto ORM na resposta; todos os 198 países presentes
- [ ] T047 [P] [US1] Teste do agendador em `backend/tests/unidade/worker/test_agenda.py`: cron diário às 06:17 em `America/Sao_Paulo`; na partida roda se a última tentativa tiver mais de 20 horas; comando `coletar --alertas` roda uma vez; o worker encadeia coleta → classificação
- [ ] T048 [P] [US1] Teste de contrato em `backend/tests/contrato/test_openapi_mapa.py`: o caminho e os esquemas de `/mapa` no OpenAPI gerado equivalem a `specs/001-mapa-alertas-viagem/contracts/openapi.yaml`

### Implementação do backend

- [ ] T049 [US1] Implementar `backend/src/farol/coleta/cliente_educado.py` (sessão `requests`, protego por host, User-Agent, pausa, detecção de verificação humana e bloqueio, parada com motivo)
- [ ] T050 [P] [US1] Implementar os extratores `backend/src/farol/coleta/extratores/lista_alertas.py` (itens, link de próxima página) e `backend/src/farol/coleta/extratores/alerta.py` (JSON-LD primeiro, "Publicado em" como reserva), reaproveitando os seletores de `ferramentas/testar_coleta.py`
- [ ] T051 [US1] Implementar `backend/src/farol/coleta/servico_alertas.py`: percorre a lista (seguindo próxima página), abre todos os alertas com pausa, calcula hash, grava novo/alterado, marca removidos só em coleta completa e registra a execução (critério FR-040)
- [ ] T052 [P] [US1] Implementar o schema e a validação em `backend/src/farol/classificacao/esquema.py`
- [ ] T053 [US1] Implementar a cadeia em `backend/src/farol/classificacao/cadeia.py`: `init_chat_model(LLM_CLASSIFICADOR, temperature=0)`, `with_structured_output`, prompt em português com o texto do alerta entre delimitadores e sem ferramentas
- [ ] T054 [US1] Implementar `backend/src/farol/classificacao/servico.py`: classifica alertas novos ou alterados, valida os códigos contra `territorio`, grava `classificacao` e `nivel_territorio`, deixa pendente em caso de falha
- [ ] T055 [US1] Implementar a regra do nível em `backend/src/farol/mapa/nivel.py` (função pura sobre linhas já carregadas)
- [ ] T056 [US1] Implementar `backend/src/farol/mapa/visoes.py` (dataclasses imutáveis) e `backend/src/farol/mapa/servico.py` (monta a visão do mapa com número fixo de consultas)
- [ ] T057 [US1] Implementar os DTOs `Mapa`, `TerritorioNoMapa` (com `bandeira`, `identidade_do_soberano`, `rotulo_busca`, `termos_busca`), `PostoNoMapa`, `PaisSemPosto`, `Regiao` em `backend/src/farol/api/dtos.py` e a rota `backend/src/farol/api/rotas/mapa.py` (só converte e devolve)
- [ ] T058 [US1] Implementar o worker em `backend/src/farol/worker/agenda.py` (APScheduler, 06:17 `America/Sao_Paulo`, partida condicional), `backend/src/farol/worker/jobs.py` (coleta → classificação) e `backend/src/farol/worker/__main__.py` (`coletar --alertas`); ligar ao serviço `worker` do `docker-compose.yml`
- [ ] T059 [US1] Regenerar `frontend/src/servicos/api/esquema.d.ts` a partir do OpenAPI exportado pelo backend e conferir que bate com o contrato

### Testes do frontend (escrever primeiro e ver falhar)

- [ ] T060 [P] [US1] Teste das funções de cor em `frontend/src/funcionalidades/mapa/cor.test.ts`: nível → cor, borda regional (`nao_viaje` vs `evite`), território neutro, padrão `nao_verificado`
- [ ] T061 [P] [US1] Testes dos hooks `frontend/src/funcionalidades/mapa/useMapa.test.ts` e `useGeometria.test.ts`: uma única chamada a `/mapa`, carregamento, erro, geometria carregada uma vez
- [ ] T062 [P] [US1] Teste da legenda em `frontend/src/funcionalidades/legenda/Legenda.test.tsx`: os quatro níveis em texto (não só cor), item "Região mais grave", texto de que "sem alerta" não é recomendação de viagem
- [ ] T063 [P] [US1] Teste do aviso em `frontend/src/funcionalidades/aviso/Aviso.test.tsx`: data da última atualização, aviso de site não oficial com link para o portal do Itamaraty, aviso de dados desatualizados quando `desatualizado`, mensagem de dados ainda não obtidos quando `dados_obtidos` é falso
- [ ] T064 [P] [US1] Testes de `SobreFronteiras` e `Sobre` em `frontend/src/funcionalidades/legenda/SobreFronteiras.test.tsx` e `frontend/src/funcionalidades/sobre/Sobre.test.tsx`: explicação com Kosovo, Taiwan, Malvinas, Saara Ocidental, Antártida e dependências; atribuição das fontes (Natural Earth, Wikipédia CC BY-SA, Itamaraty)
- [ ] T065 [US1] Teste de integração da tela em `frontend/src/App.test.tsx` (API simulada e mapa falso): o mapa recebe os territórios com níveis do `/mapa`; com `dados_obtidos=false` nenhum território é `sem_alerta`; país com região de alerta mais grave recebe `bordaRegional`

### Implementação do frontend

- [ ] T066 [P] [US1] Definir a interface em `frontend/src/funcionalidades/mapa/tipos.ts` (`MapaProps`, `TerritorioDesenhado`, `PostoDesenhado`, `PaisSemPostoDesenhado`, `PedidoDeCamera`), exatamente como em `contracts/mapa-props.md`
- [ ] T067 [P] [US1] Implementar `frontend/src/funcionalidades/mapa/cor.ts` (cor por nível e borda regional)
- [ ] T068 [US1] Implementar `frontend/src/funcionalidades/mapa/useMapa.ts` e `frontend/src/funcionalidades/mapa/useGeometria.ts`
- [ ] T069 [US1] Implementar o adaptador `frontend/src/funcionalidades/mapa/adaptador-maplibre.tsx` (MapLibre GL JS 6, import ESM, globo 3D, só oceano e países, camadas de preenchimento, fronteiras e borda regional); único arquivo que importa `maplibre-gl`; revalidar a API de globo do protótipo `prototipos/mapa/template_globo.html`
- [ ] T070 [P] [US1] Implementar `frontend/src/funcionalidades/legenda/Legenda.tsx` (amostra de cor + texto de cada nível e "Região mais grave") e `frontend/src/funcionalidades/legenda/SobreFronteiras.tsx` (link ao lado da legenda e explicação curta)
- [ ] T071 [P] [US1] Implementar `frontend/src/funcionalidades/aviso/Aviso.tsx` e `frontend/src/funcionalidades/sobre/Sobre.tsx`
- [ ] T072 [US1] Montar `frontend/src/App.tsx` e `frontend/src/main.tsx` (mapa, legenda, aviso, link "Sobre"), layout responsivo funcionando em 360 px de largura, sem a seção "Notícias" do protótipo
- [ ] T073 [US1] Validação manual: com chave do Gemini ou Ollama, rodar `docker compose exec worker python -m farol.worker coletar --alertas` e conferir no navegador os passos 1 a 4 de `quickstart.md`

**Checkpoint**: P1 funcional e testável sozinha. Parar e validar antes de seguir.

---

## Phase 4: User Story 2 - Ver os detalhes de um país e onde buscar ajuda (Priority: P2)

**Objetivo**: ao tocar num país, o mapa se aproxima e abre o painel com bandeira, nome, nível, regiões, alertas com datas e links, postos expansíveis com Google Maps, posto responsável, Líbia e Brasil.

**Teste independente**: tocar num país com alerta e postos, num país sem posto (Iêmen), na Líbia, no Brasil, em Kosovo e nas Malvinas, e conferir o conteúdo do painel (`quickstart.md`, passos 5 a 7).


### Testes do backend (escrever primeiro e ver falhar)

- [ ] T074 [P] [US2] Teste do serviço do painel em `backend/tests/integracao/mapa/test_servico_painel.py`: lista todos os alertas que citam o território (e o soberano, se dependência) do mais recente ao mais antigo, com `define_nivel`, `situacao_normalizada` e `pendente`; `regiao_unica_do_alerta`; `XK` e `FK` devolvem o painel do soberano (nome "Sérvia"/"Argentina", `bandeira` `RS`/`AR`, `identidade_do_soberano`, alertas e postos do soberano) com a observação no topo, nunca com bandeira própria; Brasil sem postos; país sem posto devolve `posto_responsavel`; Líbia com `sem_posto_indicado`; área neutra e código desconhecido levantam "não encontrado"
- [ ] T075 [P] [US2] Teste da rota em `backend/tests/integracao/api/test_rota_paises.py`: 200 com o DTO do contrato; 404 para neutro/desconhecido; 422 para código mal formado; número de consultas limitado e fixo; postos com `contato_coletado_em` e `contato_fonte_url` quando houver endereço ou telefone
- [ ] T076 [P] [US2] Teste de contrato em `backend/tests/contrato/test_openapi_paises.py`: `/paises/{codigo}` e os esquemas `Pais`, `AlertaDoPais`, `PostoNoPainel` equivalem ao `contracts/openapi.yaml`

### Implementação do backend

- [ ] T077 [US2] Implementar `backend/src/farol/mapa/painel.py` (visão do painel, reaproveitando `nivel.py`) e exportá-la pela interface pública de `backend/src/farol/mapa/__init__.py`
- [ ] T078 [US2] Implementar os DTOs `Pais`, `AlertaDoPais`, `PostoNoPainel` em `backend/src/farol/api/dtos.py` e a rota `backend/src/farol/api/rotas/paises.py`
- [ ] T079 [US2] Regenerar `frontend/src/servicos/api/esquema.d.ts` com a rota de países

### Testes do frontend (escrever primeiro e ver falhar)

- [ ] T080 [P] [US2] Teste do link do Google Maps em `frontend/src/funcionalidades/painel/googleMaps.test.ts`: com endereço usa o endereço; sem endereço usa "tipo do Brasil, cidade, país" (leva à cidade); a URL é codificada
- [ ] T081 [P] [US2] Teste do enquadramento em `frontend/src/funcionalidades/mapa/enquadramento.test.ts`: usa a maior parte do território (Rússia e França não mostram o mundo); inclui o posto responsável só se a largura ficar abaixo de 180° de longitude; zoom máximo 5.5
- [ ] T082 [P] [US2] Testes do painel em `frontend/src/funcionalidades/painel/Painel.test.tsx` e `Posto.test.tsx`: bandeira (Taiwan sem bandeira; Kosovo e Malvinas mostram o nome e a bandeira da Sérvia e da Argentina, nunca uma própria) e nome; nível e texto; regiões; aviso de alerta só regional; lista de alertas com data e link (o que define o nível marcado); postos com tipo e cidade, expansíveis para endereço, telefone de plantão, fonte e data da coleta; "endereço ainda não cadastrado"; link "Abrir no Google Maps"; posto responsável; Líbia orienta procurar o Itamaraty; Brasil sem postos; observação com link "Sobre as fronteiras deste mapa"; observação no topo para Kosovo e Malvinas
- [ ] T083 [US2] Teste do fluxo em `frontend/src/App.test.tsx` (acrescentar): tocar num território faz **uma** chamada a `/paises/{codigo}` e abre o painel; tocar em Kosovo ou nas Malvinas chama `/paises/XK` ou `/paises/FK` e abre o painel da Sérvia ou da Argentina com a observação no topo; área neutra e oceano não abrem painel; Esc e "Ver mundo" fecham e voltam a câmera ao mundo; com movimento reduzido a câmera pede `duration` zero

### Implementação do frontend

- [ ] T084 [P] [US2] Implementar `frontend/src/funcionalidades/painel/googleMaps.ts`
- [ ] T085 [P] [US2] Implementar `frontend/src/funcionalidades/mapa/enquadramento.ts` (função pura `calcularEnquadramento`)
- [ ] T086 [US2] Implementar `frontend/src/funcionalidades/painel/usePais.ts` (uma chamada por seleção, com cancelamento)
- [ ] T087 [P] [US2] Criar `frontend/src/compartilhado/Bandeira.tsx` com `flag-icons` (só os SVGs exibidos; nunca emoji de bandeira); recebe o código já resolvido pelo backend (`bandeira`), não exibe nada se for nulo (Taiwan) e nunca monta bandeira a partir de `XK` ou `FK`
- [ ] T088 [US2] Implementar `frontend/src/funcionalidades/painel/Painel.tsx`, `AlertasDoPais.tsx` e `Posto.tsx` (expansível por `details`/botão acessível, texto inserido como texto, nunca HTML) e as ações de seleção em `frontend/src/estado/reducer.ts`
- [ ] T089 [US2] Estender `frontend/src/funcionalidades/mapa/adaptador-maplibre.tsx`: contorno de seleção (para Kosovo e Malvinas, o contorno e a câmera usam o grupo `zoom` do soberano), toque em país, ignorar áreas neutras e oceano, pedidos de câmera `mundo` e `enquadrar` (duração zero se `reduzirMovimento`)
- [ ] T090 [US2] Integrar o painel em `frontend/src/App.tsx`: painel lateral no computador e gaveta no celular, botão "Ver mundo", tecla Esc, margens de câmera conforme o layout

**Checkpoint**: P1 e P2 funcionam juntas; P2 pode ser testada sozinha com a API simulada.

---

## Phase 5: User Story 3 - Ver os postos no mapa (Priority: P3)

**Objetivo**: ícones de postos a partir do zoom 3.5, ícone de país sem posto ligado ao responsável, destaque do posto expandido no painel e toque no ícone abrindo o painel.

**Teste independente**: aproximar o mapa e conferir ícones por tipo; expandir e recolher postos; tocar em ícones (`quickstart.md`, passos 8 e 9).


### Testes do frontend (escrever primeiro e ver falhar)

- [ ] T091 [P] [US3] Teste das funções de marcadores em `frontend/src/funcionalidades/mapa/marcadores.test.ts`: ícones só a partir do zoom 3.5; país selecionado, seu posto responsável e o grupo em destaque aparecem em qualquer zoom; ícone do outro lado do globo não aparece; ícone compartilhado por dois postos mostra o selo "+1"
- [ ] T092 [P] [US3] Teste de `garantir-visivel` em `frontend/src/funcionalidades/mapa/camera.test.ts`: move só se o ponto está fora da área visível e nunca altera o zoom; `manter` não reenquadra
- [ ] T093 [P] [US3] Teste do estado em `frontend/src/estado/reducer.test.ts` (acrescentar): expandir posto define o grupo em destaque; só um ícone em destaque por vez; recolher ou fechar o painel remove o destaque; tocar num ícone seleciona o país do posto com o(s) posto(s) expandido(s); tocar num ícone compartilhado expande os dois postos; tocar em ícone de outro país troca o painel sem reenquadrar
- [ ] T094 [US3] Teste de componentes em `frontend/src/funcionalidades/mapa/Marcador.test.tsx` e `Posto.test.tsx`: ícone de embaixada, consulado e escritório; país sem posto com `map-pin-share`; destaque = maior **e** com contorno (não só cor); `reduzirMovimento` desliga a animação do destaque; expandir um posto no painel dispara o destaque

### Implementação do frontend

- [ ] T095 [P] [US3] Implementar `frontend/src/funcionalidades/mapa/marcadores.ts` (agrupamento por `grupo`, regra de visibilidade, zoom 3.5)
- [ ] T096 [P] [US3] Implementar a regra `garantir-visivel`/`manter` em `frontend/src/funcionalidades/mapa/camera.ts`
- [ ] T097 [P] [US3] Criar `frontend/src/compartilhado/icones-posto.tsx` com `@tabler/icons-react` (`building-bank`, `building`, `briefcase`, `map-pin-share`)
- [ ] T098 [US3] Estender `frontend/src/estado/reducer.ts` com `postosExpandidos`, `grupoEmDestaque` e as ações de expandir, recolher e tocar num ícone
- [ ] T099 [US3] Estender `frontend/src/funcionalidades/mapa/adaptador-maplibre.tsx`: marcadores do MapLibre com os ícones renderizados por portal do React (`opacityWhenCovered`), linha tracejada `#0C447C` até o posto responsável, destaque (maior, com contorno, `z-index` à frente), `onSelecionarGrupo`
- [ ] T100 [US3] Ligar em `frontend/src/App.tsx` e `frontend/src/funcionalidades/painel/Posto.tsx`: expandir/recolher postos no painel controla o destaque; tocar num ícone abre o painel do país com o posto expandido, sem reenquadrar o mapa

**Checkpoint**: P1 a P3 funcionam juntas.

---

## Phase 6: User Story 4 - Buscar um país pelo nome (Priority: P4)

**Objetivo**: campo de busca com sugestões sem diferença de acento e de maiúsculas, incluindo territórios e dependências, que leva o mapa ao país e abre o painel.

**Teste independente**: digitar "mexi", "GRO", "groenlandia" e "vaticano" e escolher a sugestão (`quickstart.md`, passo 10).

- [ ] T101 [P] [US4] Teste da busca em `frontend/src/funcionalidades/busca/busca.test.ts`: sem acento e sem diferença de maiúsculas; "mexi" encontra México; "kosovo", "malvinas" e "ilhas malvinas" encontram `XK` e `FK` pelos `termos_busca`, com os rótulos "Kosovo (Sérvia)" e "Malvinas (Argentina)"; "gro" e "groenlandia" encontram "Groenlândia (Dinamarca)"; encontra Vaticano e Mônaco; busca vazia e sem resultado
- [ ] T102 [P] [US4] Teste do componente em `frontend/src/funcionalidades/busca/Busca.test.tsx`: sugestões enquanto digita (papel `combobox`, navegação por teclado); escolher um resultado seleciona o território e pede câmera; escolher Kosovo ou Malvinas abre o painel do soberano (título "Sérvia"/"Argentina", bandeira do soberano, observação no topo) e pede a câmera do soberano; sem resultado mostra mensagem e **não** move o mapa; países esmaecidos continuam encontráveis
- [ ] T103 [US4] Implementar `frontend/src/funcionalidades/busca/busca.ts` (normalização NFKD, índice a partir dos territórios de `/mapa`, casando `nome`, `rotulo_busca` e `termos_busca`)
- [ ] T104 [US4] Implementar `frontend/src/funcionalidades/busca/Busca.tsx` e integrá-lo em `frontend/src/App.tsx`, abrindo o painel como no toque

**Checkpoint**: P1 a P4 funcionam juntas.

---

## Phase 7: User Story 5 - Filtrar o mapa por nível (Priority: P5)

**Objetivo**: a legenda vira filtro com uma caixa de marcar por nível; níveis desmarcados esmaecem os países (sem esconder e sem pintar de cinza); região mais grave mantém o país visível; mensagem com botão quando tudo está desmarcado.

**Teste independente**: desmarcar e marcar níveis, desmarcar todos, e conferir o Líbano com só "não viaje" marcado (`quickstart.md`, passos 4 e 11).

- [ ] T105 [P] [US5] Teste das funções de filtro em `frontend/src/funcionalidades/legenda/filtro.test.ts`: território esmaecido quando seu nível está desmarcado; **não** esmaecido quando o nível de uma região de alerta está marcado (Líbano com só "não viaje"); neutros nunca esmaecem; nenhum nível marcado
- [ ] T106 [P] [US5] Teste do componente em `frontend/src/funcionalidades/legenda/Legenda.test.tsx` (acrescentar): caixas de marcar, todas marcadas ao abrir; desmarcar esmaece e marcar devolve a cor; tocar num país esmaecido abre o painel; com tudo desmarcado aparece a mensagem e o botão que marca todos
- [ ] T107 [US5] Implementar `frontend/src/funcionalidades/legenda/filtro.ts` e as ações de níveis marcados em `frontend/src/estado/reducer.ts`
- [ ] T108 [US5] Transformar `frontend/src/funcionalidades/legenda/Legenda.tsx` em filtro (caixas acessíveis com rótulo em texto) e mostrar a mensagem de "nenhum nível marcado" com o botão em `frontend/src/App.tsx`
- [ ] T109 [US5] Estender `frontend/src/funcionalidades/mapa/adaptador-maplibre.tsx` para aplicar `esmaecido` (opacidade reduzida mantendo a cor e a interação)

**Checkpoint**: P1 a P5 funcionam juntas.

---

## Phase 8: Coleta mensal de postos (melhor esforço; última fase, serve à US2)

**Objetivo**: preencher endereço e telefone de plantão dos postos a partir do gov.br, com fallback para a cidade. **Não bloqueia P1 a P5** (o painel já mostra a cidade e o link do Google Maps sem esses dados).

**Teste independente**: rodar a coleta de postos sobre as fixtures e conferir os campos preenchidos, os nulos e o relatório de cobertura.

- [ ] T110 [US2] Salvar como fixtures, com `ferramentas/testar_coleta.py` (educado, com pausa), as subpáginas de contato de 2 a 3 postos (uma embaixada e consulados, por exemplo `/emergencias` e `/fale-conosco-1` de Milão) em `backend/tests/fixtures/govbr/` e anotar no `LEIA-ME.md` da pasta como foram obtidas
- [ ] T111 [P] [US2] Teste dos extratores em `backend/tests/unidade/coleta/test_extratores_postos.py`: tabela de repartições (`reparticoes.html`: 198 linhas de dados, país → posto de atendimento, link do posto); endereço e telefone de plantão das subpáginas salvas; página sem esses dados devolve nulo, sem erro
- [ ] T112 [P] [US2] Teste do serviço em `backend/tests/integracao/coleta/test_servico_postos.py`: segue links do posto e redirecionamentos, registra `url_gov_br`; `robots.txt` consultado por host; grava `endereco`, `telefone_plantao`, `contato_coletado_em` e `contato_fonte_url` juntos; campos não encontrados ficam nulos; bloqueio ou verificação humana interrompe e grava o motivo; relatório `postos_com_endereco` e `postos_com_telefone`
- [ ] T113 [P] [US2] Teste do agendamento mensal em `backend/tests/unidade/worker/test_agenda.py` (acrescentar) e do comando `coletar --postos`
- [ ] T114 [P] [US2] Implementar `backend/src/farol/coleta/extratores/reparticoes.py` e `backend/src/farol/coleta/extratores/posto.py` (melhor esforço, seletores definidos a partir das fixtures)
- [ ] T115 [US2] Implementar `backend/src/farol/coleta/servico_postos.py` (mesmas regras de coleta responsável) e a gravação do contato via repositório de postos
- [ ] T116 [US2] Agendar a coleta mensal em `backend/src/farol/worker/agenda.py` e acrescentar `coletar --postos` em `backend/src/farol/worker/__main__.py`
- [ ] T117 [US2] Rodar a coleta de postos de verdade uma vez, registrar a cobertura (quantos dos 209 postos têm endereço e telefone) em `specs/001-mapa-alertas-viagem/research.md` (item R1) e informar o usuário

**Checkpoint**: contato dos postos coletado quando disponível; cobertura medida e relatada.

---

## Phase 9: Polish e verificações transversais

**Objetivo**: contrato completo, segurança, acessibilidade, desempenho e validação final.

- [ ] T118 [P] Teste de contrato completo em `backend/tests/contrato/test_openapi_completo.py`: o OpenAPI gerado equivale por inteiro a `specs/001-mapa-alertas-viagem/contracts/openapi.yaml`
- [ ] T119 [P] Testes de segurança em `backend/tests/integracao/api/test_seguranca.py`: só rotas GET; CORS rejeita origem não listada; nenhum segredo em respostas, logs ou OpenAPI; texto de alerta com HTML sai como texto no JSON
- [ ] T120 [P] Teste em `frontend/src/funcionalidades/painel/seguranca.test.tsx`: títulos e textos de alertas com marcação HTML são exibidos como texto e nunca inseridos como HTML
- [ ] T121 [P] Revisão de acessibilidade em 360 px com teclado e leitor de tela: cor nunca é a única informação, foco visível, rótulos das caixas da legenda, `prefers-reduced-motion` em todo movimento; registrar achados e correções em `specs/001-mapa-alertas-viagem/checklists/`
- [ ] T122 [P] Construir as imagens para arm64 (`docker buildx build --platform linux/arm64` em `backend/` e `frontend/`) e confirmar que sobem
- [ ] T123 [P] Rodar `pip-audit` e `npm audit`, corrigir ou justificar cada achado
- [ ] T124 Medir SC-001 (nível de qualquer país em até 10 s, por toque e por busca) e o tempo de carga do `/mapa`; ajustar o que passar do esperado
- [ ] T125 Percorrer o roteiro completo de `specs/001-mapa-alertas-viagem/quickstart.md` (passos 1 a 14) e corrigir divergências entre o roteiro e o sistema
- [ ] T126 Revisar código duplicado e restos do protótipo (seção "Notícias", alertas de exemplo) e rodar `uv run poe verificar` e `npm run verificar` até passarem sem erros

---

## Dependencies & Execution Order

### Dependências entre fases

- **Setup (Fase 1)**: sem dependências.
- **Foundational (Fase 2)**: depende da Fase 1 e **bloqueia** todas as histórias.
- **US1 (Fase 3)**: depende da Fase 2. É o MVP.
- **US2 (Fase 4)**: depende da Fase 2; usa o adaptador do mapa e a regra do nível da US1, então segue a US1 na prática.
- **US3 (Fase 5)**: depende da US2 (o destaque nasce do painel e o toque no ícone abre o painel).
- **US4 (Fase 6)**: depende da US2 (a busca abre o painel).
- **US5 (Fase 7)**: depende da US1 (a legenda); independente de US2 a US4.
- **Coleta de postos (Fase 8)**: depende só da Fase 2 e da coleta de alertas da US1 (cliente educado); pode rodar a qualquer momento depois da US1, mas fica por último por escolha de prioridade. Não bloqueia nenhuma história.
- **Polish (Fase 9)**: depende das fases desejadas concluídas.

### Dentro de cada história

- Testes primeiro: escreva e veja **falhar** antes de implementar.
- Modelos e repositórios antes de serviços; serviços antes de rotas; funções puras antes dos componentes; componentes antes da integração em `App.tsx`.
- Tarefas que editam o mesmo arquivo (`adaptador-maplibre.tsx`, `reducer.ts`, `App.tsx`, `dtos.py`) não são paralelas entre si.

### Oportunidades de paralelismo

- Setup: `T001`, `T002`, `T005`, `T006`, `T007`, `T009`.
- Foundational: testes `T011`, `T015`, `T019`, `T021`, `T027` e os do frontend `T030`, `T033`, `T036` em paralelo; backend e frontend caminham juntos depois do OpenAPI de contrato.
- US1: todos os testes de backend `T039` a `T048` em paralelo; backend e frontend em paralelo depois de `T059`.
- US2 a US5: o trabalho do frontend de US4 e US5 pode andar em paralelo depois da US2.

## Exemplo de paralelismo: User Story 1

```text
# Testes do backend da US1, juntos (arquivos diferentes):
Task: T039  Task: T040  Task: T042  Task: T044  Task: T047

# Frontend da US1 enquanto o backend é implementado (depois de T059):
Task: T067  Task: T070  Task: T071  Task: T066
```

## Implementation Strategy

### MVP primeiro (somente a User Story 1)

1. Fase 1: Setup. 2. Fase 2: Foundational (bloqueia tudo). 3. Fase 3: US1.
4. **Parar e validar**: `quickstart.md`, passos 1 a 4, e `uv run poe verificar` + `npm run verificar`.
5. Mostrar o mapa com níveis reais.

### Entrega incremental

1. Setup + Foundational. 2. US1 (mapa com níveis) → validar. 3. US2 (painel) → validar. 4. US3 (postos no mapa e destaque). 5. US4 (busca). 6. US5 (filtro). 7. Coleta de postos (melhor esforço). 8. Polish.
Cada história acrescenta valor sem quebrar a anterior.

## Notes

- `[P]` = arquivos diferentes, sem dependência de tarefa incompleta.
- `[US#]` liga a tarefa à história da spec para rastreabilidade.
- As tarefas da Fase 8 levam `[US2]` porque servem ao painel (FR-011), mas rodam por último.
- Confirme que cada teste falha antes de implementar.
- Faça commit só quando o usuário pedir.
- Pare em qualquer checkpoint para validar a história sozinha.
- Evite: tarefas vagas, conflito no mesmo arquivo, dependências entre histórias que quebrem a independência.

