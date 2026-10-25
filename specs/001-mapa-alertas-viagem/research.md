# Pesquisa (Fase 0): Mapa de alertas de viagem para brasileiros

Este documento registra as decisões técnicas, o que foi conferido nos arquivos do repositório e na web, e os riscos que o plano herda. As escolhas de tecnologia vêm do pedido do plano; aqui constam só as conferências, as lacunas encontradas e as decisões novas. Versões não citadas aqui são "a estável vigente na instalação", fixadas em `uv.lock` e `package-lock.json`.

## 1. Conferências feitas

| Item | Resultado | Fonte |
|---|---|---|
| MapLibre GL JS 6 existe | Sim. A 6.0.0 saiu em 22/07/2026; a série 6.x chegou à 6.8.0. **WebGL2 passou a ser obrigatório** e o pacote é **só ESM** (sem UMD). | [newreleases.io](https://newreleases.io/project/github/maplibre/maplibre-gl-js/release/v6.0.0), [malagis.com](https://geo.malagis.com/maplibre-gl-js-v6-mandatory-webgl-and-esm-only.html) |
| Globo no MapLibre | Existe desde a série 5; a 6.x segue corrigindo detalhes do globo (ex.: camadas desenhadas duas vezes perto do antimeridiano, corrigido na 6.1.0). | mesmas fontes |
| `gemini-3.6-flash` | Existe e é o código estável da API Gemini. Uma fonte de terceiros cita um "Gemini 3.7 Flash" de 13/08/2026, **sem confirmação oficial** achada; o padrão fica como pedido e o modelo é configurável. | [ai.google.dev](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash), [chatbase.co](https://www.chatbase.co/blog/gemini-3-6-flash) |
| `init_chat_model("google_genai:…")` | Formato com prefixo de provedor é o documentado. O pacote `langchain-google-genai` está na série 4.x (usa o SDK `google-genai`). | [reference.langchain.com](https://reference.langchain.com/python/langchain-google-genai) |

O protótipo (`prototipos/mapa/template_globo.html`) usa MapLibre **5.24.0 via UMD**. Na migração para a 6 isso muda para import ESM pelo Vite; a API de globo usada no protótipo (`setProjection({ type: "globe" })`, `Marker` com `opacityWhenCovered`, `fitBounds`) deve ser revalidada na primeira tarefa do mapa.

## 2. Lacunas encontradas nas fixtures do gov.br

Estas são as descobertas mais importantes desta fase. Todas afetam o plano.

### R1. Endereço e telefone de plantão não estão nas páginas de posto salvas

`posto_1.html` (Embaixada em Amã) e `posto_2.html` (Consulado-Geral em Milão) são as **páginas iniciais** dos postos. O texto principal não contém endereço, telefone nem link `tel:`. Na página de Milão, o endereço e os contatos estão atrás de abas que são **outras páginas**: `…/consulado-milao/emergencias` e `…/consulado-milao/fale-conosco-1`. A página de Amã, no HTML estático, nem mostra o menu de abas.

- **Decisão:** a coleta mensal de postos é **melhor esforço** e é a **última fase** das tarefas, para não bloquear as histórias P1 a P5. Ela segue os links "Emergências", "Fale com…" e "Sobre…" de cada posto (mesmo host, sujeitos ao robots.txt), extrai o que achar e grava `NULL` no resto. A spec já cobre isso (posto sem endereço: o painel mostra a cidade; o link do Google Maps leva à cidade), e o SC-006 só exige o link do Google Maps.
- **Consequência:** é preciso salvar como fixtures as subpáginas de pelo menos 2 ou 3 postos (embaixada e consulado) antes de escrever os extratores. A primeira tarefa da coleta de postos é medir quantos dos 209 postos têm endereço e telefone extraíveis; o resultado vira um relatório da execução, não uma falha.
- **Risco aberto:** se a cobertura for baixa, o painel mostrará "endereço ainda não cadastrado" para muitos postos (como no protótipo). Não bloqueia a entrega, mas deve ser dito ao usuário.
- **Cobertura medida (T125, rodada real de 25/10/2026, cerca de 45 min):** 160 de 199 páginas lidas. Dos 209 postos, **76 (36%) ficaram com endereço, 56 (27%) com telefone de plantão e 29 com os dois**. As 39 páginas não lidas foram por `robots.txt` inacessível ou proibido, erro de conexão (hosts `*.itamaraty.gov.br` antigos) e 404. Os postos restantes ficam com o painel em "ainda não cadastrado", como previsto.
- **Qualidade (amostra de 30 endereços):** quase todos são endereços de rua completos, sem menus nem avisos. Em 8 dos 76 sobrou um rótulo de título da página colado no começo ou no fim ("Jurisdição", "Endereço Postal", "Postal Address", "Emergências Consulares", "Embassy of Brazil", "Consulate General of Brazil", "Endereço da chancelaria", "Address"). O extrator passou a cortar exatamente esses rótulos (`sem_rotulos_de_pagina`) e a limpeza foi reaplicada ao banco sem nova coleta (0 restantes). Ainda há endereços que não são endereço (postos 207, 114, 67 e 34 pegaram manchetes e títulos de notícia); não foram cortados e aguardam decisão.

### R2. Paginação da lista de alertas (resolvida)

`lista_alertas.html` traz 18 itens e **nenhum link de próxima página**. Hoje a lista é uma página só.

- **Decisão (do usuário):** a lista é **completa quando não há link de próxima página**. A coleta só vale como **incompleta** se existir um link de próxima página e ele falhar (erro, bloqueio, robots.txt, formato inesperado). O extrator segue o link de próxima página, quando houver, até acabar.
- **Teste:** um caso com a fixture atual (sem link, lista completa) e um caso sintético com link de próxima página que falha (lista incompleta). Se o gov.br passar a paginar, o extrator já funciona; nenhuma fixture da página 2 é necessária agora.
- **Como reconhecer o link:** o seletor de "próxima página" é definido junto com o caso sintético, a partir do padrão de paginação do Plone (`b_start:int`) e de rótulos como "Próximo"; é o único ponto a revisar se a lista crescer e passar a paginar de verdade.

### R3. A lista dá só a data de publicação; a modificação exige abrir o alerta

A lista traz `dd/mm/aaaa` (publicação). A data e hora de **última modificação** (`dateModified` do JSON-LD) só existe na página do alerta. Exemplo real: `alerta_2` (Oriente Médio) foi publicado em 04/07/2026 e **modificado em 17/08/2026**.

- **Decisão:** toda rodada abre a página de **todos** os alertas da lista (para calcular o hash e ler `dateModified`), com pausa de 2 s. É a leitura que também alimenta o critério de 70% de páginas lidas. Com algumas dezenas de alertas, são alguns minutos por dia.
- **Otimização futura (não nesta feature):** requisições condicionais (ETag / If-Modified-Since) ou ler com menos frequência os alertas muito antigos.

### R4. Itens da lista que não são alertas de viagem

A lista mistura alertas de viagem com avisos de fraude, orientações e notícias (ex.: "Alerta de novas fraudes… EUA", categoria "Apoio a Cidadãos"; "Participação de brasileiros em conflitos armados"). A categoria da página (`#form-widgets-categoria`) ajuda, mas não basta ("Orientações para Brasileiros em Viagem aos EUA" é viagem).

- **Decisão:** a decisão é do classificador (campo `e_alerta_de_viagem`), com a categoria como entrada. O caso de teste de fraude (`alerta_3`) deve resultar em "não é alerta de viagem".

### R5. Links da tabela de repartições apontam para subdomínios antigos

A tabela (`reparticoes.html`, 198 linhas de dados) liga países a postos, e os links dos postos são do tipo `http://islamabade.itamaraty.gov.br/pt-br/`, enquanto as páginas de posto usadas pelos testes são `https://www.gov.br/mre/pt-br/embaixada-ama`. O mapeamento posto → página do gov.br **não está nos CSVs**.

- **Decisão:** a coleta de postos parte do link da tabela, segue os redirecionamentos e registra a URL final em `posto.url_gov_br`. O `robots.txt` é consultado **por host** (cada host novo carrega o seu). Se o link não resolver para uma página `www.gov.br/mre/pt-br/…`, o posto fica sem contato e entra no relatório.

## 3. Decisões de arquitetura

### D1. Camadas do backend (import-linter)

```text
api   worker          (topo: entradas HTTP e agendador)
mapa  coleta  classificacao   (casos de uso; independentes entre si)
dominio           (modelos ORM, enums, repositórios, regras puras)
infra             (configuração, banco, HTTP, relógio, logs)
```

- Contratos do import-linter: `layers` (de cima para baixo) e `independence` entre `mapa`, `coleta` e `classificacao`. Cada módulo expõe uma interface pública em `__init__.py`; os contratos proíbem importar o que não é exportado por ela.
- **Decisão:** os repositórios ficam em `dominio` (único lugar que fala SQL), junto com os modelos. Os serviços de `coleta`, `classificacao` e `mapa` os usam. O `worker` orquestra coleta → classificação.
- **Alternativa rejeitada:** um repositório por módulo. Triplicaria a configuração de sessão e quebraria a regra "um só lugar" do banco.

### D2. DTOs e OpenAPI

- DTOs Pydantic só na camada `api`; os serviços devolvem dataclasses imutáveis, e as rotas os convertem.
- **`/docs` e `/redoc` só em desenvolvimento**, controlados pela variável de ambiente `API_DOCS_HABILITADA` (padrão `false` no código; `true` no `.env.example` de desenvolvimento). A constituição v1.0.1 (princípio III) exclui a documentação automática da proibição de gerar HTML, desde que fique desligada em produção. `/api/v1/openapi.json` é servido sempre, e é dele que o `openapi-typescript` gera os tipos. Um teste confirma que, com a variável desligada, `/docs` e `/redoc` respondem 404.

### D3. Nível de cada território (regra de domínio, no `mapa`)

Implementa FR-002, FR-007, FR-008, FR-008a, FR-031 e FR-040. O algoritmo está em `data-model.md`. Pontos que o plano fixa:

- A regra roda em Python sobre linhas já carregadas (sem consulta por país).
- **Dependências:** o pedido diz que "cada dependência aponta para o país soberano e o frontend só busca o nível por esse código". A spec (FR-031) manda a dependência seguir o **mais recente entre o seu alerta e o do soberano**. Para não errar quando a dependência tem alerta próprio, o backend calcula e entrega o nível **por território** (`codigo` próprio), e o arquivo de geometria carrega `codigo` e `soberano`. O frontend continua só buscando o nível pelo código da feição, sem lógica de herança.
- **Alerta pendente cujo título não cita país conhecido** (ex.: "Oriente Médio"): nenhum país muda de nível, porque não há como saber quais são. É um risco residual herdado do pedido. Mitigação: `/saude` informa o número de alertas pendentes e o log registra cada um.

### D4. Classificador

- Entrada: título, data, categoria e texto. Saída estruturada (`with_structured_output`): `e_alerta_de_viagem` e uma lista de `{codigo, nivel_pais, regioes[{nome, nivel}]}`. Níveis permitidos: `evitar`, `nao_viajar`, `normalizada`. `nivel_pais` pode ser nulo (alerta só regional, FR-007).
- Validação depois do modelo: códigos fora do conjunto permitido invalidam a resposta inteira (pedido); níveis fora do enum falham no Pydantic.
- **Texto externo é dado, não instrução** (princípio VIII): o texto do alerta vai entre delimitadores, o modelo não tem ferramentas, e nada do que o texto diz altera o schema. Um texto com "ignore as instruções" só pode produzir uma saída válida do schema ou falhar.
- Temperatura 0. Reclassifica só quando o hash do alerta muda. O modelo usado fica gravado em cada classificação.
- **Custo e cota:** o volume é de poucos alertas novos por semana, então o plano gratuito da API deve bastar (princípio VII). Dados enviados são públicos. Confirmar a cota vigente ao configurar a chave.
- **Cota conferida em 25/10/2026** (páginas de preços e limites da API Gemini, atualizadas em 15/10/2026): o Gemini 3.6 Flash tem camada gratuita no nível Standard, para entrada e saída; o lote (Batch) não está disponível na camada gratuita. Os números exatos de requisições por minuto e por dia da camada gratuita não estão na documentação: aparecem só no AI Studio, na conta de quem usa. A classificação de verdade rodou com este modelo sobre os 18 alertas do histórico, todos com status `ok`. O teste com o Ollama não foi feito: não havia Ollama rodando no computador.

### D5. Coleta

- Cliente HTTP único, usado pelos dois coletores: `requests.Session`, User-Agent `FarolAtlas/… (contato: <CONTATO_COLETA>)`, `protego` por host, pausa configurável (2 s), detecção de verificação humana / HTTP 403/429 (as funções de `ferramentas/testar_coleta.py` são a base). Verificação humana ou bloqueio **para a execução inteira** e grava o motivo (princípio IV).
- Hash SHA-256 de `título + texto` com espaços normalizados. Extração: o `extrair_alerta` da ferramenta (JSON-LD primeiro, rótulo "Publicado em" como reserva).
- Remoção: `removido_em` só é preenchido quando a execução é completa. Uma volta do alerta à lista limpa o `removido_em`.
- **Confirmação (FR-040, SC-008):** o que a coleta lê vai para as colunas comuns de `alerta`; só ao fim de uma execução **completa** o serviço copia a leitura para as colunas `confirmado_*`, e só estas entram no cálculo do nível. Uma coleta incompleta nunca altera nível, mesmo que tenha lido alertas novos ou alterados. A ordem no worker é: coletar → (se completa) confirmar → classificar.
- Agendamento: APScheduler em processo próprio, `BlockingScheduler`, fuso `America/Sao_Paulo`, cron diário às 06:17, mensal para os postos. Na partida, roda se a última **tentativa** tiver mais de 20 h. Uma falha recente não é repetida antes do dia seguinte (a spec tolera 3 dias).
- Comando de desenvolvimento: `python -m farol.worker coletar --alertas | --postos`.

### D6. Geometria

- Entrada: Natural Earth 10m `ne_10m_admin_0_countries_bra`, simplificada com mapshaper a 0.0005. O `montar_dados.py` recebe um GeoJSON já com os campos `nome`, `iso` e `soberano`; esse **pré-processamento não está documentado** no repositório e passa a constar no README do script.
- O script atual precisa de **ajustes para a spec**: as Malvinas (`FK`) estão em `NEUTRO` e devem virar parte da Argentina com observação (FR-034); o Taiwan precisa seguir a regra de dependência (FR-033); Kosovo já vira Sérvia com observação; Antártida e Saara Ocidental seguem neutros. Os alertas de exemplo no fim do script saem (os dados reais vêm da API).
- Saída: `frontend/public/geo/territorios.geojson`, versionada. Propriedades por feição: `codigo`, `soberano`, `tipo` (`pais` | `dependencia` | `neutro`), `titulo`, `zoom` (grupo de enquadramento). Um teste confere a contagem (198 países do Itamaraty selecionáveis) e que nenhum país fica sem desenho.

### D7. Frontend

- **Organização por funcionalidade** (princípio III): `mapa`, `painel`, `busca`, `legenda` (legenda e filtro) e `aviso`. Estado compartilhado (território selecionado, posto expandido, níveis marcados) em um `useReducer` + contexto no topo da aplicação, sem biblioteca global.
- **Mapa atrás de interface própria** (`MapaProps`, ver `contracts/mapa-props.md`): o adaptador MapLibre é o único arquivo que importa `maplibre-gl`. Marcadores continuam como elementos do DOM do MapLibre (como no protótipo), com os ícones do Tabler renderizados por portal do React. São no máximo cerca de 270 marcadores e só aparecem a partir do zoom 3.5.
- **Diferenças em relação ao protótipo, a corrigir na implementação:** (a) o protótipo tem a seção "Notícias" no painel, que está **fora do escopo** da spec; (b) o clique no marcador seleciona só o primeiro país do grupo; (c) o marcador do posto responsável de um país sem posto só aparece no zoom alto; a spec (FR-018h) exige que o ícone em destaque apareça em qualquer zoom; (d) não há busca, filtro por nível nem destaque de posto.
- **Acessibilidade:** a legenda é texto com amostra de cor; região mais grave tem borda **e** item de legenda; o ícone em destaque é maior e com contorno; `prefers-reduced-motion` zera animações do painel e do mapa (`duration: 0`).
- **Zoom dos ícones:** 3.5 (resolve o ponto deixado em aberto na clarificação). Enquadramento máximo 5.5; o posto responsável só entra se a largura total ficar abaixo de 180° de longitude.
- **"Sobre" e "Sobre as fronteiras deste mapa"** abrem como modal acessível (foco preso, Esc fecha), sem roteador. A explicação sobre Saara Ocidental e Antártida (áreas neutras, sem painel) fica só ali.

### D8. Painel: uma requisição por seleção

O painel pede `GET /paises/{codigo}` quando o usuário seleciona um país. A constituição v1.0.1 (princípio III) permite isso: a proibição de "uma requisição por país" vale para o carregamento do mapa, que recebe tudo numa única chamada a `/mapa`. Alternativa avaliada: colocar tudo em `/mapa`. Rejeitada porque endereços e telefones mudam pouco e crescem com a cobertura da coleta de postos.

### D9. Testes

- Backend: pytest; PostgreSQL de teste por serviço `postgres-teste` do compose (perfil `teste`), com porta ligada só ao `127.0.0.1`. A coleta usa as fixtures; o classificador usa modelo falso da LangChain (`GenericFakeChatModel`) e há um teste de contrato do schema de saída. `/mapa` e `/paises/{codigo}` têm teste de limite de consultas (princípio III), com tetos de 6 e de 8 consultas, respectivamente.
- Frontend: Vitest + Testing Library, com a API simulada (MSW ou `fetch` falso). O adaptador do mapa é substituído por um falso; a lógica (cor, filtro, busca, enquadramento, marcadores visíveis) fica em funções puras.
- Teste de arquitetura: `lint-imports` roda junto com `pytest` no comando de verificação.

### D10. Verificação local (CI fica fora)

Um comando por lado:

- `cd backend && uv run poe verificar` → ruff (lint e formato), mypy, lint-imports, pytest, pip-audit.
- `cd frontend && npm run verificar` → eslint, prettier --check, tsc, vitest, npm audit.

`poethepoet` é uma dependência de desenvolvimento nova (executor de tarefas multiplataforma, para não depender de `make` no Windows). Os princípios I e VIII dizem que nenhuma mudança é aceita com falha de verificação e que dependências são conferidas "a cada mudança". Sem CI, isso depende de disciplina.

- **Decisão (do usuário):** um hook `pre-push` **opcional** em `.githooks/pre-push`, versionado, que chama os dois comandos. Ativação por desenvolvedor: `git config core.hooksPath .githooks`. A documentação de ativação entra no README **quando o usuário pedir o README**; até lá fica no `quickstart.md`. O hook não substitui a CI, que entra depois chamando os mesmos comandos.

### D11. Docker e ambiente

- Serviços: `postgres`, `migracao` (Alembic + seed idempotente, termina), `api`, `worker`, `frontend`. `api` e `worker` esperam `migracao` terminar com sucesso.
- Em desenvolvimento, os dois bancos publicam porta **só em `127.0.0.1`** (`5432` no banco de desenvolvimento e `5433` no de teste), para abrir o banco com um cliente local; nenhuma porta de banco escuta em outro endereço. Um teste lê o `docker-compose.yml` e falha se isso mudar. A constituição v1.0.2 (VIII) permite isso em desenvolvimento; em produção os bancos ficam só na rede interna do Docker, sem porta publicada (o compose de produção está fora desta feature).
- `WATCHFILES_FORCE_POLLING=true` (uvicorn `--reload`) e `server.watch.usePolling` (Vite), por causa do Windows.
- Ollama no host: `http://host.docker.internal:11434`; no Linux/Oracle isso exige `extra_hosts: host.docker.internal:host-gateway` (já previsto no compose).
- Imagens multi-arquitetura (`python:3.13-slim`, `postgres:18`, `node` LTS); nenhuma dependência de runtime sem wheel arm64. `shapely`/`pycountry` ficam em um grupo de desenvolvimento do `uv`, fora da imagem.
- `.gitattributes` com `* text=auto eol=lf`. Os arquivos `LF → CRLF` que o Git avisou nos commits anteriores deixam de ser reescritos.

## 4. Riscos que o plano aceita

| # | Risco | Efeito | Tratamento |
|---|---|---|---|
| 1 | Endereço e telefone pouco extraíveis (R1) | Muitos postos sem contato no painel | Melhor esforço, relatório de cobertura, fallback para a cidade |
| 2 | A lista de alertas passar a paginar (R2) | O extrator nunca viu um link de próxima página real | Regra fixada: sem link = completa; link que falha = incompleta; teste sintético cobre o caso |
| 3 | Alerta pendente sem país no título (D3) | Mapa mantém níveis antigos | Contador em `/saude`, log, retentativa diária |
| 4 | Mudança de layout do gov.br | Extração quebra | Fixtures + testes apontam o que mudou; execução incompleta preserva os dados |
| 5 | Gemini 3.6 Flash substituído ou cota alterada | Classificação falha | Modelo por variável de ambiente; Ollama como alternativa de desenvolvimento |
| 6 | Servidor em nuvem cai na verificação humana | Sem coleta em produção | O script de teste de coleta já documenta rodar no servidor; execução é interrompida e registrada |
| 7 | Sem CI | Verificação depende de disciplina | Comando único + hook `pre-push` opcional em `.githooks` |
