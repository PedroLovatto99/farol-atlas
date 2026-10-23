# Modelo de dados: Mapa de alertas de viagem para brasileiros

Banco: PostgreSQL 18, acesso por SQLAlchemy 2 (ORM), migrações Alembic. Nomes de tabelas e colunas em português, sem acento. Todos os instantes são `timestamptz` em UTC.

```text
territorio 1───* posto
territorio 1───* nivel_territorio *───1 classificacao *───1 alerta
territorio *───1 posto (posto_responsavel)
execucao_coleta (independente; liga-se aos alertas por data)
```

## territorio

Um lugar selecionável ou desenhável no mapa. Os 198 países do Itamaraty são os de `tipo = pais` com `na_lista_itamaraty = true`.

| Coluna | Tipo | Regras |
|---|---|---|
| `codigo` | `text` PK | ISO-2 (ex.: `BR`) ou o código do Natural Earth para dependências (ex.: `GL`, `TW`, `GF`). Igual a `properties.codigo` da geometria. |
| `nome_pt` | `text` | Nome exibido no painel, em português; para dependência, no formato "Nome (País)". Para Kosovo e Malvinas, o nome do **soberano** ("Sérvia", "Argentina"). |
| `tipo` | `enum` | `pais`, `dependencia`, `neutro`. |
| `soberano_codigo` | `text` FK → `territorio.codigo`, nulo | Obrigatório se `tipo = dependencia`. Kosovo (`XK` → `RS`) e Malvinas (`FK` → `AR`) são dependências com `identidade_do_soberano` (ver "Kosovo e Malvinas", abaixo). |
| `na_lista_itamaraty` | `bool` | `true` para os 198. Um teste exige exatamente 198. |
| `codigo_bandeira` | `text`, nulo | Código da bandeira exibida (flag-icons). País: o próprio código. Dependência: o próprio código (FR-031). **Kosovo e Malvinas: o do soberano (`RS`, `AR`), nunca uma bandeira própria.** Nulo para Taiwan (FR-033). |
| `identidade_do_soberano` | `bool` | `true` só para Kosovo e Malvinas: o painel, o nome e a bandeira são os do soberano, e a observação abre o painel no topo (FR-030, FR-034). `false` para todos os outros. |
| `rotulo_busca` | `text`, nulo | Texto da sugestão na busca; se nulo, vale `nome_pt`. Ex.: "Kosovo (Sérvia)", "Malvinas (Argentina)". |
| `termos_busca` | `text[]` | Outros nomes que também encontram o território. Kosovo: `{Kosovo}`; Malvinas: `{Malvinas, Ilhas Malvinas}`. Vazio nos demais. |
| `observacao` | `text`, nulo | Texto curto do FR-030, FR-034, FR-035 (Kosovo, Malvinas, Taiwan e dependências). Áreas neutras (Saara Ocidental, Antártida) não têm painel nem observação aqui: a explicação delas fica só em "Sobre as fronteiras deste mapa". |
| `posto_responsavel_id` | `int` FK → `posto.id`, nulo | Só para país sem posto próprio e com posto indicado. |
| `sem_posto_indicado` | `bool` | `true` quando não há posto próprio nem responsável (hoje, Líbia; FR-014). |
| `icone_latitude`, `icone_longitude` | `numeric(8,5)`, nulos | Ponto dentro do território onde fica o ícone "país sem posto" (FR-018). Preenchido na carga a partir do ponto representativo da maior parte do território, calculado pelo script de geometria. Nulo para países com posto. |

Regras: territórios `neutro` não têm nível e não abrem painel (FR-016, FR-032). `tipo = pais` implica `soberano_codigo` nulo. Seed: `dados/postos/*.csv` (países e responsáveis), mais `dados/territorios/observacoes.yaml` (observações e regras especiais) e `dados/territorios/territorios.json` (dependências, soberano e ponto do ícone dos países sem posto, gerado por `backend/scripts/gerar_geometria.py`), além de `dados/postos/fonte.yaml` (fonte e data dos dados de postos).

### Kosovo e Malvinas: caso especial das dependências

Kosovo (`XK`) e Malvinas (`FK`) usam o **mesmo mecanismo das dependências**: `tipo = dependencia`, `soberano_codigo` preenchido, nível calculado como "o mais recente entre o alerta próprio e o do soberano" (FR-031). A diferença é `identidade_do_soberano = true`, que muda só a identidade exibida:

| Aspecto | Dependência comum (ex.: Groenlândia) | Kosovo e Malvinas |
|---|---|---|
| Nome no painel | "Groenlândia (Dinamarca)" | "Sérvia" / "Argentina" |
| Bandeira | A própria (`GL`) | A do soberano (`RS` / `AR`), **nunca** uma própria |
| Painel | Dados do soberano, título e bandeira da dependência | **Painel do soberano**, com a observação (FR-030, FR-034) **no topo** |
| Enquadramento do zoom | Grupo da dependência | Grupo do soberano |
| Busca | Encontra "Groenlândia" | Encontra "Kosovo" e "Malvinas" (e "Ilhas Malvinas"); abre o painel do soberano |
| Postos e alertas do painel | Os do soberano (e os da dependência) | Os do soberano (e os do próprio território, se houver) |

Seed (`seed.py`): `XK` com `nome_pt = Sérvia`, `soberano_codigo = RS`, `codigo_bandeira = RS`, `rotulo_busca = Kosovo (Sérvia)`, `termos_busca = {Kosovo}`; `FK` com `nome_pt = Argentina`, `soberano_codigo = AR`, `codigo_bandeira = AR`, `rotulo_busca = Malvinas (Argentina)`, `termos_busca = {Malvinas, Ilhas Malvinas}`. A observação de cada um vem de `dados/territorios/observacoes.yaml`.

## posto

Seed de `dados/postos/postos_brasileiros.csv` (209 linhas); contato preenchido pela coleta mensal.

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `int` PK | Mantém o `id` do CSV. |
| `territorio_codigo` | `text` FK | País do posto (`pais_iso`). |
| `cidade` | `text` | |
| `tipo` | `enum` | `Embaixada`, `Consulado-Geral`, `Consulado`, `Vice-Consulado`, `Escritório de Representação`, `Escritório Comercial`. |
| `latitude`, `longitude` | `numeric(8,5)` | Centro da cidade, não o endereço exato (README dos dados). |
| `na_lista_oficial` | `bool` | Do CSV; `observacao_origem` guarda a coluna `observacao`. |
| `url_gov_br` | `text`, nulo | Página final do posto, depois dos redirecionamentos. |
| `endereco` | `text`, nulo | Melhor esforço (pesquisa R1). |
| `telefone_plantao` | `text`, nulo | Melhor esforço (pesquisa R1). |
| `contato_coletado_em` | `timestamptz`, nulo | Princípio V: fonte e data da coleta de toda informação exibida. |
| `contato_fonte_url` | `text`, nulo | Página de onde saiu o endereço ou o telefone. |

Postos na mesma cidade e coordenada **dividem o ícone** no mapa. Quem agrupa é a API (`/mapa` devolve `grupo` por `latitude,longitude`), para o frontend aplicar FR-018d e FR-018g sem recalcular.

## jurisdicao (sem tabela própria)

`jurisdicao_cumulativa.csv` (60 países) vira `territorio.posto_responsavel_id` na carga. A coluna `posto_responsavel` do CSV é resolvida por cidade (como o `montar_dados.py` já faz, com o alias `Cambera → Camberra`); o que não resolver é erro de seed, não silêncio. Entradas entre parênteses (Líbia) viram `sem_posto_indicado`.

## alerta

Um item da lista de alertas do Portal Consular (histórico).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `int` PK | |
| `url` | `text` UNIQUE | URL canônica da página do alerta. |
| `titulo` | `text` | |
| `texto` | `text` | Corpo normalizado (espaços colapsados). |
| `html_corpo` | `text` | Guardado para reprocessar sem nova coleta. Nunca é inserido no frontend (princípio VIII). |
| `categoria` | `text`, nulo | Ex.: "Brasileiro indo para o exterior". |
| `publicado_em` | `timestamptz` | JSON-LD `datePublished`; reserva: "Publicado em". Se a página não foi lida: data da lista (meia-noite local). |
| `modificado_em` | `timestamptz`, nulo | JSON-LD `dateModified`. |
| `hash` | `char(64)` | SHA-256 de `titulo + texto` com espaços normalizados. |
| `primeira_coleta_em`, `ultima_coleta_em` | `timestamptz` | |
| `removido_em` | `timestamptz`, nulo | Só preenchido numa execução completa (FR-040). Limpo se o alerta voltar à lista. |
| `pagina_lida` | `bool` | `false` quando só se conhece título, link e data da lista (FR-008). |
| `confirmado_execucao_id` | `int` FK → `execucao_coleta.id`, nulo | Última execução **completa** que confirmou este alerta. Nulo = lido só em coleta incompleta: **não vale para o nível** (FR-040, SC-008). Atualizado a cada execução completa em que o alerta continua na lista. |
| `confirmado_hash` | `char(64)`, nulo | Hash da versão confirmada. Nulo quando a página não foi lida na execução que confirmou (alerta novo ou alterado, FR-008). |
| `confirmado_titulo` | `text`, nulo | Título da versão confirmada; é o que identifica o país de um alerta pendente (FR-008). |
| `confirmado_data_ref` | `timestamptz`, nulo | `coalesce(modificado_em, publicado_em)` da versão confirmada (FR-007b); para página não lida, a data da lista. |

As colunas sem prefixo `confirmado_` guardam o que a coleta **leu por último**; as `confirmado_*` guardam o que uma execução **completa** confirmou. Só estas últimas entram no cálculo do nível. Ao fim de uma execução completa, o serviço de coleta copia a leitura atual para as colunas `confirmado_*` de todo alerta presente na lista.

## classificacao

Uma por `(alerta, hash)`: o resultado de classificar aquele conteúdo.

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `int` PK | |
| `alerta_id` | `int` FK | |
| `alerta_hash` | `char(64)` | Hash no momento da classificação. A classificação **vale para o nível** quando `alerta_hash` é igual a `alerta.confirmado_hash`. O serviço classifica o hash lido mais recente, mesmo antes da confirmação, para a classificação já estar pronta quando uma execução completa o confirmar. |
| `status` | `enum` | `ok`, `falhou`. |
| `e_alerta_de_viagem` | `bool`, nulo | Nulo se `falhou`. `false` não afeta o mapa (FR-007a). |
| `modelo` | `text` | Ex.: `google_genai:gemini-3.6-flash`. |
| `erro` | `text`, nulo | Motivo da falha (resposta inválida, ISO fora do conjunto, tempo esgotado). |
| `classificado_em` | `timestamptz` | |

UNIQUE `(alerta_id, alerta_hash)`. Um alerta confirmado sem classificação `ok` para o `confirmado_hash` (inclusive quando `confirmado_hash` é nulo) está **pendente**.

## nivel_territorio

Um item por território citado numa classificação `ok` com `e_alerta_de_viagem = true`.

| Coluna | Tipo | Regras |
|---|---|---|
| `classificacao_id` | `int` FK | |
| `territorio_codigo` | `text` FK | Só códigos de `territorio` (198 países e dependências do mapa). Qualquer outro invalida a classificação (D4). |
| `nivel_pais` | `enum`, nulo | `evitar`, `nao_viajar`, `normalizada`. Nulo = o alerta só tem nível regional para este território. |
| `regioes` | `jsonb` | Lista de `{nome, nivel}` com `nivel` em `evitar`, `nao_viajar`, `normalizada`. Vazia se não há região. |

PK `(classificacao_id, territorio_codigo)`. Um alerta pode ter vários itens (Oriente Médio: IR, IL, LB com "Sul do Líbano", PS com "Faixa de Gaza").

## execucao_coleta

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `int` PK | |
| `tipo` | `enum` | `alertas`, `postos`. |
| `iniciada_em`, `finalizada_em` | `timestamptz` | `finalizada_em` nulo enquanto roda. |
| `paginas_esperadas`, `paginas_lidas` | `int` | Esperadas = itens da lista (alertas) ou linhas da tabela (postos). |
| `lista_lida_inteira` | `bool` | Verdadeiro se não há link de próxima página, ou se todos os links de próxima página foram seguidos com sucesso. Falso se existe um link de próxima página que falhou (R2). |
| `completa` | `bool` | `lista_lida_inteira` **e** `paginas_lidas ≥ 0,7 × paginas_esperadas` **e** pelo menos um alerta (FR-040). |
| `motivo_interrupcao` | `text`, nulo | Ex.: "caiu na verificação humana", "bloqueado (HTTP 429)", "proibida pelo robots.txt". |
| `postos_com_endereco`, `postos_com_telefone` | `int`, nulos | Relatório de cobertura (R1), só para `tipo = postos`. |

"Última coleta completa" = a execução `tipo = alertas`, `completa = true`, com maior `finalizada_em`.

## fonte_dados

Fonte e data dos dados do seed, para o painel mostrar a atribuição dos postos (FR-011a) e a linha se atualizar quando os CSVs mudarem.

| Coluna | Tipo | Regras |
|---|---|---|
| `chave` | `text` PK | `postos` (hoje a única). |
| `fontes` | `jsonb` | Lista de `{nome, url, licenca}`. Hoje: Itamaraty (lista de repartições consulares) e Wikipédia ("List of diplomatic missions of Brazil", licença CC BY-SA). |
| `conferido_em` | `date` | Data em que os dados foram conferidos (hoje 2026-10-21). |
| `carregado_em` | `timestamptz` | Quando o seed gravou o registro. |

Origem: `dados/postos/fonte.yaml`, carregado pelo seed (idempotente, atualiza o registro quando o arquivo muda). Quem atualizar os CSVs de postos atualiza também o `fonte.yaml`. O arquivo guarda ainda o SHA-256 de cada CSV (campo `arquivos`); um teste falha se um CSV mudar sem o `fonte.yaml` ser atualizado (data e hash).

## Estados e transições

```text
alerta:  lido (coleta qualquer) ──(execução completa)──▶ confirmado ──(hash muda em coleta completa)──▶ reconfirmado
         lido em coleta incompleta: não confirma e não muda o nível; o que estava confirmado continua valendo
         novo ──(hash muda)──▶ alterado ──▶ classificacao nova (vale quando o hash é o confirmado)
         visto na lista ──(some, coleta completa)──▶ removido ──(volta)──▶ ativo
classificacao: [sem classificacao vigente] pendente ──▶ ok | falhou ──(próxima rodada)──▶ ok | falhou
execucao_coleta: iniciada ──▶ finalizada(completa) | finalizada(incompleta, com motivo)
```

## Regra do nível (serviço `mapa`)

Entrada: territórios, alertas **confirmados** (`confirmado_execucao_id` não nulo) e ativos (`removido_em` nulo), a classificação de cada um para o seu `confirmado_hash`, e a última execução completa. Alertas lidos só em coleta incompleta **não entram**.

```text
nivel(territorio t):
  se nunca houve execução completa:                  → nao_verificado       (FR-002)
  candidatos(t) = itens de classificações ok (para o confirmado_hash), e_alerta_de_viagem,
                  de alertas confirmados e ativos, que citam t
                  + se t é dependência: os que citam t.soberano             (FR-031)
                  + alertas confirmados pendentes cujo confirmado_titulo cita t pelo nome (FR-008)
  se candidatos vazio:                                → sem_alerta
  mais_recente = máx por confirmado_data_ref;
                 empate → o de nível mais grave (nao_viajar > evitar > normalizada) (FR-007b)
  se mais_recente é pendente:                         → nao_verificado
  se mais_recente.nivel_pais = normalizada:           → sem_alerta, sem regiões   (FR-007)
  se mais_recente.nivel_pais não é nulo:              → esse nível; regiões = as do item, exceto normalizada
  senão (só regional):                                → sem_alerta; regiões = as do item, exceto normalizada
```

- Uma região só gera destaque quando seu nível é mais grave que a cor do país **ou** quando o país não tem nível geral (FR-004). O filtro (FR-027) usa o nível da região.
- Alerta cuja página não foi lida mas é "o mesmo" (mesma `url` e mesma `publicado_em` da lista, e hash conhecido): mantém as colunas `confirmado_*` e a classificação do `confirmado_hash` (FR-008a). Se for novo ou mudou, a execução completa o confirma com `confirmado_hash` nulo: pendente.
- Os alertas listados no painel (`GET /paises/{codigo}`) são **todos** os que citam o território (e o soberano, para dependência), do mais recente ao mais antigo, com o que define o nível marcado (FR-010).

## Validações

| Regra | Onde |
|---|---|
| 198 territórios com `na_lista_itamaraty` | teste de seed |
| Todo `pais_iso` dos CSVs existe em `territorio` | seed (falha ruidosa) |
| `soberano_codigo` obrigatório para `dependencia` | restrição `CHECK` |
| Códigos citados pelo classificador ∈ `territorio` | serviço `classificacao`, antes de gravar |
| `completa` só se `lista_lida_inteira` e ≥ 70% lidas | serviço `coleta`, com teste de borda (69%, 70%) |
| Endereço e telefone sempre com `contato_coletado_em` e `contato_fonte_url` | restrição `CHECK` |
