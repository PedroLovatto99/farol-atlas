# Pesquisa e decisões: chat de dúvidas de viagem (feature 003)

**Data**: 2026-11-01 | **Spec**: [spec.md](spec.md) | **Plano**: [plan.md](plan.md)

Este documento resolve tudo o que o plano deixou em aberto. A seção 1 traz as **três decisões que são suas**, cada uma com a comparação e a minha recomendação; a seção 2 traz o que foi conferido no código e nos pacotes instalados; a seção 3 traz as demais decisões técnicas (D1 a D14), já tomadas dentro do que você definiu no pedido do plano; a seção 4, os riscos.

**Como a confiança está marcada**: "conferido" = li no código do repositório ou rodei no ambiente; "fonte" = veio de uma página citada; "estimativa" = ordem de grandeza minha, a confirmar na implementação. O que dependia do Docker (que estava parado ao escrever este documento) está marcado como **a conferir antes de codar** e entra no `quickstart.md`.

---

## 1. Decisões suas, com recomendação

### Dado que decide quase tudo: o corpus é minúsculo

No banco local há **18 alertas**, de 434 a 12.015 caracteres (média 2.585), em **17 países** (levantamento da investigação de 29/10). Em trechos de ~1.000 caracteres dá algo como **100 a 150 trechos** no total, e mesmo com o triplo disso seria pouco. Isso torna desnecessário qualquer índice de busca aproximada, faz o armazenamento de vetores custar quase nada e deixa o **filtro por país** (que o pedido já prevê) fazer a maior parte do trabalho de "achar o alerta certo": para "o que fazer se eu já estou no Irã?", sobram um ou dois alertas, e a busca por similaridade só escolhe os parágrafos dentro deles.

### 1.1 Armazenamento dos vetores: Chroma × pgvector

| Critério | Chroma (servidor próprio) | pgvector no PostgreSQL existente |
|---|---|---|
| Memória num servidor pequeno | Mais um serviço (Python + SQLite/DuckDB + hnswlib): **estimativa de 250 a 500 MB** em repouso, fora o cliente | **Quase zero**: ~150 linhas × 768 floats ≈ 0,5 MB no mesmo PostgreSQL que já roda |
| Operação | Serviço novo no compose (dev, produção e teste), porta, volume, healthcheck, versão a acompanhar | Nenhum serviço novo. Troca de imagem do banco e uma extensão |
| Backup | Fora do `pg_dump`: o script `ferramentas/backup-banco.sh` não o cobre; precisa de cópia de volume e de ordem de restauração | **Dentro do `pg_dump`**: backup e restauração já descritos em `docs/deploy.md` passam a cobrir os vetores |
| Consistência com a regra de 15 minutos (FR-007, FR-008) | Dois sistemas: o alerta muda no PostgreSQL, o trecho no Chroma. Sem transação conjunta; precisa de reconciliação | **Uma transação**: o trecho é gravado ou removido junto com a verificação do hash do alerta; e a consulta pode fazer `JOIN` com `alerta` e já excluir, na hora, o que saiu da lista ou mudou de hash |
| Testes no CI | Cliente em memória (`EphemeralClient`) serve, mas é outro comportamento do de produção | O CI já sobe um PostgreSQL; basta trocar a imagem do serviço por uma com pgvector. Mesmo SQL de produção |
| Valor de aprendizado | Alto para "vector DB" como produto | Alto para busca vetorial dentro de SQL, e o filtro relacional + vetor numa só consulta é justamente o caso desta feature |
| Camadas da constituição | O cliente do Chroma ficaria fora de `dominio`, quebrando "só os repositórios falam com o banco" | Cabe no padrão: um repositório em `dominio` com `Vector` do SQLAlchemy |
| Riscos | Mais uma peça para atacar (constituição VIII fala de "Chroma" exposto) | Troca de imagem do PostgreSQL (ver 2.3); extensão `vector` exige `CREATE EXTENSION` na migração |

**Recomendação: pgvector.** Para esse tamanho de corpus, o Chroma só acrescentaria um serviço, memória e uma segunda fonte de verdade sem trazer nenhuma capacidade de que a feature precise. Sobre o "previsto no plano original": a constituição cita o Chroma como exemplo ("Banco e Chroma MUST NOT ficar expostos"), não como obrigação; com pgvector, os vetores ficam dentro do banco e a regra continua cumprida sem emenda (se preferir, uma emenda PATCH 1.0.4 pode trocar "e Chroma" por "e qualquer índice vetorial"). Se você quiser Chroma pelo aprendizado, o desenho permite: o acesso fica atrás de um `Protocol` de recuperação (D4), e o custo da troca é um repositório novo; mas o ganho de consistência e backup se perde.

**Detalhes que decorrem da escolha**
- Sem índice de aproximação (HNSW/IVFFlat) enquanto houver menos de ~10 mil trechos: varredura exata é mais rápida e dá o resultado certo. A migração não cria índice vetorial; só índice comum por `alerta_id`.
- Operador de distância cosseno (`<=>`).
- **Coluna `vector` sem dimensão fixa**, com `CHECK (vector_dims(embedding) = dimensoes)`: cada linha guarda o **modelo** e a **dimensão** com que foi vetorizada, e a busca só compara vetores do mesmo modelo e da mesma dimensão (`WHERE modelo_embedding = :modelo AND dimensoes = :dimensoes` antes do `ORDER BY` por distância; vetores de dimensões diferentes nunca são comparados). Sem índice vetorial isso não custa nada; se um dia houver índice (acima de ~10 mil trechos), ele passa a ser parcial por modelo. Trocar de modelo ou de dimensão não exige migração: muda a variável e roda `python -m farol.worker reindexar` (D3).

### 1.2 Embeddings: modelo local × serviço por API

| Opção | Memória | Português | Custo e cota | Latência | Gabarito no CI sem rede |
|---|---|---|---|---|---|
| **bge-m3 local** (o previsto) | ~568 M parâmetros: arquivo ~2,2 GB (fp32), **2,5 a 3 GB de RAM** em uso (estimativa); precisa de torch ou de ONNX, e a imagem do backend cresce centenas de MB | Muito boa, multilíngue, até 8.192 tokens | Zero de cota; custo é a máquina | Dezenas a centenas de ms por trecho em CPU Ampere (estimativa) | Baixar o modelo no CI (2 GB, lento) ou vetores pré-calculados |
| **Modelo local menor** (fastembed/ONNX: `paraphrase-multilingual-MiniLM-L12-v2`, 0,22 GB, 384 dim; `multilingual-e5-large`, 2,24 GB, 1024 dim; fonte: lista do fastembed) | MiniLM ~300 a 500 MB de RAM (estimativa); e5-large como o bge-m3 | MiniLM: **truncado em 128 tokens**, bem abaixo do tamanho de um trecho, então perde conteúdo; e5-large: boa | Zero | Baixa | O modelo é pequeno (MiniLM), mas a qualidade com trechos de 1.000 caracteres é o problema |
| **API do Gemini** (`gemini-embedding-001`, texto, 2.048 tokens de entrada, dimensão ajustável de 128 a 3072, recomendadas 768, 1536 e 3072; tem `task_type` `RETRIEVAL_DOCUMENT`/`RETRIEVAL_QUERY`; fonte: documentação do Gemini) | **Zero** no servidor; o cliente já está em `langchain-google-genai` (conferido: `GoogleGenerativeAIEmbeddings` com `output_dimensionality` e `task_type`) | Boa, multilíngue | Plano gratuito. Limites do modelo **não estão na documentação pública**: só no AI Studio. Números de fórum (não verificados): 100 RPM, 30 mil TPM, 1.000 RPD. Uso real: 1 chamada por pergunta (a consulta) + poucas dezenas para indexar um alerta novo | Uma ida e volta de rede (centenas de ms) | Vetores pré-calculados como fixture (ver abaixo) |
| `gemini-embedding-2` (multimodal, 8.192 tokens, sem `task_type`) | Zero | Boa | Não pesquisei limites | idem | idem |

**Recomendação: `gemini-embedding-001` por API, a 768 dimensões**, atrás de um `Protocol` (`Embeddador`). Razões: (1) o servidor "de 1 a 12 GB" não precisa reservar 3 GB para um modelo que vetoriza 150 trechos e uma pergunta por vez; (2) a imagem do backend não ganha torch nem ONNX; (3) qualidade em português e entrada de 2.048 tokens cobrem um trecho de ~1.000 caracteres com folga; (4) usa a conta Google que o projeto já tem; (5) 768 dimensões ocupam metade de 1.536 e perdem pouco para o corpus pequeno.

**O que se perde, e como se cobre**
- *Depender da rede e da cota na hora de perguntar.* Cobertura: se o embedding da pergunta falhar, a busca nos alertas cai para **busca textual do PostgreSQL** (`to_tsvector('portuguese', …)`), com o mesmo filtro por país (D4). Não é igual, mas com o filtro por país o corpus candidato é de 1 a 3 alertas e a busca textual acerta bem; é só o plano B.
- *Trocar de modelo muda os vetores.* Cobertura: **modelo e dimensão ficam gravados em cada vetor** e a busca só compara vetores do mesmo modelo e da mesma dimensão (2.3 e D3); trocar a variável e rodar `python -m farol.worker reindexar` refaz tudo (poucas dezenas de chamadas); no intervalo, os alertas sem vetores do modelo configurado entram pela busca textual.
- *CI sem rede.* **Vetores pré-calculados como fixture**: um script único (`ferramentas/gerar_vetores_do_gabarito.py`, rodado à mão com a chave) vetoriza os trechos dos alertas de teste e as perguntas do gabarito que dependem de recuperação e grava `vetores.npz` com o hash do texto de cada item; um teste falha se o hash do trecho (ou da pergunta) não bater mais com o texto atual, mandando regerar. O CI nunca baixa modelo e nunca usa rede. Para os demais testes, um `EmbeddadorFalso` determinístico.
- *Alternativa se um dia o servidor for grande*: trocar o `Embeddador` por um modelo local; nada mais muda.

Observação de privacidade (vale citar na documentação): no plano gratuito do Gemini, o texto enviado (inclusive a pergunta) pode ser tratado segundo os termos do plano gratuito da Google. O aviso fixo do chat já manda não digitar dados pessoais (FR-016); nada disso passa a ser guardado em nosso servidor.

### 1.3 Divisão da cota entre o chat e a coleta (FR-028)

Fato relevante (documentação do Gemini): as cotas são aplicadas **por projeto**, não por chave, e **variam por modelo**. Quatro formas de separar:

| Forma | Isolamento | Custo operacional | Observação |
|---|---|---|---|
| **A. Projeto Google separado para o chat** (chave própria, `GOOGLE_API_KEY_CHAT`) | **Total**: o chat pode esgotar a cota dele sem encostar na da coleta | Criar um projeto e uma chave (grátis); uma variável | Resolve inclusive os embeddings do chat, que passam a usar a chave do chat |
| **B. Mesma chave, modelo diferente para o chat** (`LLM_CHAT` ≠ `LLM_CLASSIFICADOR`) | Parcial: a cota por modelo é separada, mas pedidos e tokens por minuto de projeto e os limites de abuso são compartilhados | Nenhum | Funciona como fallback da A |
| **C. Reserva para a coleta** (o chat consulta um contador compartilhado e para quando a cota restante cair) | Depende de saber a cota real, que a API não informa | Alto e frágil (a cota muda sem aviso) | Descartada |
| **D. Só o teto de 500 perguntas por dia** | Limita o tamanho do problema, não o isola | Já definido na spec | Insuficiente sozinho |

**Recomendação: A, com B como valor padrão e D como cinto de segurança.** Concretamente: `GOOGLE_API_KEY_CHAT` (obrigatória com o chat ligado e usando o Google; nunca cai em `GOOGLE_API_KEY`: sem ela a partida falha em produção e o chat fica indisponível em desenvolvimento, com mensagem clara, FR-028), `LLM_CHAT` (ausente = o mesmo modelo do classificador, o que **não** isola a cota: a documentação recomenda definir um modelo próprio), e o teto global de 500 perguntas por dia. O limite de chamadas por pergunta é duro (no máximo 4 chamadas ao modelo e 1 de embedding), então o pior dia é de **2.000 chamadas ao modelo + 500 de embedding**; compare isso com a cota real do projeto do chat no AI Studio antes de ligar para o público (item de checagem do `quickstart.md`). A coleta continua independente por um segundo motivo, que já é verdade hoje: ela roda no worker, em outro processo, e nenhuma etapa dela chama código do chat.

---

## 2. O que foi conferido

### 2.1 Código do repositório (conferido)

- **Como o painel monta nível e alertas**: `farol.mapa.montar_painel(sessao, codigo)` e `calcular_niveis` (mapa/painel.py, mapa/nivel.py). O alerta que rege o nível de cada território sai em `NivelDoTerritorio.alerta_id`; na lista de alertas do painel, `AlertaDoPais.define_nivel` marca o vigente. Visto: `farol.vistos.montar_visto_do_pais(sessao, codigo, relogio)` (`VisaoDoVisto`). `farol.api.composicao.montar_painel_com_visto` junta os dois. Postos: dentro de `montar_painel` (`PostoNoPainel`, posto responsável, `sem_posto_indicado`, `FontePostos`). **As ferramentas do chat reaproveitam essas funções, sem regra nova.**
- **Que alertas valem**: `AlertaRepositorio.listar_confirmados_ativos()` = confirmados por coleta completa (`confirmado_execucao_id`) e não removidos (`removido_em` nulo); a classificação vigente é a do `confirmado_hash` (`Alerta.classificacao_vigente()`).
- **Texto do alerta**: `alerta.texto` (espaços colapsados) e `alerta.html_corpo` (HTML do corpo, guardado "para reprocessar").
- **Camadas** (`pyproject.toml`): `api | worker` > `mapa | coleta | classificacao | vistos` > `dominio` > `infra`, com contratos de independência e de "só a interface pública". O `chat` entra na camada do meio e em todas as listas dos contratos (D1).
- **Já existente que a feature aproveita**: IP real do visitante (`IpReal`, `PROXY_CONFIAVEL=172.30.0.2/32`), limite geral de 120 pedidos/min (`LimiteDePedidos`), CORS (`allow_methods=["GET"]`), cache de leitura (só GET), contador de versão dos dados (`infra/versao.py`), `Configuracoes` com `llm_classificador`, `llm_tradutor`, `google_api_key`, `ollama_base_url`; `argumentos_do_modelo` em `infra/modelo.py`.
- **Tarefas e scripts**: `uv run poe verificar` = lint, formato, tipos, arquitetura (import-linter), testes e auditoria; `exportar-openapi`. No frontend, `npm run verificar` e `npm run gerar-tipos` (que hoje lê `specs/002-visto-brasileiros/contracts/openapi.yaml`). Worker: `python -m farol.worker [coletar …|reclassificar|vistos …]`.

### 2.2 Pacotes instalados (conferido no ambiente)

| Pacote | Versão | Uso |
|---|---|---|
| langchain / langchain-core | 1.4.7 / 1.7.0 | `create_agent`, `init_chat_model`, middleware (`ModelFallbackMiddleware`, `ModelCallLimitMiddleware`, `ToolCallLimitMiddleware`, `ModelRequest.tool_choice`) |
| langchain-google-genai | 4.4.2 | `GoogleGenerativeAIEmbeddings` (campos `model`, `task_type`, `output_dimensionality`) e o chat do Gemini |
| langgraph | 1.2.16 | base do `create_agent` (sem uso direto) |
| fastapi | 0.162.0 | **`fastapi.sse.EventSourceResponse`** e `ServerSentEvent`: SSE nativo, que "funciona com qualquer método HTTP" (inclusive POST) |
| starlette (GZip) | instalado | já trata `text/event-stream` (não comprime) |
| numpy | 2.5.4 | já presente |
| **pgvector** (Python) | a adicionar | tipo `Vector` do SQLAlchemy; **única dependência nova de backend** (tem como dependência o numpy, que já existe) |

Frontend: **nenhuma dependência nova** (o `fetch` com `ReadableStream` lê o SSE do POST; `EventSource` não serve porque só faz GET).

### 2.3 Imagem do PostgreSQL com pgvector (conferido no registro oficial em 01/11/2026)

- **Mesma base de Debian.** O `postgres:18` oficial é um apelido de `18-trixie` (Debian 13): no repositório `docker-library/postgres`, `18`, `latest` e `18-trixie` apontam para o mesmo diretório `18/trixie`, cujo `FROM` é `debian:trixie-slim` (PostgreSQL 18.6). O banco de desenvolvimento do projeto confirma na prática: a investigação de 29/10 leu `PostgreSQL 18.6 (Debian 18.6-1.pgdg13+2)`, e `pgdg13` é Debian 13. O `Dockerfile` do pgvector parte de `postgres:$PG_MAJOR-$DEBIAN_CODENAME`, então **`pgvector/pgvector:0.8.7-pg18-trixie` é o `postgres:18-trixie` mais a extensão**: mesma glibc, mesma ordenação de texto. A tag sem sufixo (`pg18`) é `bookworm` (Debian 12) e **não** serve; por isso a tag é fixada com `-trixie` e com a versão do pgvector (`0.8.7`).
- **arm64.** Conferido: as seis tags `pg18*` do `pgvector/pgvector` incluem `linux/arm64` (a `0.8.7-pg18-trixie` pesa ~155 MB no arm64), e o `postgres` oficial publica `amd64` e `arm64v8` para todo o 18. A VM Ampere e o CI (amd64) funcionam.
- **Volume existente.** Mesmo major (18), mesmo diretório de dados e mesma base de Debian: o volume do desenvolvimento é reaproveitado sem migração e sem `pg_upgrade`. Como defesa extra, o `quickstart.md` traz o passo de **conferir a versão de ordenação (collation) do volume** e, só se houver diferença, reconstruir os índices antes de aceitar a nova versão. Isso não pôde ser rodado ao escrever este plano (Docker parado) e não é um risco esperado, dado o parágrafo acima.
- A extensão se chama `vector` e a migração faz `CREATE EXTENSION IF NOT EXISTS vector` (o usuário do compose é superusuário do banco dele; o `pg_dump` inclui `CREATE EXTENSION`, então a restauração em outro banco com a mesma imagem funciona).
- **Lugares que mudam de imagem** (todos para a mesma tag fixa, `pgvector/pgvector:0.8.7-pg18-trixie`): `docker-compose.yml` (serviços `postgres` e `postgres-teste`), `docker-compose.prod.yml`, `.github/workflows/ci.yml` (serviço do job `backend` e a lista de imagens do job `producao`, que já confere `linux/arm64`), `backend/tests/unidade/infra/test_compose_producao.py` (lista de imagens permitidas e uma verificação nova: a imagem do banco é a mesma tag nos três arquivos) e `docs/deploy.md` (inclusive o aviso de fazer backup antes de trocar a imagem em um servidor que já tenha dados).

---

## 3. Demais decisões

### D1. Módulo `chat` e os contratos do import-linter

- Pacote novo `farol.chat`, **na camada de `mapa | coleta | classificacao | vistos`**, sem importar nenhum deles. Pode importar `farol.dominio` e `farol.infra` (pela interface pública).
- Os contratos do `pyproject.toml` mudam em: "Camadas" (acrescentar `farol.chat`), "Casos de uso independentes entre si" (acrescentar), um contrato novo "So a interface publica de chat" e `farol.chat.*` em `forbidden_modules` onde cada contrato já lista os módulos irmãos, e `farol.chat` entre os `source_modules` dos contratos de "interface pública" dos outros.
- **Protocols definidos em `farol.chat`** (ver [contracts/ferramentas-do-chat.md](contracts/ferramentas-do-chat.md)): `ConsultaDeNivel`, `ConsultaDeVisto`, `ConsultaDePostos`, `ResolvedorDePaises` e `Embeddador`. As implementações ficam em `farol.api` (a camada de cima), em `farol/api/chat/ferramentas.py`, e chamam exatamente `montar_painel_com_visto` e companhia.
- A busca nos alertas (`RecuperadorDeTrechos`) e a indexação ficam **dentro** de `farol.chat`, porque só dependem de `dominio` (repositório `TrechoAlertaRepositorio`) e do `Embeddador`.
- **Uma pequena adição ao `mapa`**: `alertas_que_definem_nivel(sessao) -> dict[int, frozenset[str]]` (id do alerta → códigos de território para os quais ele rege o nível), reaproveitando `calcular_niveis`. Sem mudança de comportamento. O `worker` passa esse mapa à indexação, para o `chat` nunca importar o `mapa`.

### D2. Agente com ferramentas (LangChain 1.x)

- `create_agent(model, tools=[…4 ferramentas…], system_prompt=…, middleware=[…])`, com saída estruturada `RespostaDoModelo` (`texto`, `assuntos`, `situacao`). Modelo criado com `init_chat_model(nome, **argumentos_do_modelo(nome, configuracoes))`, o mesmo caminho do classificador, com variável própria (`LLM_CHAT`) e chave própria opcional.
- **Ferramentas** (todas só de leitura, todas com o argumento `pais` validado pelo código contra os países que **o código** detectou, ver D6): `consultar_nivel(pais)`, `consultar_visto(pais)`, `consultar_postos(pais)`, `buscar_nos_alertas(consulta, pais?)`. Cada uma devolve ao modelo um texto curto delimitado (dado, nunca instrução) e guarda o **artefato estruturado** (`response_format="content_and_artifact"`) que o código usa para montar cartões e citações.
- **Limites duros**: `ModelCallLimitMiddleware` (4 chamadas por pergunta), `ToolCallLimitMiddleware` (6 chamadas de ferramenta), `recursion_limit`, e o prazo de 20 s (D8).
- **Fallback de modelo**: `ModelFallbackMiddleware` (modelo alternativo em `LLM_CHAT_ALTERNATIVO`) no agente, porque o `bind_tools` precisa de um modelo de chat de verdade; `with_fallbacks` só nas chamadas sem ferramentas (por exemplo, o embedding). Tudo atrás de uma função (`criar_modelo_do_chat`), então a escolha não vaza. A decisão e o motivo estão no item seguinte.
- **Decisão sobre o fallback (Fase 1, T026; revista após a aprovação da fase)**: o plano B do agente é o **`ModelFallbackMiddleware`** (langchain 1.4.7), não `with_fallbacks`. O teste de 15 minutos mostrou que os dois funcionam: `create_agent` aceita `principal.with_fallbacks([reserva])`, o `bind_tools` passa pelo embrulho e o alternativo responde quando o principal falha. Mas `create_agent` tipa o modelo como `BaseChatModel` e `with_fallbacks` devolve um `RunnableWithFallbacks`, o que obrigaria a um `cast` para passar no mypy; o middleware deixa o principal como um `BaseChatModel` de verdade e dispensa o `cast`. A fachada (`criar_modelo_do_chat`) continua sendo o único ponto que sabe disso, então a escolha não vaza. O `with_fallbacks` fica só para chamadas sem ferramentas (como o embedding). Teste de regressão: `backend/tests/unidade/chat/test_modelo_com_fallback.py`.
- **Contingência sem modelo** (constituição VII: "o chat MUST continuar respondendo se o provedor principal falhar"): se não houver modelo disponível (nenhum configurado, todos fora do ar), o chat entra no **modo só registros**: um roteador de palavras-chave no código (nível, visto/isento/RG, consulado/embaixada/telefone/endereço) identifica o assunto, o `ResolvedorDePaises` identifica o país, e a resposta é feita só de cartões, com o aviso "o assistente está fora do ar; aqui estão os dados do painel". Sem conseguir inferir, o aviso de indisponibilidade da spec (FR-029). Esse mesmo roteador é a "rede lexical" da trava (D5).

### D3. Indexação e a regra de 15 minutos

- **Quando**: um *varredor* idempotente, `indexar_pendentes`, roda **a cada 5 minutos** (`INDEXACAO_INTERVALO_MINUTOS`) num segundo executor do APScheduler (`ThreadPoolExecutor(1)` próprio), de modo que **não espera** a coleta de postos (~45 min, que ocupa o executor único de coleta). Também roda ao fim de `coletar --alertas`, de `reclassificar` e pelo comando novo `python -m farol.worker indexar [--tudo|--status]`. Com `COLETAS_AUTOMATICAS=false` o worker segue ocioso (não agenda o varredor); a indexação é então manual, e o `quickstart.md` diz como.
- **O que indexa**: alertas com `confirmado_hash`, classificação vigente `ok`, página lida e `removido_em` nulo (os que valem para o nível). Por alerta, compara `(alerta_hash, modelo_embedding, classificacao_id)` com o que há no índice, **e `indexado_em` com `classificacao.classificado_em`**: igual e em dia = nada a fazer; mudou = apaga os trechos antigos e grava os novos na **mesma transação**; alerta removido ou sem confirmação = apaga os trechos. O hash por alerta (`Alerta.hash`/`confirmado_hash`) é o que evita reindexar o que não mudou.
- **Situação de vigor**: metadado `em_vigor_para` (códigos para os quais o alerta rege o nível, vindo do `mapa` pelo `worker`) e `paises` (códigos citados na classificação), mantidos pelo varredor sem reembedar quando só eles mudam. **A fonte da verdade na hora da resposta é a ferramenta de nível** (o mesmo `define_nivel` do painel): o trecho é rotulado "em vigor" ou "anterior" comparando seu `alerta_id` com o alerta que rege o nível do país, então um descompasso de poucos minutos do metadado nunca vira uma afirmação errada.
- **Saída imediata**: a consulta de recuperação faz `JOIN` com `alerta` exigindo `removido_em IS NULL` e `confirmado_hash = trecho.alerta_hash`. Alerta que saiu da lista ou mudou de conteúdo **some das respostas no mesmo instante**, antes mesmo do varredor passar; o prazo de 15 minutos fica garantido com larga folga para a saída. Para a entrada, o pior caso é o intervalo do varredor (5 min) + o tempo de vetorizar poucos trechos (segundos) + a coleta/classificação, que é anterior e independente.
- **Se a vetorização falhar** (sem cota, rede): o alerta fica sem trechos, o varredor tenta de novo no ciclo seguinte e o erro vai para o log; o chat continua com os outros alertas e a busca textual cobre quem ainda não tem vetor (D4).
- **Modelo e dimensão por vetor, e a regra de comparação.** Cada trecho guarda `modelo_embedding` e `dimensoes`. A recuperação vetorial **só olha as linhas cujo modelo e dimensão são os configurados** (`EMBEDDINGS_MODELO`, `EMBEDDINGS_DIMENSOES`). Um alerta que ainda não tem trechos do modelo configurado (troca de modelo em andamento, ou falha ao vetorizar) **entra pela busca textual**, de modo que nunca se compara um vetor de um modelo com o da pergunta de outro, e nenhum alerta some do chat durante a troca.
- **Trocar de modelo.** O varredor refaz sozinho, no ciclo seguinte, o que não tem vetor do modelo configurado; para fazer **agora e de uma vez**, com relatório, existe o comando **`python -m farol.worker reindexar`** (indexar tudo com o modelo configurado e, só depois de cada alerta ficar completo, apagar os vetores dos outros modelos; `--manter-antigos` não apaga). `indexar --status` avisa quando o índice tem modelo ou dimensão diferente do configurado. Contrato em [contracts/indexacao-e-comandos.md](contracts/indexacao-e-comandos.md).

- **Trechos e a classificação (`trecho_alerta.classificacao_id`)**: nenhum fluxo da 001 apaga classificações. A coleta com conteúdo novo cria **outra** linha (outro hash) e o trecho antigo deixa de valer pela regra `alerta_hash = confirmado_hash`. O `reclassificar` regrava a **mesma linha** (mesmo `id` e hash, só `classificado_em` avança), então comparar o `classificacao_id` não basta: o trecho ficaria com `paises` da classificação anterior. Decisão: (1) a FK é `ON DELETE CASCADE`, então apagar uma classificação apaga os trechos dela na hora; (2) o varredor trata como defasado o alerta cujo trecho tem `indexado_em < classificado_em` e o refaz (`TrechoAlertaRepositorio.alertas_a_indexar`), no ciclo de 5 minutos, e o `reclassificar` roda o varredor ao terminar; (3) a saída continua imediata pelo `JOIN` com `confirmado_hash`. Pior caso de defasagem do metadado: um ciclo (5 min), dentro dos 15 minutos.

### D4. Trechos e recuperação

- **Fatiamento**: trechos de **alguns parágrafos** (alvo de ~1.000 caracteres, máximo ~1.600, com um parágrafo de sobreposição). Os parágrafos vêm de `html_corpo` (`<p>`, `<li>`, títulos), mas cada trecho é gravado como **intervalo `[inicio, fim)` de `alerta.texto`**, não como cópia: o "Ver trecho" mostra `alerta.texto[inicio:fim]`, de forma que é, por construção, **o texto original, caractere a caractere** (SC-002), e some junto se o alerta mudar (o hash não bate). Parágrafo que não se acha no `texto` cai no fatiamento por frases.
- **Recuperação** (`RecuperadorDeTrechos`): se o código detectou países, filtra `paises && {países, soberano}`; ordena por distância de cosseno entre o vetor da pergunta e o do trecho; devolve os **4 melhores** (limite de caracteres no total). Sem país, busca em todos e o chat avisa que pode não ser do país que a pessoa quer. O alerta que rege o nível do país é sempre incluído se tiver algum trecho com similaridade mínima.
- **Plano B textual**: `to_tsvector('portuguese', …) @@ plainto_tsquery(…)` com o mesmo filtro, quando o embedding da pergunta falha. Estatisticamente é pior, mas é determinístico, testável sem vetores e custa zero.
- **Alertas que não são de viagem** (por exemplo, fraudes): entram no índice sem países, rotulados assim; nunca definem nível.

### D5. Trava no código e citações montadas pelo código

A resposta do modelo nunca chega à pessoa sem passar por estas etapas, todas no código:

1. **Rede de assuntos**: o modelo declara `assuntos`; um verificador léxico independente olha o **texto** da resposta e a pergunta (palavras de nível, visto/isento/RG, posto/consulado/telefone/endereço). Se qualquer um dos dois pede uma ferramenta que não foi chamada, a resposta é **descartada** e o agente é rodado de novo **uma vez** com `tool_choice` forçado para a ferramenta que faltou (`ModelRequest.tool_choice` em um middleware). Falhou de novo: resposta de contingência só com cartões.
2. **Cartões e citações do código**: os dados dos cartões (nível, visto, posto) e todas as citações (título, data, link, "Ver trecho" como fatia do texto original) saem dos **artefatos das ferramentas**, nunca do texto do modelo. O texto do modelo é só prosa de ligação. Os links da resposta são só os das citações; nada de link ou HTML escrito pelo modelo.
3. **Verificador de prosa**: lista de proibições aplicada ao texto do modelo, conforme os registros usados: "seguro", "tranquilo", "sem riscos", "recomendo viajar" e afins; categoria de visto citada na prosa diferente da do cartão; "isento" com cartão "sem informação"; "RG" em Malvinas; "nível X" diferente do cartão. Violou: descarta e usa a contingência de cartões.
4. **País só o que o código detectou** (D6).

### D6. Entender a pergunta: país, seguimento e histórico

- **Resolução de países feita pelo código**, antes do modelo, com a mesma lógica de nomes da busca (nomes, `rotulo_busca`, `termos_busca`, sem acento, `titulo_cita`/`nomes_para_titulo` do `mapa`, usados pelo `ResolvedorDePaises` da camada de cima). Nome ambíguo (Congo, Guiné) ou ausente, sem país em **mensagens anteriores da própria pessoa**: o código responde com a pergunta de volta, **sem chamar o modelo** (poupa cota).
- **Pergunta de lista (sem país específico).** O código também reconhece a *intenção de lista* ("quais países", "em que países", "para onde posso ir", "onde preciso de visto", "lista de países…") por palavras-chave. Sem país detectado **e** com intenção de lista, o chat **não pergunta de volta**: libera ao modelo só as ferramentas de lista (D15). Sem país e sem intenção de lista, continua a pergunta de volta. Com país detectado, as ferramentas de lista ficam fechadas (a pergunta é sobre aquele país).
- **Histórico**: o navegador manda as últimas 6 mensagens. Elas entram no prompt como **um bloco delimitado de dados não confiáveis**, **nunca como mensagens com papel de assistente** (um cliente adulterado não pode fingir "o chat já disse X"). Para continuidade de país, o código só olha as mensagens com papel de **pessoa**. Nenhum fato vem do histórico: tudo é buscado de novo nas ferramentas a cada resposta (FR-020).
- **Ferramentas só aceitam países da lista do código**; se o modelo pedir outro (por injeção, por exemplo), a chamada é recusada e conta como tentativa suspeita nas contagens.

### D7. Defesa contra injeção de instruções (FR-023)

Camadas: delimitadores neutralizados como o classificador já faz (`<<<`/`>>>` trocados em texto externo); texto dos alertas, observações de visto e histórico só entram como **dados dentro de blocos**; ferramentas só de leitura e restritas a países do código; saída estruturada validada; prosa verificada (D5); links e citações do código; limites de chamadas e de tempo; histórico sem papéis forjáveis. Testes: alertas de teste com frases de comando ("ignore as instruções…"), histórico adulterado e perguntas com tentativas de mudar o papel; critério: as regras de linguagem não são violadas (SC-006, SC-007, SC-016). **A suíte determinística do CI usa modelo falso**, então ela prova que o *código* segura o que o modelo disser; se o *modelo real* obedece ou não à injeção é medido na avaliação com modelo real, fora do CI.

### D8. API: POST com SSE, prazo de 20 s e limites

- **Rota**: `POST /api/v1/chat`, `operation_id` `perguntarAoChat`. Corpo: `{pergunta (1 a 500 caracteres), historico (até 6 itens: papel + texto até 1.500 caracteres)}`. Resposta: `text/event-stream` com eventos `progresso`, `resposta` e `erro` (ver [contracts/openapi.yaml](contracts/openapi.yaml)).
- **Streaming: sim, só de progresso e do resultado final, não de tokens.** A trava (D5) pode **descartar e refazer** a resposta; mostrar tokens ao vivo exporia texto que depois seria jogado fora. O progresso ("identificando o país…", "buscando nos alertas…", "consultando o nível…", "montando a resposta…") vem dos pontos reais do pipeline e atende ao FR-027. Usa-se o SSE nativo do FastAPI 0.162 (`response_class=EventSourceResponse`, que funciona com POST); no cliente, `fetch` + leitor de `ReadableStream`. O prazo de **20 s** vale no servidor (`anyio.fail_after`) e no cliente (`AbortController`, 20 s + folga de 2 s).
- **Antes do stream** (resposta JSON normal): `422` validação (pergunta vazia, longa demais, histórico inválido, não conta nos limites); `429` com `Retry-After` e `{codigo: "limite_por_hora"|"limite_do_dia", volta_em}`; `503` `{codigo: "chat_desligado"}` quando `CHAT_HABILITADO=false`. **Depois de iniciado**, qualquer falha vira o evento `erro`.
- **Limites**: janela deslizante de 60 min por IP (`request.client.host`, que já é o IP real resolvido por `IpReal`), **na memória** do processo (a produção roda 1 processo; recomeçar do zero num reinício é aceitável e é o que mantém IP fora do banco); **teto global de 500 por dia** (dia em horário de Brasília) num contador do **banco**, que sobrevive a reinício, com `UPDATE … SET perguntas = perguntas + 1 WHERE perguntas < 500 RETURNING` (atômico) para reservar a vaga. **Falha por indisponibilidade ou estouro de tempo devolve a vaga nos dois contadores** (FR-026b). Ordem: valida o corpo → reserva a vaga do IP → reserva a vaga do dia (se falhar, devolve a do IP) → roda.
- **Contagens anônimas** (`contagem_chat`, ver data-model.md): perguntas, recusas, "não encontrei", cartões só de registros (contingência), limites atingidos, falhas de serviço, estouros de tempo, travas acionadas, país fora da lista pedido pelo modelo, uso de cada ferramenta. Sem texto, sem IP, sem sessão. O texto das perguntas e respostas **não vai a log nenhum** (logs só com códigos de evento).
- **Pegadinha que o plano trata**: o contador de versão dos dados (`infra/versao.py`) sobe a cada escrita via ORM e **invalidaria o cache de leitura a cada pergunta** se as contagens do chat o disparassem. Solução: `abrir_sessao(..., versiona=False)` para as sessões que só mexem em contagens (e testes de que o cache de `/mapa` continua valendo depois de uma pergunta).
- **Privacidade da instrumentação**: `LANGSMITH_TRACING=false`/`LANGCHAIN_TRACING_V2=false` fixos no ambiente do compose e um teste que falha se algum rastreamento externo estiver ligado. (O pacote `langsmith` está instalado como dependência do LangChain e, se alguém ligar a variável, enviaria perguntas para fora.)

### D9. Caddy, CORS e proxy

- **CORS por rota**: um despachante fino escolhe o `CORSMiddleware` pelo caminho: `/api/v1/chat` → métodos `["POST"]`, cabeçalhos `["Content-Type"]`; qualquer outro → o atual (`["GET"]`, sem cabeçalhos). Mesmas origens, sem credenciais. Testes: preflight do POST em `/chat` passa; preflight de POST em `/mapa` continua recusado.
- **Caddy**: o `Caddyfile` ganha um *snippet* com o `reverse_proxy` e dois blocos `handle`: `handle /api/v1/chat` com `request_body { max_size 16KB }`, **sem `encode`** e com `flush_interval -1` (o SSE não pode ficar retido em buffer nem comprimido), e `handle` (o resto) como hoje, com **1 KB** e `encode`. Dimensionamento do corpo: pergunta de 500 caracteres + 6 mensagens (3 × 500 + 3 × 1.500 caracteres) no pior caso de acentos (2 bytes por caractere em português) + JSON ≈ **13 KB**; 16 KB dá folga e o Pydantic impõe o limite exato por campo. O `write` do servidor está em 30 s, acima dos 20 s do chat. `verificar-caddy.sh` ganha: POST de 2 KB em `/mapa` → 413; POST de 10 KB em `/chat` → passa; POST de 20 KB em `/chat` → 413.
- **Limites existentes**: o limite geral de 120 pedidos/min por IP continua valendo para o chat, na frente do limite próprio. O `IpReal` e o `PROXY_CONFIAVEL` não mudam.
- **Compressão do SSE**: o `GZipMiddleware` do Starlette já ignora `text/event-stream` (conferido).

### D10. Frontend

- **Pasta nova** `frontend/src/funcionalidades/chat/` (organização por funcionalidade): `BotaoDoChat`, `Chat` (gaveta no celular, painel no desktop), `ListaDeMensagens`, `MensagemDoChat`, `Citacao` (com o "Ver trecho" recolhido: `button` com `aria-expanded`), `Cartoes` (reaproveitam `SecaoVisto`, `Posto` e o bloco de nível do painel, para o texto ser **idêntico** ao do painel), `CaixaDePergunta`, `AvisoFixoDoChat`, `useChat` (máquina de estados, histórico em memória, prazo de 20 s, "Nova conversa") e o consumo do SSE em `servicos/api/chat.ts` (o cliente atual só faz GET). Componentes não chamam a API: recebem tudo de `useChat`.
- **Estado**: o aberto/fechado do chat entra no reducer (`chatAberto`), como `painelRecolhido`; o histórico fica no hook, montado no nível de `Tela` (assim fechar o chat não apaga a conversa; recarregar a página apaga). **Nada em `localStorage`.**
- **Convivência** (ver [contracts/chat-ui.md](contracts/chat-ui.md)): botão no canto inferior direito, deslocado por CSS quando o painel do país está aberto; no desktop, o chat é um painel à direita e, com o painel do país aberto, **o painel do país é exibido como a barra compacta da 002 enquanto o chat está aberto, sem mudar o estado** (`painelRecolhido` continua como estava; ao fechar o chat tudo volta); no celular, o chat é uma gaveta sobre a metade de baixo (como já faz o painel do país hoje, que também cobre a legenda enquanto aberto). Nada de `position: fixed` novo fora dos padrões já usados (`absolute` dentro do contêiner `h-dvh`, z-index acima do painel).
- **Acessibilidade**: `role="dialog"` não modal com `aria-labelledby`; foco vai ao campo de pergunta ao abrir e volta ao botão ao fechar; `Esc` fecha o chat (sem competir com o `Esc` do painel e dos diálogos existentes, que já checam `[role="dialog"]`); região `aria-live="polite"` para o progresso e para a resposta nova; botões de 44 px (`min-h-11`); respeita `prefers-reduced-motion` (sem transições de entrada); 360 px sem rolagem horizontal; contraste AA com os tokens de cor existentes.
- **Tipos**: gerados de `contracts/openapi.yaml` (a v1.2 completa). O script `gerar-tipos` passa a ler o contrato da 003. Os eventos do SSE têm esquemas próprios no contrato, e o cliente os valida em tempo de execução (nada de `any`).

### D11. Gabarito e testes

- **Arquivo versionado** `backend/tests/gabarito/chat/gabarito.yaml` com **60 perguntas, pelo menos 5 de cada tipo** (conteúdo de alertas, nível, visto, postos, seguimento, sem resposta nos dados, fora do escopo, injeção, histórico adulterado) e o comportamento esperado de cada uma (formato em [contracts/gabarito.md](contracts/gabarito.md)). Alertas de teste: textos públicos do Itamaraty exportados do banco local por um script (`ferramentas/exportar_alertas_para_gabarito.py`) para `backend/tests/fixtures/chat/alertas.json`, como a 001 fez com as páginas salvas.
- **No CI (determinístico, sem rede, sem modelo real)**: (1) recuperação com vetores pré-calculados: o alerta esperado entre os 4 primeiros em **pelo menos 90%** das perguntas de conteúdo; (2) ferramenta correta chamada, com um **modelo falso roteirizado** por pergunta; (3) trava: um modelo falso que "esquece" a ferramenta é refeito com a ferramenta obrigatória; (4) recusas e "não encontrei"; (5) citações e "Ver trecho" idênticos ao `alerta.texto[inicio:fim]`; (6) verificador de prosa; (7) injeção por alerta e por histórico; (8) contingência só com cartões; (9) regras de linguagem (sem alerta ≠ seguro, sem informação de visto ≠ isento, Malvinas sem RG) nas respostas montadas.
- **Fora do CI**: `uv run poe avaliar-chat` roda as 60 perguntas contra o modelo real (precisa da chave do chat e do banco com os alertas de teste), e imprime o relatório (acertos por tipo, recuperação, violações). Não bloqueia o CI.
- **TDD**: testes antes do código, como na 001 e na 002. Sem rede nem LLM real (constituição II).
- **CI e imagem**: o serviço de PostgreSQL do job `backend` passa a ser o da pgvector (1.3 acima).

### D12. Configuração (variáveis novas, nomes reais do padrão do projeto)

`CHAT_HABILITADO` (padrão `true`), `LLM_CHAT`, `LLM_CHAT_ALTERNATIVO`, `GOOGLE_API_KEY_CHAT`, `EMBEDDINGS_MODELO` (padrão `google_genai:gemini-embedding-001`), `EMBEDDINGS_DIMENSOES` (768), `CHAT_LIMITE_POR_HORA_POR_IP` (20), `CHAT_LIMITE_POR_DIA` (500), `CHAT_TEMPO_MAXIMO_SEGUNDOS` (20), `CHAT_PERGUNTA_MAX_CARACTERES` (500), `CHAT_HISTORICO_MENSAGENS` (6), `CHAT_TRECHOS_POR_PERGUNTA` (4), `INDEXACAO_INTERVALO_MINUTOS` (5). Todas em `Configuracoes` (pydantic-settings) e no `.env.example`; segredos como `SecretStr`. Em produção, com `CHAT_HABILITADO=true`, são obrigatórios os limites positivos e `GOOGLE_API_KEY_CHAT` (quando algum modelo do chat é do Google); o chat nunca usa a chave da coleta. O `docs/deploy.md` recomenda também definir `LLM_CHAT`.

### D13. Operação em servidor pequeno (estimativas)

| Processo | Memória em repouso (estimativa) |
|---|---|
| PostgreSQL (com pgvector) | 150 a 250 MB |
| API (FastAPI + LangChain carregado) | 250 a 350 MB |
| Worker | 200 a 300 MB |
| Caddy | ~30 MB |
| **Total** | **~0,7 a 1 GB**; recomendo **2 GB ou mais** na hospedagem. Com `bge-m3` local, somaria 2,5 a 3 GB, razão da escolha da seção 1.2. |

Um processo da API atende o chat sem fila: cada pergunta passa a maior parte do tempo esperando rede (modelo e embedding), sem CPU. Cinco perguntas simultâneas (SC-013) cabem no `async`; o trabalho de banco é pouco e roda em *threadpool*.

### D14. O que NÃO muda

Nenhuma rota, DTO, regra ou cor da 001 e da 002; os testes de contrato da 002 continuam passando (o contrato completo passa a ser o da 003, com um teste de que a parte da 002 não mudou); o cache de leitura e o contador de versão ficam como estão; `GET` continua somente leitura em todas as outras rotas (o `POST` existe só em `/chat`).

---

### D15. Perguntas de lista: "quais países…?" (acréscimo aprovado em 01/11)

- **Ferramentas novas**, ambas de leitura, sem argumento livre: `listar_paises_por_nivel(nivel)` com `nivel ∈ {nao_viajar, evitar, sem_alerta, nao_verificado}`, e `listar_paises_por_visto(situacao, so_rg)` com `situacao ∈ {isento, visto_na_chegada, autorizacao_eletronica, visto_exigido, outra_situacao, sem_informacao}` e `so_rg` (verdadeiro só com `isento`). Os argumentos são enums validados pelo código.
- **Mesmas funções do mapa e dos vistos.** Um Protocol novo, `ConsultaDeListas`, implementado na `api` com `farol.mapa.montar_mapa` (nível já resolvido de cada território, nome, tipo, `atualizado_em`, `desatualizado`) e `farol.vistos.montar_vistos_do_mapa` (situação, `aceita_rg`, `coletado_em`, `desatualizado`, fonte). Filtra por **países** (`tipo` = país; dependências, Kosovo e Malvinas não entram), ordena por nome e corta em 50. É exatamente o que o filtro da legenda do globo mostra para o mesmo nível ou categoria; um teste de integração compara, para cada nível e categoria, a lista do chat com `GET /mapa` e `GET /vistos` filtrados do mesmo jeito.
- **Regras que a lista herda**: "sem alerta" lista com a ressalva do FR-010 (acrescentada pelo código em `avisos`) e nunca vira "seguro"; "não verificado" aparece como categoria própria; a lista de visto traz Wikipédia (CC BY-SA, fonte não oficial), data do dado, `desatualizado` e a recomendação de conferir com o consulado; "sem informação de visto" é uma categoria própria, nunca isento; as Malvinas nunca estão na lista do RG porque dependências não entram nas listas. Não existe ferramenta nem lista de "países seguros", e **cruzar critérios** ("sem alerta e sem visto") é recomendação de destino: o roteador de intenção devolve `recusa` com a explicação e a oferta das listas separadas.
- **Cartão `lista`** (contrato `CartaoDeLista`): critério em texto legível, países `{codigo, nome}`, `total`, `exibidos`, `truncada`, fonte e data. Montado pelo código; o modelo escreve só a frase de apresentação. O verificador de prosa ganha a regra **"país citado no texto tem de estar nos dados desta resposta"** (nos cartões, nos artefatos ou na pergunta), o que também pega o modelo citando país de cabeça fora de uma lista.
- **Trava**: pergunta de lista sobre nível exige `listar_paises_por_nivel`; sobre visto, `listar_paises_por_visto` (a rede lexical de D5 ganha as palavras de lista: "quais países", "para onde", "onde posso ir"). Contagens anônimas novas: `ferramenta_lista_nivel`, `ferramenta_lista_visto`, `listas_truncadas`.
- **Custo**: cada pergunta de lista faz as mesmas consultas fixas do `/mapa` e do `/vistos` (o painel já as faz), sem N+1.

## 4. Riscos e como ficam cobertos

| Risco | Cobertura |
|---|---|
| Cota gratuita do embedding ou do modelo menor do que o esperado | Isolamento do chat (1.3), teto de 500/dia, limite duro de chamadas por pergunta, busca textual como plano B, contingência só com cartões, e a checagem da cota real no `quickstart.md` antes de abrir ao público |
| Modelo ignora a trava ou escreve algo proibido | A trava, o verificador de prosa e as citações são **código**; no pior caso, a resposta vira cartões |
| Troca da imagem do PostgreSQL altera ordenação de texto | **Conferido**: `postgres:18` = `18-trixie` e o pgvector fixo é `0.8.7-pg18-trixie` (mesma base, arm64). Mesmo assim, o `quickstart.md` confere a versão de ordenação do volume existente e reconstrói índices só se houver diferença; backup antes (já é regra do `docs/deploy.md`) |
| SSE retido pelo proxy ou comprimido | `flush_interval -1`, sem `encode` na rota, teste no `verificar-caddy.sh` |
| Contagens do chat invalidando o cache de `/mapa` | `versiona=False` + teste |
| Vetores do gabarito desatualizados | Hash do texto na fixture e teste que falha mandando regerar |
| Chave do chat vazar para log | `SecretStr`; testes de segurança existentes ganham o chat; rastreamento externo desligado e testado |
| Estimativas de memória erradas | Marcadas como estimativa; medir na VM (item do `quickstart.md`) |
