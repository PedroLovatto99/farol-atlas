# Contrato: mudanças na interface do mapa e na legenda (modo "Vistos")

Muda `specs/001-mapa-alertas-viagem/contracts/mapa-props.md`. A biblioteca do mapa continua isolada atrás de `MapaProps`: só o adaptador importa `maplibre-gl` (princípio III), e o adaptador não sabe o que é um alerta nem um visto.

## `MapaProps`

| Antes (001) | Depois (002) |
|---|---|
| `TerritorioDesenhado.nivel: NivelId` | `TerritorioDesenhado.preenchimento: Preenchimento` |
| (cor calculada no adaptador a partir do nível) | cor e padrão calculados **fora** do adaptador, por funções puras (`preenchimentoDeAlerta`, `preenchimentoDeVisto`) |

```ts
/** Como um território é pintado. O adaptador só executa. */
export interface Preenchimento {
  /** Cor de base, em hex. */
  cor: string;
  /** "rg": listras sobre a cor de base ("Isento, entrada com RG"); null: cor lisa. */
  padrao: "rg" | null;
}

export interface TerritorioDesenhado {
  codigo: CodigoTerritorio;
  preenchimento: Preenchimento;
  /** Sempre null no modo Vistos (FR-025). */
  bordaRegional: BordaRegional | null;
  /** Filtro da legenda do modo ativo, calculado fora do mapa. */
  esmaecido: boolean;
}
```

O restante de `MapaProps` (postos, seleção, câmera, callbacks) **não muda**. Área neutra continua pela cor própria (`tipo = neutro`), sem `preenchimento`.

## Camadas do adaptador

| Camada | Tipo | Regras |
|---|---|---|
| `paises` | `fill` | `fill-color` = `["get","cor"]`; `fill-opacity` esmaece pelo filtro (como hoje) |
| `padrao-rg` (nova) | `fill` | filtro `["==",["get","padrao"],"rg"]`; `fill-pattern` = `"listras-rg"`; mesma opacidade da camada `paises` |
| `fronteiras`, `regional`, `selecao`, `linha-responsavel` | `line` | inalteradas; `regional` fica vazia no modo Vistos porque nenhuma feição tem `borda_regional` |

**Imagem `listras-rg`:** 16×16 px, RGBA, listras diagonais (45°) em azul-marinho escuro `#0B3A52`, opacas, com 3 px de largura a cada 8 px, sobre a cor de base `#00B1DF` do "Isento" (a imagem inclui a base, porque `fill-pattern` substitui o preenchimento; contraste listra × base 4,8:1). É uma matriz de pixels gerada por função pura (`mapa/padroes.ts`), sem canvas, e registrada com `map.addImage("listras-rg", { width, height, data })` depois do carregamento do estilo. A mesma figura vira o fundo da amostra da legenda (`repeating-linear-gradient` com os mesmos números), e um teste compara os dois.

**Plano B** (se a verificação no globo mostrar que `fill-pattern` não funciona): uma camada `line` `padrao-rg` com `line-dasharray` e `line-color` igual ao "Isento" escurecido, desenhada dentro das feições com RG. A interface (`padrao: "rg"`) não muda.

## Legenda do modo "Vistos"

Chaves da legenda (`ChaveDeVisto`), na ordem de exibição:

| Chave | Rótulo na legenda | Quem entra |
|---|---|---|
| `isento` (pai) | Isento de visto | todos os "Isento", com e sem RG |
| `isento_rg` (subitem) | Isento, entrada com RG | "Isento" com `aceita_rg` |
| `visto_na_chegada` | Visto na chegada | |
| `autorizacao_eletronica` | Autorização ou visto eletrônico | |
| `visto_exigido` | Visto exigido | |
| `outra_situacao` | Outra situação | |
| `sem_informacao` | Sem informação de visto | inclui todo território sem dado |
| (informativo, sem caixa) | Brasil: seu país, sem seção de visto | o Brasil (cor neutra) |

**Filtro (caixa com subitem):** o estado é o conjunto de chaves marcadas, todas ao abrir. Regras puras em `legenda/filtroDeVistos.ts`:

- marcar ou desmarcar `isento` marca ou desmarca também `isento_rg`;
- desmarcar só `isento_rg` esmaece só os "Isento com RG"; `isento` passa a **estado misto**;
- marcar só `isento_rg` com `isento` desmarcado mostra apenas os com RG e esmaece os demais "Isento";
- um "Isento com RG" aparece normal se `isento_rg` está marcado, qualquer que seja o estado de `isento`; um "Isento sem RG" aparece normal se `isento` está marcado (tabela abaixo);
- os outros territórios esmaecem se a chave deles está desmarcada;
- o estado misto é comunicado por `aria-checked="mixed"` e pelo texto "(parcial)", não só por cor;
- o filtro de vistos é **independente** do filtro de alertas (cada modo guarda o seu, em memória).

Tabela de verdade do "Isento":

| `isento` | `isento_rg` | Isento sem RG | Isento com RG |
|---|---|---|---|
| marcado | marcado | normal | normal |
| marcado | desmarcado | normal | esmaecido |
| desmarcado | marcado | esmaecido | normal |
| desmarcado | desmarcado | esmaecido | esmaecido |

Mensagem e botão de "todas desmarcadas" valem para o modo Vistos como no de alertas (FR-028 da 001).

## Linha de fonte e data (FR-029)

Componente `LinhaDaFonteDeVistos`, **fora** da parte recolhível de `LegendaRecolhivel`, só no modo Vistos:

```text
Vistos: Wikipédia (CC BY-SA), fonte não oficial, coletados em 20/10/2026
```

"Wikipédia" é um link para o artigo; a data é a de `coletado_em`. Sem coleta válida: "Vistos: ainda não há dados de visto". Quebra em linhas no celular e não cobre o mapa, o aviso nem o "Sobre". Com dados antigos (FR-029a), o aviso entra em `Aviso`, na área de avisos do site, sem abrir painel.

## Carregamento e erro de `/vistos`

O modo "Vistos" busca `/vistos` sob demanda, ao ser escolhido pela primeira vez (e guarda a resposta na memória). Três situações, que valem também ao escolher o modo de novo depois de um erro:

| Situação | Globo | Legenda |
|---|---|---|
| Carregando | territórios **sem preenchimento** (só as fronteiras) | "Carregando os vistos…" no lugar dos itens; o seletor já mostra "Vistos" |
| **Erro** (rede, 5xx ou resposta fora do contrato) | territórios **sem preenchimento**; **nunca** o cinza | mensagem "Não foi possível carregar os vistos." e o botão "Tentar de novo" (busca outra vez); a linha de fonte mostra "Vistos: dados indisponíveis no momento" |
| Pronto | pintura normal do modo | legenda e linha de fonte completas |

- **Cinza só tem um significado**: "sem informação de visto" (`#AEABA2`). Erro e carregamento nunca o usam, para não afirmar que não há dado quando só falhou a busca.
- Sem preenchimento = `fill-opacity` 0 na camada `paises` (o oceano aparece por baixo); o clique continua abrindo o painel, que tem a sua própria chamada (`GET /paises/{codigo}`, com o `visto` dentro). A verificação de que o clique funciona com opacidade 0 entra no spike da P2; se falhar, usa-se a cor do oceano `#DCE8F2` como "sem pintura".
- Voltar para "Alertas" durante o erro funciona normalmente; o filtro, a seleção e o painel não mudam.
- Testes (Vitest): erro de rede ⇒ mensagem e botão, nenhum território com a cor de "sem informação"; "Tentar de novo" refaz a chamada e, em sucesso, pinta; carregando ⇒ nenhum território cinza.

## Estado (`estado/reducer.ts`)

```ts
modo: "alertas" | "vistos";                // padrão "alertas"; nunca guardado (FR-021)
vistosMarcados: readonly ChaveDeVisto[];   // todas ao abrir; independente de niveisMarcados
vistos: { estado: "nao_pedido" | "carregando" | "erro" | "pronto"; dados?: VistosDoMapa };
```

Ações novas: `trocar-modo`, `alternar-visto`, `marcar-todos-vistos`, `vistos-carregando`, `vistos-carregados`, `vistos-falhou`. Trocar de modo não mexe na seleção, no painel aberto, nos postos expandidos nem na câmera.
