# Contrato: interface do modo daltonismo

Sem mudança na API HTTP, no OpenAPI ou em `esquema.d.ts`. Cores e padrões:
[paletas-e-padroes.md](paletas-e-padroes.md).

## Preferência (`funcionalidades/daltonismo/preferencia.ts`)

```ts
export const CHAVE_DO_DALTONISMO = "farol-atlas:daltonismo";
export function lerPreferenciaDoDaltonismo(): boolean;
export function gravarPreferenciaDoDaltonismo(ligado: boolean): void;
```

| Situação | Resultado |
|---|---|
| Valor guardado `"ligado"` | `true` |
| `"desligado"`, ausente ou qualquer outro valor | `false` |
| `localStorage` ausente ou lança erro, ao ler | `false`, sem erro |
| `localStorage` ausente ou lança erro, ao gravar | Nada acontece; o modo segue valendo na visita |

A outra aba não é avisada: sem ouvinte de `storage`.

## Botão (`funcionalidades/daltonismo/BotaoDoDaltonismo.tsx`)

```ts
interface Props {
  ligado: boolean;
  onAlternar(): void;
}
```

| Item | Regra |
|---|---|
| Elemento | `<button type="button" aria-pressed={ligado}>`; Enter e Espaço vêm do navegador |
| Nome acessível | Sempre "Modo daltonismo"; o estado é o `aria-pressed` |
| Texto visível | "Modo" e "daltonismo" em duas linhas, `text-xs` |
| Estado visual | Ligado: fundo `marinho`, texto branco em negrito e quadradinho marcado. Desligado: fundo branco e quadradinho vazio |
| Tamanho | `min-h-11` |
| Foco | Mesmo contorno do `SeletorDeModo` (`aviso-borda`) |
| Lugar | Grupo da direita do `<header>`, depois do `SeletorDeModo`, que ganha `flex-wrap justify-end` |
| Animação | Nenhuma |

## Estado e props

Em `Tela`:

```ts
const [daltonismo, setDaltonismo] = useState(lerPreferenciaDoDaltonismo);
```

O clique inverte o estado e grava. O valor entra nas dependências do `useMemo` de `territorios`.

| Destino | Mudança |
|---|---|
| `MapaProps` | `daltonismo?: boolean` (sem ele, `false`) |
| `LegendaRecolhivel`, `Legenda`, `LegendaDeVistos` | `daltonismo?: boolean` |
| `Painel` | `daltonismo?: boolean`, usado no selo (`NivelDoPais`) e nas bordas (`Regioes`) |
| `MapaFalso` | Expõe `data-testid="mapa-daltonismo"` |

O padrão `false` nas props e nos parâmetros mantém os chamadores e os testes atuais funcionando.

## Funções puras

```ts
// mapa/tipos.ts
export type PadraoDoPreenchimento = "rg" | "nao_viajar" | "evitar";
// Preenchimento.padrao passa a ser PadraoDoPreenchimento | null

// mapa/cor.ts
export function paletaDe(daltonismo: boolean): Paleta;
export function corDoTerritorio(tipo: string, nivel: NivelId | undefined, daltonismo?: boolean): string;
export function preenchimentoDeAlerta(tipo: string, nivel: NivelId | undefined, daltonismo?: boolean): Preenchimento;
export function preenchimentoDeVisto(tipo: string, situacao: SituacaoNoGlobo | null, aceitaRg: boolean, daltonismo?: boolean): Preenchimento;

// mapa/feicoes.ts
export function montarFeicoes(geometria: Geometria, territorios: readonly TerritorioDesenhado[], modo?: ModoDoGlobo, daltonismo?: boolean): Colecao<PropriedadesDesenhadas>;

// mapa/contorno.ts: CONTORNO_DO_MODO_VISTOS quando modo === "vistos" ou daltonismo
export function contornoDosPaises(modo: ModoDoGlobo, daltonismo?: boolean): Contorno;
// mapa/contorno.ts: { duration: 0, delay: 0 } com movimento reduzido; null sem essa preferência
export function transicaoDoContorno(reduzirMovimento: boolean): { duration: number; delay: number } | null;
```

`preenchimentoDeAlerta` só devolve padrão com o modo ligado e nível `nao_viajar` ou `evitar`. Área
neutra nunca tem padrão, e as cores do neutro e do oceano não mudam.

## Propriedades das feições e camadas

| Propriedade nova | Quando existe | Valor |
|---|---|---|
| `imagem_do_padrao` | Território com padrão | Nome da imagem ([tabela](paletas-e-padroes.md#padrões)) |
| `borda_tracejada` | Modo ligado e `bordaRegional === "evitar"` | `true` |

| Camada | Mudança |
|---|---|
| `padrao-rg` → `padroes` | Filtro `["has", "imagem_do_padrao"]`; `fill-pattern: ["get", "imagem_do_padrao"]`; mesma opacidade |
| `regional` | Filtro passa a excluir feições com `borda_tracejada`; o resto fica igual |
| `regional-tracejada` (nova, logo depois de `regional`) | Filtro `["has", "borda_tracejada"]`; mesma cor, largura e opacidade, mais `line-dasharray: [3, 2]` |

`styleimagemissing` procura o nome numa tabela de imagens e registra a matriz correspondente.

O efeito que aplica o contorno na camada `fronteiras` passa a depender de
`[mapa, modo, daltonismo, reduzirMovimento]`. Antes das cores, ele define `line-color-transition` e
`line-width-transition` com `transicaoDoContorno(reduzirMovimento)`. Com movimento reduzido, a troca
sai sem animação; sem essa preferência, `null` mantém a transição padrão do MapLibre, como hoje. O
`ESTILO` não ganha `transition`.

## O que não muda

Seleção, filtros, painel, câmera, modo do globo, contorno de seleção, linha até o posto responsável, ícones dos postos, textos, neutro e oceano. Alternar não faz pedido à API nem
relê a geometria.
