# Contrato do arquivo de geometria

O script `backend/scripts/gerar_geometria.py` (derivado de `prototipos/mapa/montar_dados.py`) gera, só quando as regras de território mudam, dois arquivos versionados no repositório:

- `frontend/public/geo/territorios.geojson`: o desenho, descrito abaixo;
- `dados/territorios/territorios.json`: o seed das dependências (`codigo`, `nome_pt`, `soberano_codigo`, `codigo_bandeira`, `identidade_do_soberano`, `na_lista_itamaraty`) e os pontos dos ícones dos países sem posto (`icones_sem_posto`: `codigo`, `latitude`, `longitude`).

O geojson: O frontend o busca uma vez; o nível de cada feição vem de `GET /mapa`, pelo `codigo`.

## Origem

Natural Earth 10m, países, versão "ponto de vista do Brasil" (`ne_10m_admin_0_countries_bra`), simplificada com mapshaper na precisão `0.0005` (para o Vaticano não sumir). O pré-processamento (comando `mapshaper` completo) está no cabeçalho do script e cria as propriedades `nome` (`ADMIN`), `iso` (`ISO_A2_EH`), `soberano` (`SOVEREIGNT`) e `a3` (`ADM0_A3`, usado como código das ilhas que dividem o código ISO com o país).

## Propriedades de cada feição

| Propriedade | Tipo | Significado |
|---|---|---|
| `codigo` | string | Código próprio do território (igual a `territorio.codigo`). Para neutro: o código original, só para depuração. |
| `soberano` | string \| null | País soberano (dependências, Kosovo→`RS`, Malvinas→`AR`). |
| `tipo` | `pais` \| `dependencia` \| `neutro` | Neutro não responde a toque nem tem nível (FR-016, FR-032). |
| `titulo` | string | Nome exibido; dependência como "Nome (País)". |
| `zoom` | string | Grupo de enquadramento (feições com o mesmo `zoom` formam a caixa; usa-se a maior parte do território). |

## Regras aplicadas pelo script (spec, "Regras do mapa")

| Regra | Requisito |
|---|---|
| 198 países do Itamaraty selecionáveis, incluindo o Brasil | FR-029 |
| Kosovo (`XK`) como dependência da Sérvia com identidade do soberano: mesmo `zoom` do soberano, observação no topo | FR-030 |
| Dependências apontam para o soberano e usam a própria bandeira | FR-031 |
| Guiana Francesa (`GF`) separada da França (recorte geográfico), como dependência da França; está na lista do Itamaraty | FR-031 |
| Porto Rico (`PR`) como dependência dos Estados Unidos ("Porto Rico (Estados Unidos)"), com bandeira própria; está na lista do Itamaraty (atendido por Miami) | FR-031 |
| Antártida, Saara Ocidental e áreas sem soberania reconhecida: `neutro` | FR-032 |
| Taiwan (`TW`) como dependência da China, sem bandeira; está na lista do Itamaraty | FR-033 |
| Malvinas (`FK`) como dependência da Argentina com identidade do soberano: mesmo `zoom` do soberano, observação no topo (hoje o script as trata como neutras: **mudar**) | FR-034 |
| Ilhas que dividem o código com o país (Clipperton/FR, ilhas australianas/AU) viram dependência à parte | protótipo |

## Testes do arquivo

1. Os 198 países do Itamaraty têm ao menos uma feição `tipo = pais` com o seu `codigo`.
2. Nenhuma feição `tipo = pais` ou `dependencia` tem `codigo` fora de `territorio` (seed), e vice-versa.
3. Todo `soberano` existe e é `pais`.
4. `FK` não é `neutro`; `EH`, `AQ` são.
5. O arquivo tem tamanho abaixo de um limite fixado na primeira geração (regressão de simplificação).
