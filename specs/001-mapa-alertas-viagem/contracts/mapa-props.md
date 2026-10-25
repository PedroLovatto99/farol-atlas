# Contrato do componente de mapa (`MapaProps`)

Princípio III: a biblioteca do mapa fica isolada atrás de uma interface própria. Só o adaptador `frontend/src/funcionalidades/mapa/adaptador-maplibre.tsx` importa `maplibre-gl`. Trocar a biblioteca não pode exigir mudança em `painel`, `busca`, `legenda` nem no estado da aplicação. Testes usam um componente falso que cumpre este mesmo contrato.

## Props (TypeScript, `strict`, sem `any`)

```ts
export type CodigoTerritorio = string;
export type NivelId = "sem_alerta" | "evitar" | "nao_viajar" | "nao_verificado";

export interface TerritorioDesenhado {
  codigo: CodigoTerritorio;      // feição da geometria
  nivel: NivelId;                // já resolvido pelo backend
  bordaRegional: "nao_viajar" | "evitar" | null; // FR-004
  esmaecido: boolean;            // filtro de níveis (FR-025), calculado fora do mapa
}

export interface PostoDesenhado {
  grupo: string;                 // ícone compartilhado (FR-018d)
  cidade: string;                // nome acessível do ícone
  latitude: number;
  longitude: number;
  tipos: TipoPosto[];            // mais de um quando dois postos dividem o ícone
  territorios: CodigoTerritorio[];
}

export interface PaisSemPostoDesenhado {
  territorio: CodigoTerritorio;
  nome: string;                  // nome acessível do ícone
  latitude: number;
  longitude: number;
  responsavel: { latitude: number; longitude: number; grupo: string } | null; // linha tracejada (FR-018)
}

export interface MapaProps {
  territorios: readonly TerritorioDesenhado[];
  postos: readonly PostoDesenhado[];
  paisesSemPosto: readonly PaisSemPostoDesenhado[];

  selecionado: CodigoTerritorio | null;      // contorno de seleção
  grupoEmDestaque: string | null;            // FR-018a: maior, com contorno, à frente; aparece em qualquer zoom (FR-018h)
  gruposDoPainel: readonly string[];         // ícones dos postos que o painel aberto lista: aparecem em qualquer zoom (FR-017)
  reduzirMovimento: boolean;                 // FR-039, FR-018f: sem animação

  onSelecionarTerritorio(codigo: CodigoTerritorio): void;   // toque num país; áreas neutras não chamam (FR-016)
  onSelecionarGrupo(grupo: string): void;                   // toque num ícone (FR-018g): o chamador abre o painel
  onLimparSelecao(): void;

  /** Pedido de câmera. O adaptador só o executa; a regra de enquadramento é uma função pura fora dele. */
  camera: PedidoDeCamera;
}

export type PedidoDeCamera =
  | { tipo: "mundo" }
  | { tipo: "enquadrar"; caixa: [[number, number], [number, number]]; margem: Margem; zoomMaximo: number }
  | { tipo: "garantir-visivel"; latitude: number; longitude: number; margem: Margem }   // FR-018c: só pan, sem mudar o zoom; a margem é a área coberta pelo painel
  | { tipo: "manter" };                                                  // FR-018g: toque no ícone não reenquadra
```

## Regras que o adaptador cumpre

| Regra | Origem |
|---|---|
| Globo 3D, só oceano e países (sem mapa de fundo) | plano |
| Marcadores só a partir do zoom 3.5, exceto: os do painel aberto (`gruposDoPainel`), o posto responsável do país sem posto selecionado, o ícone do país sem posto selecionado e `grupoEmDestaque` | FR-017, FR-018h |
| Toque num ícone de posto chama `onSelecionarGrupo`; toque no ícone de país sem posto chama `onSelecionarTerritorio` | FR-018g |
| O clique num ícone não chega ao mapa (não seleciona o país que está embaixo) | FR-018g |
| Linha tracejada só do país sem posto selecionado até o posto responsável | FR-018 |
| Marcadores do outro lado do globo não aparecem nem recebem toque | protótipo (`opacityWhenCovered`) |
| `garantir-visivel` move o centro apenas se o ponto está fora da área visível, sem alterar o zoom | FR-018c, FR-018h |
| `reduzirMovimento` ⇒ `duration: 0` em qualquer movimento de câmera | FR-039 |
| Toque em área neutra ou oceano não dispara `onSelecionarTerritorio` | FR-016 |
| Kosovo (`XK`) e Malvinas (`FK`): o contorno de seleção e o enquadramento usam o grupo `zoom` do soberano (`RS`, `AR`), que vem das propriedades da geometria; `onSelecionarTerritorio` ainda recebe `XK` ou `FK` | FR-030, FR-034 |
| Ícones: embaixada `building-bank`, consulado `building`, escritório `briefcase`, país sem posto `map-pin-share` com linha tracejada até o responsável | plano |

## O que fica fora do componente (funções puras, testadas à parte)

`calcularEnquadramento` (maior parte do território; inclui o responsável só se a largura < 180° de longitude; zoom máximo 5.5), `planejarCamera` (decide se `garantir-visivel` precisa mover; o ponto do outro lado do globo nunca está visível), `corDoTerritorio`, `territorioEsmaecido` (FR-025 a FR-027), `postosVisiveis`, `paisesSemPostoVisiveis`, `agruparPostos`, `buscarTerritorios` (sem acento e sem diferença de maiúscula).
