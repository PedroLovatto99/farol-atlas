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
| `nome_pt` | `text` | Nome em português; para dependência, no formato "Nome (País)". |
| `tipo` | `enum` | `pais`, `dependencia`, `neutro`. |
| `soberano_codigo` | `text` FK → `territorio.codigo`, nulo | Obrigatório se `tipo = dependencia`. Também usado por Kosovo (→ `RS`) e Malvinas (→ `AR`). |
| `na_lista_itamaraty` | `bool` | `true` para os 198. Um teste exige exatamente 198. |
| `tem_bandeira` | `bool` | `false` para Taiwan (FR-033). |
| `observacao` | `text`, nulo | Texto curto do FR-030, FR-034, FR-035 (Kosovo, Malvinas, Taiwan, Saara Ocidental, Antártida, dependências). |
| `observacao_no_topo` | `bool` | `true` quando o painel do soberano abre com a observação no topo (Kosovo, Malvinas). |
| `posto_responsavel_id` | `int` FK → `posto.id`, nulo | Só para país sem posto próprio e com posto indicado. |
| `sem_posto_indicado` | `bool` | `true` quando não há posto próprio nem responsável (hoje, Líbia; FR-014). |
| `icone_latitude`, `icone_longitude` | `numeric(8,5)`, nulos | Ponto dentro do território onde fica o ícone "país sem posto" (FR-018). Preenchido na carga a partir do ponto representativo da maior parte do território, calculado pelo script de geometria. Nulo para países com posto. |

Regras: territórios `neutro` não têm nível e não abrem painel (FR-016, FR-032). `tipo = pais` e `soberano_codigo` nulo, exceto Kosovo e Malvinas, que existem como desenho apontando para o soberano. Seed: `dados/postos/*.csv` (países e responsáveis), mais `dados/territorios/observacoes.yaml` (observações e regras especiais) e o `territorios.geojson` (dependências e neutros).

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

Data de referência para "mais recente": `coalesce(modificado_em, publicado_em)` (FR-007b).

## classificacao

Uma por `(alerta, hash)`: o resultado de classificar aquele conteúdo.

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `int` PK | |
| `alerta_id` | `int` FK | |
| `alerta_hash` | `char(64)` | Hash no momento da classificação. A classificação é **vigente** quando é igual a `alerta.hash`. |
| `status` | `enum` | `ok`, `falhou`. |
| `e_alerta_de_viagem` | `bool`, nulo | Nulo se `falhou`. `false` não afeta o mapa (FR-007a). |
| `modelo` | `text` | Ex.: `google_genai:gemini-3.6-flash`. |
| `erro` | `text`, nulo | Motivo da falha (resposta inválida, ISO fora do conjunto, tempo esgotado). |
| `classificado_em` | `timestamptz` | |

UNIQUE `(alerta_id, alerta_hash)`. Um alerta sem classificação vigente com `status = ok` está **pendente**.

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

## Estados e transições

```text
alerta:  novo ──(hash muda)──▶ alterado ──▶ classificacao nova ──▶ vigente
         visto na lista ──(some, coleta completa)──▶ removido ──(volta)──▶ ativo
classificacao: [sem classificacao vigente] pendente ──▶ ok | falhou ──(próxima rodada)──▶ ok | falhou
execucao_coleta: iniciada ──▶ finalizada(completa) | finalizada(incompleta, com motivo)
```

## Regra do nível (serviço `mapa`)

Entrada: territórios, classificações vigentes, alertas ativos (`removido_em` nulo), última execução completa.

```text
nivel(territorio t):
  se nunca houve execução completa:                  → nao_verificado       (FR-002)
  candidatos(t) = itens de classificações vigentes ok, e_alerta_de_viagem, alertas ativos,
                  que citam t
                  + se t é dependência: os que citam t.soberano             (FR-031)
                  + alertas pendentes cujo título cita t pelo nome          (FR-008)
  se candidatos vazio:                                → sem_alerta
  mais_recente = máx por coalesce(modificado_em, publicado_em);
                 empate → o de nível mais grave (nao_viajar > evitar > normalizada) (FR-007b)
  se mais_recente é pendente:                         → nao_verificado
  se mais_recente.nivel_pais = normalizada:           → sem_alerta, sem regiões   (FR-007)
  se mais_recente.nivel_pais não é nulo:              → esse nível; regiões = as do item, exceto normalizada
  senão (só regional):                                → sem_alerta; regiões = as do item, exceto normalizada
```

- Uma região só gera destaque quando seu nível é mais grave que a cor do país **ou** quando o país não tem nível geral (FR-004). O filtro (FR-027) usa o nível da região.
- Alerta cuja página não foi lida mas é "o mesmo" (mesma `url` e mesma `publicado_em` da lista, e hash conhecido): mantém a classificação vigente (FR-008a). Se for novo ou mudou: pendente.
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
