# Modelo de dados: Requisitos de visto para brasileiros

Banco: o mesmo PostgreSQL 18 da 001, SQLAlchemy 2 (ORM), migração Alembic **`0003_vistos`** (a `0002` é a última da 001). Nomes em português, sem acento; instantes em `timestamptz` (UTC); enums gravados como texto com `CHECK` (o padrão `_enum` de `dominio/modelos.py`). Os modelos e os repositórios ficam em `farol.dominio`; o módulo `vistos` os usa só pela interface pública (`farol.dominio`).

```text
territorio 1───0..1 requisito_visto *───1 coleta_vistos
territorio 1───* mudanca_retida *───1 coleta_vistos
coleta_vistos 1───* item_para_revisao (primeira e última vez em que foi visto)
```

A tabela `territorio` **não muda**. Nenhuma tabela da 001 muda.

## Enums novos (`dominio/enums.py`)

| Enum | Valores |
|---|---|
| `CategoriaDeVisto` | `isento`, `visto_na_chegada`, `autorizacao_eletronica`, `visto_exigido`, `outra_situacao` (a ordem de exigência é a desta lista, de `isento` a `visto_exigido`; `outra_situacao` fica fora dela) |
| `MotivoOutraSituacao` | `rotulo_conhecido` (mapeado de propósito para "Outra situação"), `rotulo_desconhecido` |
| `ResultadoDaColetaDeVistos` | `valida`, `rejeitada`, `adiada`, `falhou`, `bloqueada` |
| `EstadoDaRetencao` | `pendente`, `confirmada`, `rejeitada`, `revertida`, `superada` |
| `TipoDeItemParaRevisao` | `nome`, `rotulo`, `regra` (regra por país a reconfirmar; ver abaixo) |
| `EstadoDoItem` | `pendente`, `resolvido`, `ignorado` |

## coleta_vistos

Uma tentativa de ler o artigo, válida ou não. Só uma coleta `valida` pode mudar o que o site mostra (FR-010).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `int` PK | |
| `iniciada_em` | `timestamptz` | |
| `finalizada_em` | `timestamptz`, nulo | Nulo enquanto roda. |
| `resultado` | `enum` | `valida`: aplicou os dados. `rejeitada`: baixou, mas o formato ou a quantidade de países reconhecidos não passou (nenhum dado muda). `adiada`: edição de menos de 24 h. `falhou`: erro técnico (timeout, 5xx, formato inesperado). `bloqueada`: 403, 429, verificação humana ou `robots.txt` proibindo. |
| `motivo` | `text`, nulo | Obrigatório quando `resultado <> 'valida'`. |
| `linhas_lidas` | `int` | Linhas de dados das três tabelas. |
| `paises_reconhecidos` | `int`, nulo | Códigos distintos do mapa ligados a alguma linha, sem contar os ignorados. Base do critério de 90% (FR-010). |
| `ultima_edicao_fonte` | `timestamptz`, nulo | `dateModified` do JSON-LD (ou o rodapé). |
| `revisao_fonte` | `bigint`, nulo | `wgRevisionId`. |
| `adiamentos_seguidos` | `int` | Quantos `adiada` consecutivos até esta tentativa (inclusive). Depois de 3, coleta mesmo assim. |
| `falhas_seguidas` | `int` | Idem para `falhou`. |
| `aplicadas`, `retidas` | `int` | Países cujos dados mudaram e foram aplicados; países com mudança retida nesta coleta. |
| `html_sha256` | `char(64)`, nulo | Para saber se a página mudou entre tentativas. |

Índice por `iniciada_em`. "Última coleta válida" = a mais recente com `resultado = 'valida'` (por `finalizada_em`).

## requisito_visto

O que o site mostra, **um registro por código de território que tem linha própria na fonte** (ex.: `AR`, `HK`, `SH`, `GB`). Dependências sem linha própria **não** têm registro: a leitura usa o do soberano (FR-013). É o dado **exibido**; a leitura de hoje só o substitui conforme a regra de retenção.

| Coluna | Tipo | Regras |
|---|---|---|
| `territorio_codigo` | `text` PK, FK → `territorio.codigo` | |
| `categoria` | `enum` | |
| `motivo_outra` | `enum`, nulo | `CHECK`: não nulo se, e só se, `categoria = 'outra_situacao'`. |
| `rotulo_original` | `text` | Rótulo(s) como na fonte, normalizados; várias linhas separadas por " / ". Sempre preenchido (FR-003, FR-007). |
| `linhas_fonte` | `jsonb` | Lista das linhas normalizadas que deram este registro: `{tabela, grupo, nome, rotulo, permanencia, notas}`. É o que o hash cobre. |
| `hash_fonte` | `char(64)` | SHA-256 do JSON canônico de `linhas_fonte`. Muda quando **a fonte** muda, nunca por causa do dicionário. |
| `aceita_rg` | `bool` | Regra do RG (`research.md` 3.2). |
| `varia_conforme_motivo` | `bool` | Da lista curada (`regras_por_pais.yaml`). |
| `permanencia_tipo` | `text` | `nenhuma` (a fonte não informa), `padronizada`, `original`, `prazos_divergentes`, `varia_conforme_motivo`. `CHECK` com esses valores. |
| `permanencia_texto` | `text`, nulo | Em português (`padronizada`) ou como na fonte, em inglês (`original`). Nulo nos outros tipos. |
| `observacoes` | `jsonb` | Lista de `{texto, hash, traducao, traduzido_em, modelo}` (uma por linha da fonte com nota; `traducao` nulo se ainda não traduzida). O hash do texto é a chave para não traduzir de novo. |
| `lido_em` | `timestamptz` | **A data do dado exibido** (FR-008): instante da coleta em que este registro foi lido da fonte pela última vez. Uma coleta que confirma o mesmo hash a atualiza; uma retenção não (o país mantém a data antiga). |
| `coleta_id` | `int` FK → `coleta_vistos.id` | A coleta de `lido_em`. |

Regras: `permanencia_tipo in ('padronizada','original')` ⇒ `permanencia_texto` não nulo; os outros tipos ⇒ nulo. A permanência é calculada só da coluna "Allowed stay" da tabela principal (decisão O3).

### Como a leitura resolve o visto de um território

1. Território sem painel (neutro): sem visto. Brasil: `visto = nulo`.
2. `identidade_do_soberano` (Kosovo, Malvinas): usa o registro do **soberano**, e o painel é o dele (sem nota de herança).
3. Há registro com o código do território: usa-o (`origem = proprio`).
4. Dependência sem registro: usa o do soberano (`origem = soberano`, com o nome do soberano para a nota do painel).
5. Sem registro em nenhum dos dois, ou nunca houve coleta válida: `situacao = sem_informacao`.

## mudanca_retida

Mudança que a fonte trouxe e que ainda não vale no site (FR-010a). O país mantém o `requisito_visto` antigo, com a data antiga.

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `int` PK | |
| `territorio_codigo` | `text` FK | |
| `coleta_id` | `int` FK | A coleta que leu o valor retido (a mais recente que o viu). |
| `estado` | `enum` | `pendente`, `confirmada`, `rejeitada`, `revertida`, `superada`. |
| `hash_fonte_lido` | `char(64)` | Hash da fonte no valor retido. A rejeição vale enquanto a fonte mantiver este hash. |
| `candidato` | `jsonb` | O registro completo que seria aplicado (categoria, motivo, rótulo, linhas, RG, permanência, observações). Confirmar grava este conteúdo em `requisito_visto`. |
| `categoria_exibida`, `categoria_lida` | `enum`, nulo | Para o resumo e o log. **Nulo = "sem informação"**: `categoria_exibida` nula quando o país ainda não tem `requisito_visto` (ausência de requisito); `categoria_lida` nula quando a fonte deixou de trazer linha para o país. |
| `aceita_rg_exibido`, `aceita_rg_lido` | `bool` | Para reter também o "passar a aceitar só o RG". |
| `criada_em`, `resolvida_em` | `timestamptz` | |

Índice único parcial: no máximo **um** registro `pendente` e **um** `rejeitada` por território.

### Estados e transições

```text
             (leitura traz mudança menos exigente / passa a aceitar RG)
 [nada] ───────────────────────────────────────────────────────────▶ pendente
 pendente ── dono confirma ───────────────────────────────▶ confirmada (aplica o candidato)
 pendente ── dono rejeita ────────────────────────────────▶ rejeitada
 pendente/rejeitada ── a fonte voltou ao valor exibido ───▶ revertida (automática)
 pendente/rejeitada ── a fonte mudou para outro valor ────▶ superada (e a decisão recomeça)
 rejeitada ── a fonte mantém o mesmo hash lido ───────────▶ rejeitada (nada novo; não retém de novo)
 pendente ── a fonte mantém o mesmo hash lido ────────────▶ pendente (só atualiza `coleta_id`)
```

## item_para_revisao

Tudo o que espera revisão do dono, em uma tabela só: nomes e rótulos que a coleta não reconheceu (tipos `nome` e `rotulo`; FR-012, FR-012a, FR-012b) e regras por país a reconfirmar (tipo `regra`). Nunca descartados em silêncio.

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | `int` PK | |
| `tipo` | `enum` | `nome`, `rotulo` ou `regra`. Para `regra`, `valor` é o código do território. |
| `valor` | `text` | Normalizado. `UNIQUE (tipo, valor)`. |
| `contexto` | `jsonb` | Onde apareceu: lista de `{tabela, nome_na_fonte}` (para rótulos, os países). Para `regra`: `{hash_esperado, hash_lido, texto}` (o texto novo da nota, para o dono decidir). |
| `primeira_vez_em`, `ultima_vez_em` | `timestamptz` | |
| `estado` | `enum` | `pendente`, `resolvido` (uma coleta posterior reconheceu o item: automático), `ignorado`. |
| `motivo_ignorar` | `text`, nulo | `CHECK`: `estado = 'ignorado'` exige `tipo = 'nome'` e motivo não vazio. **Rótulo e regra não podem ser ignorados.** |
| `resolvido_em` | `timestamptz`, nulo | |

Depois de cada coleta válida, todo item `pendente` que **não** foi visto naquela coleta (porque o dicionário passou a reconhecê-lo ou a linha saiu da fonte) vira `resolvido`. Um item `resolvido` que reaparece volta a `pendente`; um item `ignorado` continua `ignorado` (foi decisão do dono, com motivo).

## O que o dicionário guarda (arquivos, não tabelas)

`backend/src/farol/vistos/dicionarios_yaml/` (formato em `contracts/dicionario-de-rotulos.md`):

| Arquivo | Conteúdo |
|---|---|
| `rotulos.yaml` | 20 rótulos atômicos → categoria (ou "outra situação"), com `aceita_rg`, exemplo da fixture e, quando preciso, o `motivo` da regra geral de categoria. |
| `nomes.yaml` | Nome da fonte (em inglês) → código do mapa, ou `ignorar` com motivo. |
| `regras_por_pais.yaml` | Códigos com `varia_conforme_motivo`, `prazos_diferem_por_motivo` e `hash_observacao` (hoje `JM` e `ZM`). |

O conteúdo foi aprovado no levantamento (`research.md`, seção 3) e é escrito na implementação, com um teste por entrada.

## Volume e consultas

~230 registros em `requisito_visto`, algumas dezenas de linhas em `coleta_vistos` por ano, poucos itens pendentes. Consultas de leitura, com número fixo (princípio III): `GET /vistos` = 3 (última coleta válida, territórios, registros); o `visto` de `GET /paises/{codigo}` = 3 (última coleta válida, registros do território e do soberano, território com soberano, um `IN`).
