# Revisão de acessibilidade (T129)

**Escopo**: princípio VI (acessível e celular), FR-003 e a decisão de não ter teste automatizado de viewport por enquanto.
**Data**: 25/10/2026 · **Alvo**: 360 px de largura, teclado e leitor de tela.

## Como foi feita

Revisão do código de cada componente da tela (`App`, `Busca`, `Legenda`, `Painel`, `Posto`, `Aviso`, `Sobre`, `Modal`, `Marcador`, adaptador do MapLibre e `tema.css`) contra os critérios abaixo, mais os testes de interface que já cobrem o comportamento (357 testes do frontend passando).

**O que esta revisão NÃO fez**: não houve sessão com leitor de tela de verdade (NVDA, VoiceOver ou TalkBack) nem conferência em um celular ou no emulador de 360 px do navegador. Esses pontos ficam na lista "Para conferir à mão" no fim.

## Resultado por critério

| Critério | Resultado | Onde se vê |
|---|---|---|
| **Cor nunca é a única informação** | Atende | A legenda tem o nome de cada nível em texto (`Legenda.tsx`); o painel escreve o nível ("Evite viagens não essenciais") e cada região com o nível por extenso (`Painel.tsx`); a borda regional tem item de legenda com texto; o filtro e o painel substituem a leitura das cores do mapa. Ícones de postos diferem por forma (círculo, quadrado, tracejado), não só por cor; o destaque é maior e tem contorno grosso (`tema.css`). |
| **Rótulos das caixas da legenda** | Atende | Cada caixa fica dentro de um `<label>` com o nome do nível e área de toque de 44 px de altura (`min-h-11`). A amostra de cor é `aria-hidden`, para o leitor não ler "cor" duas vezes. |
| **Foco visível** | Atende | Botões, caixas, campo de busca e `summary` usam o contorno padrão do navegador (o Tailwind 4 não o remove). Os ícones do mapa têm `:focus-visible` próprio (contorno de 3 px). Diálogos prendem o foco, devolvem o foco a quem os abriu e fecham com Esc (`Modal.tsx`, com testes). |
| **`prefers-reduced-motion`** | Atende | `tema.css` zera `animation` e `transition` de tudo; o pulso do ícone em destaque só liga sem `reduzirMovimento` (`Marcador.tsx`); os movimentos da câmera do mapa usam `duracaoDoMovimento(reduzirMovimento)` (`adaptador-maplibre.tsx`). A inércia do arrastar do próprio MapLibre não é nossa e segue a configuração do navegador. |
| **Alvos de toque** | Atende | Botões e linhas clicáveis têm pelo menos 44 px de altura (`min-h-11`, `size-11`). Os ícones de postos têm 30 px (42 px em destaque), acima do mínimo de 24 px do WCAG 2.2 (critério 2.5.8). |
| **Teclado** | Atende, com ressalva | Busca é um combobox completo (setas, Enter, Esc). Legenda, painel, postos expansíveis, "Sobre" e diálogos funcionam só com teclado. Esc fecha o painel (e não fecha o painel quando um diálogo ou a lista da busca está aberto). Ressalva: ver achado 4. |
| **Leitor de tela** | Atende, com ressalvas | Regiões nomeadas (`Avisos`, `Legenda`, `Detalhes do país`, `Alertas regionais`), `role="status"` e `role="alert"` para carregando, erro e "sem resultado", `aria-current` no ícone em destaque, `lang="pt-BR"`. O mapa em si não é legível por leitor de tela (é desenho): quem não o enxerga usa a busca e o painel, que dão o mesmo dado em texto. Ressalvas: achados 1 e 2. |
| **360 px de largura** | Atende pelo código | Cabeçalho em coluna abaixo de `sm`, legenda recolhida no celular, atrás do botão "Legenda das cores" (`aria-expanded`, `aria-controls`, teclado; conferido no Edge a 360 px em 25/10/2026), painel como gaveta de 55% da altura, `max-w-[calc(100%-1rem)]` e `w-[min(90vw,24rem)]` nas caixas flutuantes, sem larguras fixas maiores que 340 px (o painel lateral só existe acima do ponto de corte). Falta ver na tela: ver "Para conferir à mão". |
| **Contraste de texto** | Atende (ver "Fundo de espaço", abaixo) | Pares usados: texto `#1f1f1d` e `#5f5e5a` sobre branco e sobre `#f4f3ee` (acima de 5,5:1); azul `#0c447c` sobre branco, e branco sobre o azul (9,8:1); `#633806` sobre `#faeeda` (8,7:1). Medidos com a fórmula de luminância do WCAG. O selo "+1" dos ícones tem 10 px, mas é decorativo (`aria-hidden`) e o nome acessível do botão já diz quantos postos há. |
| **Idioma e zoom** | Atende | `<html lang="pt-BR">` e `viewport` sem `user-scalable=no`: a pessoa pode ampliar. |

## Achados e correções

1. **Ícones de postos escondidos de leitores de tela** (corrigido). O contêiner do mapa tinha `role="img"`, e os ícones de postos (botões) ficam dentro dele. Filhos de `img` são apresentacionais, então vários leitores de tela ignorariam os botões. Trocado por `role="group"` com o mesmo nome (`adaptador-maplibre.tsx`). Não há teste automatizado: o adaptador depende de WebGL, que o ambiente de testes não tem.
2. **O painel abria sem avisar** (corrigido). Ao escolher um país (toque, busca), o foco ficava onde estava e o leitor de tela não percebia o painel novo. Agora o painel recebe o foco ao abrir (`tabindex="-1"`, fora da ordem do Tab) e devolve o foco a quem o tinha ao fechar, o que também leva quem usa teclado de volta à busca depois do Esc. Testes em `Painel.test.tsx`.
3. **`aria-controls` da busca apontava para uma lista que não existia** (corrigido). Só aponta enquanto a lista está aberta. Teste em `Busca.test.tsx`.
4. **Muitos ícones na ordem do Tab** (não alterado). Com zoom alto e muitos postos visíveis, o Tab passa por todos os ícones antes de chegar ao painel. Hoje os ícones só aparecem a partir de certo zoom e o teclado tem a busca como caminho principal, então não foi tratado. Se isso incomodar na prática, o caminho é um atalho "ir para o painel" ou tirar os ícones da ordem do Tab quando o painel está aberto.

## Para conferir à mão (não dá para fazer daqui)

- Abrir o site em 360 px (celular de verdade ou emulador do navegador) e passar por: cabeçalho com o aviso longo, legenda recolhida e expandida, busca com a lista aberta, painel como gaveta com o teclado virtual aberto.
- Percorrer a página só com o teclado (Tab, Shift+Tab, setas na busca, Esc) e conferir que o foco nunca some.
- Ligar um leitor de tela e conferir: o painel é anunciado ao abrir; os ícones de postos aparecem na lista de botões; o aviso "Dados desatualizados" é lido.
- Ligar "reduzir movimento" no sistema e conferir que o mapa anda sem animar e o ícone em destaque não pulsa.

## Fundo de espaço (25/10/2026)

O fundo do mapa passou de bege para um céu quase preto (`#04060c`) com 180 estrelas (pequenas e discretas, poucas brilhantes), atrás do globo. O que ficou sobre o céu foi medido no Edge, a 1280 px e a 360 px, com o painel aberto e fechado: para cada texto, a cor contra o fundo de verdade (somando as camadas translúcidas) e, quando não há cartão opaco por baixo, contra os dois piores casos, o céu escuro e o mapa claro (`#dce8f2`). **Nenhum dos 17 a 42 textos conferidos por tela ficou abaixo do AA (4,5:1).** O menor valor foi 7,9:1 (botão "Sobre" sobre o céu).

| O que | Antes | Agora | Contraste |
|---|---|---|---|
| Título "Farol Atlas" | texto escuro com sombra, direto sobre o mapa: ilegível no céu preto | texto branco num cartão `#04060c` a 90% | 17:1 sobre o mapa claro, 20:1 sobre o céu (**ajustado**) |
| Botão "Sobre" | azul `#0c447c` sobre branco a 90% | igual | 7,9:1 sobre o céu, 9,7:1 sobre o mapa |
| Aviso de site não oficial, busca, legenda, painel, "Fronteiras", zoom | cartões com fundo próprio | igual | 6,5:1 a 16,5:1 |
| Fundo da página (antes do React montar) | branco | `#04060c` (sem piscar de branco), `theme-color` igual | |

Os pares de cores do tema ficam travados por teste (`contraste.test.ts`), que lê os tokens de `tema.css`. O token do céu é novo (`--color-ceu`); o `--color-espaco` continua sendo a superfície clara dos cartões. As cores dos níveis de alerta não mudaram. O céu é decorativo (`aria-hidden`, sem toque) e não tem animação, então "reduzir movimento" não tem o que desligar.
