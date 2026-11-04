# Research: Modo de cores para daltonismo

As medições usam o código do projeto (`distanciaDeCor.ts` e `contraste.ts`), com CIEDE2000 e as
matrizes de Machado, Oliveira e Fernandes (2009), as mesmas da 002. Tabelas completas em
[contracts/paletas-e-padroes.md](contracts/paletas-e-padroes.md).

## Ponto de partida

Cores atuais medidas pelos critérios do FR-006 e do FR-007:

| Modo | Pares abaixo de 12 |
|---|---|
| Alertas | 5 de 27: `sem_alerta × evitar` (5,3), `nao_verificado × neutro` (6,8), `borda não viaje × borda evite` (4,2), `sem_alerta × oceano` (7,5), `nao_verificado × oceano` (11,6) |
| Vistos | 1 de 35: `visto_exigido × listras` (8,1) |

## D1 · Paleta de Alertas

**Decisão**: paleta nova, com "sem alerta" azul-céu, "evite" amarelo, "não viaje" vermelho-coral e
"não verificado" cinza médio. Pior par: 13,4.

**Por quê**: o par verde × âmbar é o que colapsa em protanopia e deuteranopia. O eixo azul × amarelo
resiste a essas duas, e a diferença de luminosidade cobre a tritanopia. "Não viaje" continua
vermelho. As cores saíram de uma busca com limites de luminosidade, croma e matiz para cada papel,
seguida de ajuste à mão.

**Alternativas**: mexer só na luminosidade do verde e do âmbar não abre distância sem encostar em
outra cor; a saída da busca sem ajuste dava 15,6, mas com a borda em tom de vinho (`#6E071C`), longe
do "vermelha" que a legenda afirma.

## D2 · Paleta de Vistos

**Decisão**: manter as seis cores da 002 e trocar só as listras do RG por `#0E2A20`.

**Por quê**: é o único par reprovado, e a spec permite reaproveitar. A rampa aprovada pelo
responsável fica intacta. `#0E2A20` tem pior distância de 20,0 e contraste de 11,43 sobre o amarelo.
O mínimo geral (12,1) é de um par que já existe, `visto_na_chegada × sem_informacao`.

**Alternativas**: `#000000` (16,0), que passa com menos folga; clarear `visto_exigido`, que mexeria
na rampa.

**Consequência**: em "Vistos", ligar o modo só muda visivelmente os países com RG.

## D3 · Bordas regionais

**Decisão**: `#861212` contínua para "não viaje" e `#8C641A` tracejada `[3, 2]` para "evite".

**Por quê**: a luminosidade separa as duas (L 28 × L 45) e o estilo de linha cobre a escala de cinza.
A vermelha mantém o matiz da atual (h 35 × h 31). `#8C641A` é o marrom mais claro que ainda dá 3:1
sobre "sem alerta" (3,10), o que permite à vermelha ficar mais viva: escurecer menos que `#861212`
derruba o par em deuteranopia.

## D4 · Tracejado numa segunda camada

**Decisão**: camada nova `regional-tracejada`, com `line-dasharray` fixo, filtrada por
`borda_tracejada`. A camada `regional` exclui essas feições.

**Por quê**: com o modo desligado, a propriedade nunca existe, e `regional` desenha o que desenha
hoje. O FR-015 exige igualdade exata, e isso não pode ser testado no jsdom.

**Alternativa**: `line-dasharray` por feição, aceito pelo MapLibre 6.15, usando `[1, 0]` como
"contínua". Faria o modo desligado passar por outro caminho de desenho.

## D5 · Padrões

**Decisão**: "não viaje" com **hachura cruzada** (cobertura de 43,8%) e "evite" com **pontos** (14,1%),
na mesma cor de marca `#18142C`. A imagem traz só as marcas, com fundo transparente, e a cor de base
vem da camada `paises`.

**Por quê**: forma e densidade diferentes separam os dois em escala de cinza, conferido em imagem
renderizada no tamanho do mapa e no da amostra (18×12). Nenhum deles usa listras diagonais simples,
reservadas ao RG. Mais denso também acompanha mais grave. O fundo transparente faz o país filtrado
esmaecer por igual: com fundo opaco, base e padrão somariam 44% de opacidade contra 25% dos outros.

**Alternativa**: padrão com base embutida, como o RG. O RG continua assim para não mudar a aparência
atual.

## D6 · Onde mora o estado

**Decisão**: `useState(lerPreferenciaDoDaltonismo)` na `Tela`, gravando no clique, como em
`LegendaRecolhivel`.

**Por quê**: a leitura é síncrona, então o primeiro render já usa a paleta certa (FR-013), sem script
no `index.html`. Fora do reducer, alternar não tem como mexer em seleção ou filtros (FR-004). As
cores chegam por JavaScript (o MapLibre precisa de hex e as amostras usam `style`), então não há CSS
para trocar.

**Alternativas**: ação no reducer, que exigiria inicializar `ESTADO_INICIAL` com leitura externa;
atributo no `<html>` com variáveis CSS, sem efeito sobre o mapa.

**Cuidado**: `App.test.tsx` confere que o `localStorage` não contém `/vistos|modo/i`. A chave é
`farol-atlas:daltonismo`, sem "modo".

## D7 · Botão

**Decisão**: no cabeçalho, ao lado do `SeletorDeModo`, com o texto em duas linhas ("Modo" /
"daltonismo"), `aria-pressed` e um quadradinho com marca de seleção que mostra o estado sem depender
da cor.

**Por quê**: o cabeçalho é o único lugar visível com a gaveta aberta ou a legenda recolhida (FR-003).
O nome fica escrito em qualquer largura. Estimativa em 360 px: seletor 162 + Sobre 61 + botão 96 + dois
espaços de 8 = 335 px, de 344 disponíveis.

**Alternativa**: junto ao botão da legenda, que fica sob a gaveta aberta.

## D8 · Amostras da legenda

**Decisão**: amostras de padrão como SVG em `data:` gerado da **mesma função de desenho** do mapa; no
modo ligado, a amostra da borda vira um SVG de 30×12 com as duas linhas, uma contínua e outra
tracejada, com os mesmos números do mapa.

**Por quê**: um único desenho garante amostra igual ao mapa (FR-010). A amostra atual, de 18 px com
borda CSS, não comporta um tracejado de 7,5 px com 5 px de intervalo, e o `dashed` do CSS varia de
navegador para navegador. Modo desligado: a amostra atual, sem mudança.

## D9 · Contorno escuro em Alertas

**Decisão** (ajuste do responsável, 2026-11-04): com o modo ligado, "Alertas" usa o contorno do modo
"Vistos", `#1F2A44`, 0,6 px. Com o modo desligado, segue o branco. O estilo do mapa passa a ter
`transition: { duration: 0, delay: 0 }`.

**Por quê**: "sem alerta" virou azul-claro, perto do oceano: 13,5 de distância no pior caso, e contorno
branco com 1,72:1 contra ele e 1,24:1 contra o oceano. O contorno escuro dá 8,31:1 e 11,45:1, e o
mínimo entre as quatro cores sobe para 4,16:1. A distância não mudou; o que separa país e mar agora é
a linha.

O contorno é trocado por `setPaintProperty`, que o MapLibre anima por 300 ms por padrão, e a spec pede
troca sem animação com movimento reduzido. Só a camada `fronteiras` é alterada assim, então zerar a
transição do estilo resolve em uma linha. Efeito no modo desligado: a troca "Alertas" × "Vistos" deixa
de ter a transição de 300 ms no contorno; as cores finais são as mesmas.

**Alternativa**: zerar a transição só com movimento reduzido, o que exigiria mais um efeito no adaptador.
