# Implementation Plan: Chat de dúvidas de viagem com base nos alertas e nos dados do site

**Branch**: `003-chat-alertas-viagem` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-chat-alertas-viagem/spec.md` (com a sessão de clarificação de 01/11/2026)

> **Aprovado em 01/11/2026**: as três decisões do pedido (`research.md`, seção 1: **pgvector**, **embeddings por API do Gemini a 768 dimensões**, **projeto Google separado para o chat com teto de 500/dia**) e os cinco pontos de "Pontos aprovados" abaixo, com **três acréscimos** feitos na mesma data: (1) **perguntas de lista sem país específico**, com ferramentas de lista (D15; FR-013a, FR-013b e SC-017 na spec); (2) **troca da imagem do PostgreSQL** para a do pgvector em desenvolvimento, produção e CI, com a base Debian e o arm64 conferidos e o passo de ordenação do volume no `quickstart.md` (`research.md` 2.3); (3) **modelo e dimensão guardados com cada vetor**, busca só entre vetores do mesmo modelo e o comando **`reindexar`** (D3).

## Summary

Um chat em que a pessoa pergunta em português e recebe resposta **só com base nos dados do site**: trechos dos textos dos alertas do Itamaraty (história P1) e os registros que o painel já mostra, nível, visto e postos (P2), com seguimentos na mesma sessão, recusa do que está fora do assunto (P3) e limites, indisponibilidade e privacidade tratados (P3).

O desenho tem uma ideia só, repetida em cada camada: **o modelo de linguagem escreve prosa; tudo o que importa é montado pelo código.**

- Um módulo novo, `farol.chat`, na camada de `mapa`, `coleta`, `classificacao` e `vistos`, sem importar nenhum deles. Ele define **Protocols** para as ferramentas de nível, visto e postos; as implementações vivem na `api` e chamam **as mesmas funções que montam o painel** (`montar_painel`, `montar_visto_do_pais`), então o chat não reimplementa regra nenhuma.
- Um **agente LangChain 1.x** com quatro ferramentas (`consultar_nivel`, `consultar_visto`, `consultar_postos`, `buscar_nos_alertas`). O **país** vem do código (nomes da busca do site, mensagens anteriores *da pessoa*); o modelo só pode consultar países que o código detectou.
- Uma **trava no código** (resposta que fala de nível, visto ou posto sem a ferramenta correspondente é descartada e refeita com a ferramenta obrigatória), um **verificador de prosa** e **cartões e citações montados pelo código** a partir dos dados recuperados, inclusive o "Ver trecho", que é `alerta.texto[inicio:fim]`. Se a trava ou o verificador falham, a resposta vira só os cartões do painel, que também é o **modo de contingência** quando não há modelo.
- **Perguntas de lista** ("quais países têm alerta de não viajar?", "para onde posso ir só com o RG?"): duas ferramentas de lista, lidas das **mesmas funções do mapa e dos vistos** (`montar_mapa`, `montar_vistos_do_mapa`), que devolvem os mesmos países do filtro da legenda, em um cartão `lista` com total, até 50 nomes, fonte e data. Valem as mesmas regras de linguagem ("sem alerta" nunca é "seguro"); cruzar critérios ou pedir "os mais seguros" é recusa.
- **Busca nos alertas** em `pgvector`, no PostgreSQL que já existe (uma tabela, `trecho_alerta`), com filtro por país e plano B de busca textual. Cada vetor guarda **o modelo e a dimensão** com que foi gerado e a busca só compara vetores do mesmo modelo e da mesma dimensão; trocar de modelo é mudar a variável e rodar `python -m farol.worker reindexar`. Embeddings `gemini-embedding-001` (768) por API; vetores pré-calculados como fixture para o CI.
- **Indexação** por um varredor idempotente de 5 em 5 minutos, em executor próprio do worker, que só vetoriza o que mudou (hash por alerta); a saída de um alerta é imediata na consulta, e a entrada fica dentro dos 15 minutos de FR-008.
- `POST /api/v1/chat` com **resposta em SSE** (progresso e resultado final, não tokens), prazo de **20 s**, **20 perguntas/hora por IP** (memória do processo) e **teto global de 500/dia** (contador no banco, horário de Brasília, que sobrevive a reinício). Falhas por indisponibilidade ou tempo devolvem a vaga. Só **contagens anônimas** são gravadas.
- Frontend: botão flutuante, chat como painel (desktop) ou gaveta (celular), convivendo com legenda, linha de fonte, aviso e a barra do painel recolhido da 002; "Ver trecho" recolhido; histórico só em memória.
- **60 perguntas-gabarito** versionadas; a parte determinística roda no CI com modelo e vetores falsos, e a avaliação com o modelo real é um comando à parte.

Detalhes: [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/) e [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.13 (backend e worker); TypeScript com `strict: true` (frontend). Igual à 001 e à 002.

**Primary Dependencies**: as da 002 (FastAPI 0.162 com SSE nativo, SQLAlchemy 2.1, LangChain 1.4.7, langchain-core 1.7, langchain-google-genai 4.4.2, APScheduler, React 19, Vite). **Uma dependência nova de backend: `pgvector`** (tipo `Vector` do SQLAlchemy; usa o `numpy` já instalado). **Nenhuma nova no frontend** (`fetch` com `ReadableStream` lê o SSE). Sem torch, sem sentence-transformers, sem Chroma.

**Storage**: PostgreSQL 18 **trocando a imagem para `pgvector/pgvector:0.8.7-pg18-trixie`** (conferido: é o `postgres:18-trixie`, a mesma base Debian 13 do `postgres:18` atual, com `linux/arm64`; mesmo major, o volume é reaproveitado, com a conferência de ordenação do `quickstart.md`); migração Alembic `0005_chat` (extensão `vector`, `trecho_alerta`, `contagem_chat`); nenhuma tabela da 001, da 002 nem da `versao_dados` muda.

**Testing**: pytest (PostgreSQL de teste com pgvector; modelo de chat falso roteirizado; `EmbeddadorFalso`; vetores pré-calculados do gabarito; sem rede) e Vitest + Testing Library (SSE simulado; mapa falso). Gabarito de 60 perguntas em `backend/tests/gabarito/chat/`. Avaliação com modelo real: `uv run poe avaliar-chat`, fora do CI.

**Target Platform**: Docker Compose (desenvolvimento e produção) e Vercel para o frontend, como na produção já preparada; VM ARM (Ampere) da Oracle com Caddy.

**Project Type**: web-service + web-application, com o worker agendado na mesma imagem.

**Performance Goals**: resposta em até **20 s** (FR-027), tipicamente poucos segundos; cinco perguntas simultâneas sem lentidão do site nem das coletas (SC-013); consultas ao banco em número fixo por pergunta; **carregamento inicial do mapa não piora mais que 5%** (o código e os dados do chat só são buscados quando a pessoa abre o chat).

**Constraints**: nada de conversa no servidor; só contagens anônimas; 360 px; texto de alerta, de Wikipédia e histórico tratados como dados; operação gratuita (Gemini gratuito e pgvector); **cabe em ~1 GB de uso total (recomendado 2 GB)**; Caddy aceita POST de até 16 KB só em `/api/v1/chat`.

**Scale/Scope**: ~18 alertas (cresce devagar), 100 a 150 trechos, 500 perguntas por dia no máximo, 20 por hora por IP.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Resultado | Como o plano atende |
|---|---|---|
| I. Qualidade por ferramenta | Passa | Ruff, mypy `strict`, ESLint e `tsc` `strict` valem para tudo; sem `any` (os eventos do SSE são validados em tempo de execução). `uv run poe verificar` e `npm run verificar` verdes, incluindo o gabarito determinístico. |
| II. TDD | Passa | Cada peça nasce de teste: fatiamento, recuperação, trava, verificador, montagem de citações, limites, CORS, contagens, hook do SSE, componentes. **Sem rede e sem LLM real**: modelo de chat falso roteirizado, `EmbeddadorFalso` e vetores pré-calculados em arquivo; o CI nunca baixa modelo nem chama API. A avaliação com o modelo real é um comando à parte. |
| III. Arquitetura | Passa (constituição **v1.0.3**) | `chat` é módulo novo na camada de `mapa`/`coleta`/`classificacao`/`vistos`, sem importar nem ser importado por eles; contratos do import-linter atualizados (D1). Rotas finas: a rota `chat` só valida, aplica limites e repassa ao pipeline; regra em serviços; **só os repositórios falam SQL** (`TrechoAlertaRepositorio`, `ContagemChatRepositorio` em `dominio`). DTOs Pydantic na entrada e na saída; tipos do frontend gerados do OpenAPI v1.2. Backend só devolve JSON e SSE com JSON, sem HTML. Sem N+1 (número fixo de consultas por pergunta, com teste). Frontend por funcionalidade (`funcionalidades/chat`), componentes sem regra e sem chamar a API (só `useChat`), e o chat é buscado **sob demanda** quando a pessoa o abre, como o princípio III já permite; o carregamento inicial do mapa não depende dele. |
| IV. Coleta responsável | Passa (nada novo) | Nenhuma coleta nova: o chat usa os alertas que o worker já coleta. O varredor só lê o banco e chama a API de embeddings. A cadência de requisições ao gov.br e à Wikipédia não muda. |
| V. Informação confiável | Passa | "Responder apenas com base nos documentos coletados, citar as fontes e dizer quando não sabe": é a espinha do desenho (ferramentas como única fonte; citações montadas pelo código; "não encontrei" com indicação do painel ou do Portal). "Sem alerta" nunca vira "seguro"; "não verificado" sem nível; "sem informação de visto" nunca "isento"; fonte e data em tudo; site continua avisando que não é oficial (aviso fixo no chat). |
| VI. Acessível e celular | Passa | Teclado completo, foco gerenciado, `aria-live`, contraste AA, 44 px, 360 px, `prefers-reduced-motion`, informação que não depende de cor (rótulos "em vigor"/"anterior" em texto). Detalhes em [contracts/chat-ui.md](contracts/chat-ui.md). |
| VII. Simples e gratuito | Passa | Sem serviço novo no compose (o pgvector é uma extensão do banco que já roda); Gemini no plano gratuito. Modelo e embeddings configuráveis por variável; **"o chat MUST continuar respondendo se o provedor principal falhar"**: modelo alternativo (`LLM_CHAT_ALTERNATIVO`) e, sem nenhum modelo, o modo só registros (cartões do painel). |
| VIII. Segurança | Passa | A única rota que não é GET é a pergunta do chat; **limite por IP (20/h)**, **tamanho máximo da pergunta (500)** e **tempo máximo (20 s)** estão no desenho, além do teto global de 500/dia. Entrada validada por Pydantic; SQL só parametrizado; textos externos e histórico como dados (delimitadores, ferramentas só de leitura restritas a países do código, citações e links do código, verificador de prosa); CORS só do domínio do frontend (por rota, sem credenciais); banco sem porta publicada (vetores dentro dele); chaves só em variável de ambiente (`SecretStr`), nunca no repositório nem no frontend, e toda chamada ao LLM sai do backend; **perguntas não ficam associadas ao IP** (janela por IP só em memória, contagens sem texto nem IP, rastreamento externo desligado e testado). |
| Idioma | Passa | Interface, documentação, nomes e comentários em português. |

**Re-checagem após o desenho (Fase 1):** sem violações. Dois pontos de atenção, ambos cobertos por teste: (a) o contador de versão dos dados não pode ser disparado pelas contagens do chat (invalidaria o cache de leitura); (b) a constituição cita "Chroma" como exemplo em VIII; com pgvector a regra vale para "o banco". Uma emenda **PATCH 1.0.4** opcional trocaria "Banco e Chroma" por "Banco e qualquer índice vetorial"; não é necessária para este plano.

## Pontos aprovados (01/11/2026)

As três decisões que você pediu (1.1 a 1.3 do `research.md`) e estas posições, que **diferem ou acrescentam** ao pedido original, foram aprovadas:

1. **Fallback de modelo**: você indicou `with_fallbacks`. Para o agente com ferramentas, recomendo o `ModelFallbackMiddleware` do LangChain 1.x, e `with_fallbacks` fica para as chamadas sem ferramentas. A primeira tarefa é um teste de 15 minutos que confirma se o `create_agent` aceita `with_fallbacks`; se aceitar, uso só ele.
2. **País decidido pelo código, não pelo modelo**: a detecção de país (e a pergunta de volta em caso de ambiguidade) acontece antes do modelo, e as ferramentas só aceitam países que o código detectou. Poupa cota e fecha uma porta de injeção; custa pouca flexibilidade (um país citado de forma muito indireta não é achado).
3. **Streaming só de progresso e resultado, sem tokens**: a trava pode descartar e refazer a resposta; mostrar tokens ao vivo exporia texto que seria jogado fora.
4. **Metadados do índice**: guardo `paises` e `em_vigor_para` como você pediu, mas a **verdade na hora da resposta** é a ferramenta de nível (a do painel), e a consulta já exclui, por `JOIN`, o que saiu da lista ou mudou de hash. Assim um descompasso de minutos nos metadados nunca vira afirmação errada.
5. **Limite por IP em memória do processo** (zera no reinício; garante que IP não vai a disco) e **teto global no banco** (sobrevive a reinício, como você pediu). A produção roda 1 processo da API, como já documentado.

## Project Structure

### Documentation (this feature)

```text
specs/003-chat-alertas-viagem/
├── plan.md              # Este arquivo
├── research.md          # Fase 0: as 3 decisões comparadas, conferências, decisões D1 a D14 e riscos
├── data-model.md        # Fase 1: trecho_alerta, contagem_chat, estado em memória, citação e cartão
├── quickstart.md        # Fase 1: como validar de ponta a ponta
├── contracts/
│   ├── openapi.yaml               # API v1.2 COMPLETA (substitui a v1.1 nos testes de contrato e nos tipos do frontend)
│   ├── ferramentas-do-chat.md     # Fronteiras do módulo, Protocols, ferramentas, pipeline, trava e verificador
│   ├── indexacao-e-comandos.md    # Varredor, agenda (executor próprio) e comando `indexar`
│   ├── caddy-cors-limites.md      # Caddyfile, CORS por rota, limites e variáveis de ambiente
│   ├── chat-ui.md                 # Componentes, estado, convivência com o layout, acessibilidade e textos
│   └── gabarito.md                # Formato das 60 perguntas e o que roda no CI × avaliação real
├── checklists/requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks) — não criado aqui
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                           # + `pgvector`; contratos do import-linter (D1); tarefa poe `avaliar-chat`
├── alembic/versions/0005_chat.py            # novo: extensão vector, trecho_alerta, contagem_chat
├── src/farol/
│   ├── infra/
│   │   ├── config.py                        # variáveis novas (D12)
│   │   ├── banco.py, versao.py              # abrir_sessao(..., versiona=True): False p/ contagens do chat
│   │   └── modelo.py                        # argumentos_do_modelo aceita a chave do chat
│   ├── dominio/
│   │   ├── modelos.py                       # + TrechoAlerta, ContagemChat
│   │   └── repositorios/trechos.py, contagens_chat.py     # novos; exportados em dominio/__init__.py
│   ├── mapa/
│   │   └── __init__.py, servico.py          # + alertas_que_definem_nivel (sem mudar comportamento)
│   ├── chat/                                # NOVO módulo (interface pública no __init__)
│   │   ├── __init__.py
│   │   ├── protocolos.py                    # ResolvedorDePaises, ConsultaDeNivel/Visto/Postos, Embeddador + valores
│   │   ├── fatiamento.py                    # texto do alerta → intervalos [inicio, fim)
│   │   ├── indexador.py                     # indexar_pendentes (idempotente) e reindexar (troca de modelo/dimensão)
│   │   ├── recuperacao.py                   # RecuperadorDeTrechos (vetorial + textual)
│   │   ├── entendimento.py                  # país, ambiguidade, intenção de lista e histórico (só mensagens da pessoa)
│   │   ├── ferramentas.py                   # as 4 ferramentas do agente + artefatos
│   │   ├── agente.py, modelo.py             # create_agent, criar_modelo_do_chat (principal + alternativo)
│   │   ├── trava.py, verificador.py         # trava e verificador de prosa
│   │   ├── contingencia.py                  # roteador de palavras-chave + modo só registros
│   │   ├── montador.py                      # cartões, citações, "Ver trecho", avisos do sistema
│   │   └── pipeline.py                      # a pergunta de ponta a ponta, com prazo e eventos de progresso
│   ├── api/
│   │   ├── rotas/chat.py                    # POST /chat (SSE), validação, limites; sem regra de negócio
│   │   ├── chat/ferramentas.py              # implementações dos Protocols (usam montar_painel_com_visto, montar_mapa,
│   │   │                                    #   montar_vistos_do_mapa: nível, visto, postos e as listas de países)
│   │   ├── chat/limites.py                  # janela por IP, teto do dia, devolução de vaga
│   │   ├── chat/cors.py                     # despachante de CORS por rota (ou em app.py)
│   │   ├── dtos.py                          # + DTOs do chat (espelham o contrato)
│   │   └── app.py                           # CORS por rota; rota registrada; LANGSMITH desligado
│   └── worker/
│       ├── agenda.py                        # + executor `indexacao` e job periódico
│       ├── jobs.py                          # + indexar_real
│       └── comando.py                       # + `indexar [--tudo|--status]` e `reindexar [--manter-antigos]`; coletar --alertas/reclassificar indexam ao fim
├── tests/
│   ├── unidade/chat/                        # fatiamento, entendimento, trava, verificador, montador, contingência, ferramentas
│   ├── unidade/api/                         # CORS por rota, limites, SSE
│   ├── unidade/worker/                      # agenda com o executor novo
│   ├── integracao/chat/                     # repositórios (pgvector), indexador, recuperação, pipeline, painel × ferramentas
│   ├── gabarito/chat/                       # gabarito.yaml (60), test_gabarito.py, vetores.npz
│   └── fixtures/chat/                       # alertas.json, registros de teste
ferramentas/
├── gerar_vetores_do_gabarito.py             # novo (usa a chave; gera vetores.npz)
├── exportar_alertas_para_gabarito.py        # novo (banco local → fixtures/chat/alertas.json)
├── avaliar_chat.py                          # novo (avaliação com modelo real)
└── verificar-caddy.sh                       # + checagens do /chat
deploy/Caddyfile                             # + handle do /chat (16 KB, sem encode, flush)
docker-compose.yml, docker-compose.prod.yml  # imagem do banco com pgvector; LANGSMITH_TRACING=false
.github/workflows/ci.yml                     # serviço de PostgreSQL com pgvector; lista de imagens do job `producao`
.env.example, docs/deploy.md                 # variáveis novas; chave do chat; cota; restauração (extensão no dump)

frontend/
├── scripts/gerar-tipos.mjs                  # lê o contrato da 003
└── src/
    ├── estado/reducer.ts                    # + chatAberto, abrir-chat, fechar-chat
    ├── servicos/api/chat.ts                 # POST + leitor de SSE, validação em tempo de execução
    ├── servicos/api/esquema.d.ts            # regenerado
    ├── funcionalidades/chat/                # BotaoDoChat, Chat, ListaDeMensagens, MensagemDoChat, Cartoes,
    │                                        #   Citacao/VerTrecho, CaixaDePergunta, AvisoFixoDoChat, useChat
    └── App.tsx                              # monta o botão e o chat; Esc; barra do painel enquanto o chat está aberto
```

**Structure Decision**: o monolito modular da 001 e da 002, com um módulo novo (`chat`) na camada do meio; frontend por funcionalidade; nenhum serviço novo no compose (a imagem do banco muda).

### Testes existentes que mudam (consequência do desenho, não regressão)

| Teste | Mudança |
|---|---|
| `tests/integracao/api/test_app.py::test_cors_nao_libera_metodos_de_escrita`, preflights de `tests/unidade/api/test_app_producao.py` | Continuam valendo para todas as rotas **exceto** `/chat`; ganham casos do `/chat` |
| `tests/integracao/api/test_seguranca.py` (rotas só de leitura) | A lista de rotas de escrita permitidas passa a ser exatamente `[POST /api/v1/chat]` |
| `tests/contrato/` | O contrato completo passa a ser o da 003; novo teste de que a parte da 002 não mudou |
| `tests/unidade/infra/test_compose_producao.py` | Lista de imagens de terceiros: `postgres:18` → `pgvector/pgvector:0.8.7-pg18-trixie`; teste novo: a mesma tag no `docker-compose.yml` (dois serviços), no `docker-compose.prod.yml` e no `ci.yml` |
| `tests/integracao/dominio/test_migracoes.py` | Tabelas novas; downgrade para a `0004` |
| `tests/integracao/api/test_cache_integrado.py` / `test_versao_dos_dados.py` | Caso novo: contagem do chat **não** sobe a versão |
| `ferramentas/verificar-caddy.sh` e o job `producao` do CI | Checagens do `/chat` |

## Ordem de implementação sugerida (insumo para `/speckit-tasks`)

Cada fase termina com `poe verificar` e `npm run verificar` verdes; testes antes do código.

1. **Fundação**: troca da imagem do banco (dev, teste, CI, produção); migração `0005_chat`; modelos e repositórios; `Configuracoes`; `abrir_sessao(versiona=…)`; contratos do import-linter e módulo `chat` vazio. *(Verifica: migrações, camadas.)*
2. **Indexação**: fatiamento, `Embeddador` (real e falso), `indexar_pendentes` (modelo e dimensão por vetor, busca só do mesmo modelo), `reindexar`, `mapa.alertas_que_definem_nivel`, comandos `indexar` e `reindexar`, agenda com executor próprio. *(Verifica: contrato `indexacao-e-comandos.md`.)*
3. **Núcleo do chat — P1 (MVP)**: recuperação, entendimento do país, ferramentas, agente, trava, verificador, montador, pipeline, rota SSE, limites, CORS por rota, contrato OpenAPI v1.2. *(Verifica: gabarito de `alertas`, `sem_resposta`, `fora_do_escopo`, `injecao`.)*
4. **Registros — P2**: implementações de nível, visto e postos na `api`, **ferramentas e cartão de lista de países**, cartões, contingência. *(Verifica: tipos `nivel`, `visto`, `postos`, `lista`; comparação com `GET /paises`, `GET /mapa` e `GET /vistos`.)*
5. **Conversa — P3**: seguimentos, histórico não confiável, perguntas de volta. *(Verifica: `seguimento`, `historico_adulterado`.)*
6. **Frontend**: serviço SSE, `useChat`, componentes, layout e acessibilidade, gerar tipos. *(Em paralelo com 3 a 5 depois do contrato fechado.)*
7. **Borda e operação — P3**: Caddyfile, `verificar-caddy.sh`, compose e CI de produção, `docs/deploy.md`, `.env.example`, teste de fumaça.
8. **Fechamento**: avaliação com o modelo real, ajuste de prompt/fatiamento, medição de memória e de cota, `quickstart.md` percorrido do início ao fim.

O **MVP (P1)** são as fases 1, 2, 3 e a parte do frontend da fase 6 que abre o chat e mostra resposta com citações; ele já é demonstrável e entrega a história 1.

## Complexity Tracking

Nenhuma violação da constituição. As complexidades abaixo são escolhas do desenho, registradas porque existe uma alternativa mais simples que foi rejeitada:

| Escolha | Por que é necessária | Alternativa mais simples rejeitada por quê |
|---|---|---|
| Trava + verificador de prosa + cartões do código | O princípio V e o FR-001 exigem que nível, visto e posto sejam exatamente os do painel, e o modelo pode errar ou ser induzido | "Confiar no prompt" não é verificável e não passa nos critérios SC-003, SC-006 e SC-007 |
| Varredor em executor próprio | A regra de 15 minutos (FR-008) não pode esperar os ~45 min da coleta mensal de postos | Indexar só ao fim da coleta de alertas atrasaria a entrada se o executor único estivesse ocupado |
| CORS e Caddy por rota | O pedido exige POST e corpo maior só no chat, mantendo GET-only e 1 KB no resto | Liberar POST globalmente enfraqueceria o princípio VIII |
| `versiona=False` nas contagens | Sem isso cada pergunta invalidaria o cache de leitura | Contar fora do banco perderia o teto que sobrevive a reinício |
