# Contrato: paletas, padrões e bordas

Estes valores são a fonte dos testes. Com o modo desligado, valem as cores atuais, sem mudança.

Critério (FR-006 e FR-007): CIEDE2000 de pelo menos 12, em visão normal e nas simulações de
protanopia, deuteranopia e tritanopia, entre as cores de um modo e delas com o neutro `#F1EFE8` e o
oceano `#DCE8F2`. Medido com `distanciaEntreCores` e `simularDaltonismo`.

## Paletas

### Alertas

| Papel | Atual | Modo daltonismo | Token | Lab (L, C, h) |
|---|---|---|---|---|
| Sem alerta | `#C0DD97` | `#8CCDFB` | `--color-daltonismo-sem-alerta` | 80, 30, 253 |
| Evite | `#FAC775` | `#F1D25F` | `--color-daltonismo-evitar` | 85, 60, 92 |
| Não viaje | `#E24B4A` | `#E4605B` | `--color-daltonismo-nao-viajar` | 58, 59, 30 |
| Não verificado | `#D3D1C7` | `#878C92` | `--color-daltonismo-nao-verificado` | 58, 4, 261 |
| Borda "não viaje" | `#A32D2D` | `#861212` | `--color-daltonismo-borda-nao-viaje` | 28, 57, 35 |
| Borda "evite" | `#854F0B` | `#8C641A` | `--color-daltonismo-borda-evite` | 45, 46, 78 |
| Marcas dos padrões | (não há) | `#18142C` | `--color-daltonismo-marcas` | 8, 18, 301 |

FR-008, conferido por teste: a borda de "não viaje" fica com matiz entre 15° e 45° e croma de pelo
menos 40 (vermelho); a de "evite", com matiz entre 55° e 85° e croma entre 25 e 55 (marrom).

### Vistos

As seis situações reaproveitam `CORES_DE_VISTO`, sem token novo. Só as listras mudam.

| Papel | Atual | Modo daltonismo | Token |
|---|---|---|---|
| Isento | `#FEDD50` | `#FEDD50` | (o atual) |
| Visto na chegada | `#D17DA4` | `#D17DA4` | (o atual) |
| Autorização ou visto eletrônico | `#8F5FCC` | `#8F5FCC` | (o atual) |
| Visto exigido | `#3B1C6B` | `#3B1C6B` | (o atual) |
| Outra situação | `#948878` | `#948878` | (o atual) |
| Sem informação | `#BEBAB1` | `#BEBAB1` | (o atual) |
| Listras do RG | `#1F2A44` | `#0E2A20` | `--color-daltonismo-listras` |

## Padrões

Ladrilho de 16×16 (`LADO_DO_PADRAO`), com passo 8. Na amostra da legenda, o ladrilho é de 8×8. Uma
função de desenho por padrão serve ao mapa e à amostra.

| Nível | Padrão | Pixel (x, y) é marca quando | Cobertura | Cor da marca | Fundo |
|---|---|---|---:|---|---|
| Não viaje | Hachura cruzada | `(x + y) % 8 < 2` ou `(x - y + 16) % 8 < 2` | 43,8% | `#18142C` | Transparente |
| Evite | Pontos | `x % 8 < 3` e `y % 8 < 3` | 14,1% | `#18142C` | Transparente |
| Sem alerta, não verificado | Nenhum | | | | |

| Imagem | Quando | Conteúdo |
|---|---|---|
| `listras-rg` | "Isento" com RG, modo desligado | Atual |
| `listras-rg-daltonismo` | "Isento" com RG, modo ligado | Mesmo desenho, listras `#0E2A20`, base `#FEDD50` (opaca) |
| `hachura-nao-viaje` | "Não viaje", modo ligado | Só marcas |
| `pontos-evite` | "Evite", modo ligado | Só marcas |

O selo do painel não ganha padrão: fica só a cor, porque o nível está escrito ao lado.

## Bordas regionais

| Nível | Modo desligado | Modo ligado, mapa | Modo ligado, amostra da legenda | Painel |
|---|---|---|---|---|
| Não viaje | `#A32D2D` contínua | `#861212` contínua, 2,5 px | Linha contínua | Só a cor muda |
| Evite | `#854F0B` contínua | `#8C641A` tracejada, 2,5 px, `line-dasharray: [3, 2]` (7,5 px e 5 px) | Linha tracejada, `stroke-dasharray: 7.5 5` | Só a cor muda |

A amostra do modo ligado é um SVG de 30×12 com as duas linhas, a contínua em cima. Com o modo
desligado, a amostra atual fica. O texto da legenda não muda.

## Contraste

Fórmula WCAG 2.x, função `contraste()`.

### Contorno dos países

| Modo do globo | Modo desligado | Modo ligado |
|---|---|---|
| Alertas | Branco `#ffffff`, 0,6 px | **`#1F2A44`, 0,6 px** (FR-008a) |
| Vistos | `#1F2A44`, 0,6 px | `#1F2A44`, 0,6 px |

Alertas com o modo ligado (mínimo exigido: 3:1). A coluna do branco mostra o que o contorno escuro
substitui.

| Cor | Contorno `#1F2A44` | Se fosse o branco |
|---|---:|---:|
| Sem alerta `#8CCDFB` | 8,31 | 1,72 |
| Evite `#F1D25F` | 9,59 | 1,49 |
| Não viaje `#E4605B` | 4,16 | 3,43 |
| Não verificado `#878C92` | 4,21 | 3,39 |
| Oceano `#DCE8F2` | 11,45 | 1,24 |
| Neutro `#F1EFE8` | 12,39 | 1,15 |

"Sem alerta" × oceano, em CIEDE2000:

| Normal | Protanopia | Deuteranopia | Tritanopia |
|---:|---:|---:|---:|
| 15,2 | 13,5 | 15,8 | 18,0 |

Vistos, nos dois estados do modo:

| Cor | Contorno `#1F2A44` (igual à 002) |
|---|---:|
| Isento | 10,64 |
| Visto na chegada | 4,88 |
| Autorização ou visto eletrônico | 3,18 |
| Visto exigido | 1,06 |
| Outra situação | 4,11 |
| Sem informação | 7,36 |
| Oceano | 11,45 |
| Neutro | 12,39 |

"Visto exigido" se distingue pelo próprio preenchimento contra o oceano, como registrado na 002.

### Marcas e listras (mínimo 3:1, WCAG 1.4.11)

| Par | Contraste |
|---|---:|
| Marcas × "não viaje" | 5,21 |
| Marcas × "evite" | 12,02 |
| Listras × "Isento" | 11,43 |

### Bordas regionais

| Fundo | Borda "não viaje" | Borda "evite" |
|---|---:|---:|
| Sem alerta | 5,80 | 3,10 |
| Evite | 6,70 | 3,57 |
| Não verificado | 2,94 | 1,57 |
| Oceano | 8,00 | 4,27 |
| Neutro | 8,65 | 4,62 |
| Branco (legenda, painel) | 9,96 | 5,31 |

Entre si, as bordas têm 1,87 (hoje, 1,05). Sobre "não verificado", as duas ficam abaixo de 3:1; a
distância de cor segue acima de 12, e o estilo de linha e o painel completam a leitura.

## Distâncias (CIEDE2000)

Em ordem, do par mais próximo ao mais distante. `neutro` e `oceano` não mudam com o modo.

#### Alertas (35 pares)

| Par | Normal | Protanopia | Deuteranopia | Tritanopia | Mínimo |
|---|---:|---:|---:|---:|---:|
| borda_nao_viaje × borda_evite | 29,4 | 19,5 | 13,4 | 17,2 | 13,4 |
| sem_alerta × oceano | 15,2 | 13,5 | 15,8 | 18,0 | 13,5 |
| nao_viajar × borda_evite | 31,5 | 14,0 | 14,8 | 18,4 | 14,0 |
| evitar × neutro | 23,9 | 24,8 | 23,6 | 18,0 | 18,0 |
| nao_viajar × nao_verificado | 28,9 | 18,3 | 24,3 | 25,2 | 18,3 |
| evitar × nao_viajar | 44,9 | 30,1 | 19,9 | 26,0 | 19,9 |
| sem_alerta × nao_verificado | 23,1 | 23,0 | 22,1 | 26,1 | 22,1 |
| sem_alerta × neutro | 24,3 | 22,4 | 25,4 | 27,4 | 22,4 |
| nao_verificado × oceano | 24,6 | 24,7 | 24,4 | 24,7 | 24,4 |
| nao_viajar × borda_nao_viaje | 27,2 | 24,8 | 28,9 | 26,6 | 24,8 |
| nao_verificado × neutro | 27,2 | 26,9 | 27,3 | 27,0 | 26,9 |
| nao_verificado × borda_evite | 29,3 | 31,0 | 29,3 | 27,0 | 27,0 |
| nao_viajar × neutro | 37,7 | 34,2 | 28,5 | 37,7 | 28,5 |
| evitar × oceano | 33,4 | 33,0 | 33,1 | 29,1 | 29,1 |
| borda_nao_viaje × marcas | 32,8 | 30,4 | 37,9 | 34,4 | 30,4 |
| evitar × nao_verificado | 36,9 | 35,5 | 37,0 | 31,0 | 31,0 |
| evitar × borda_evite | 33,8 | 34,2 | 32,1 | 32,3 | 32,1 |
| nao_viajar × oceano | 40,6 | 36,7 | 34,2 | 38,4 | 34,2 |
| nao_verificado × borda_nao_viaje | 39,7 | 37,7 | 35,0 | 40,1 | 35,0 |
| borda_evite × marcas | 46,0 | 45,1 | 46,8 | 37,3 | 37,3 |
| nao_verificado × marcas | 42,2 | 41,2 | 40,9 | 40,0 | 40,0 |
| sem_alerta × nao_viajar | 50,1 | 40,9 | 43,6 | 62,0 | 40,9 |
| borda_evite × neutro | 43,2 | 45,4 | 41,6 | 42,7 | 41,6 |
| sem_alerta × evitar | 49,8 | 46,8 | 49,2 | 41,7 | 41,7 |
| nao_viajar × marcas | 49,2 | 42,3 | 55,3 | 50,7 | 42,3 |
| borda_evite × oceano | 47,0 | 49,0 | 45,8 | 48,0 | 45,8 |
| evitar × borda_nao_viaje | 63,8 | 62,4 | 49,0 | 51,0 | 49,0 |
| sem_alerta × borda_evite | 53,7 | 54,6 | 52,4 | 53,8 | 52,4 |
| borda_nao_viaje × neutro | 62,8 | 67,7 | 55,6 | 60,2 | 55,6 |
| borda_nao_viaje × oceano | 64,2 | 68,9 | 58,0 | 63,5 | 58,0 |
| sem_alerta × borda_nao_viaje | 67,7 | 69,7 | 61,0 | 71,8 | 61,0 |
| sem_alerta × marcas | 70,5 | 70,4 | 64,8 | 70,0 | 64,8 |
| evitar × marcas | 85,8 | 81,9 | 86,2 | 76,5 | 76,5 |
| marcas × oceano | 84,6 | 84,0 | 83,3 | 83,2 | 83,2 |
| marcas × neutro | 88,1 | 87,1 | 87,7 | 85,8 | 85,8 |

#### Vistos (35 pares)

| Par | Normal | Protanopia | Deuteranopia | Tritanopia | Mínimo |
|---|---:|---:|---:|---:|---:|
| visto_na_chegada × sem_informacao | 28,9 | 20,8 | 12,1 | 23,2 | 12,1 |
| sem_informacao × neutro | 12,4 | 12,6 | 12,3 | 12,6 | 12,3 |
| autorizacao_eletronica × outra_situacao | 36,6 | 35,4 | 35,6 | 12,8 | 12,8 |
| visto_na_chegada × outra_situacao | 27,7 | 19,6 | 13,8 | 17,7 | 13,8 |
| sem_informacao × oceano | 14,9 | 15,3 | 15,3 | 16,6 | 14,9 |
| isento × sem_informacao | 25,8 | 25,9 | 25,6 | 15,0 | 15,0 |
| outra_situacao × sem_informacao | 15,4 | 15,6 | 15,0 | 15,5 | 15,0 |
| isento × neutro | 25,3 | 26,3 | 24,9 | 15,7 | 15,7 |
| visto_na_chegada × autorizacao_eletronica | 22,2 | 17,7 | 25,0 | 21,6 | 17,7 |
| visto_na_chegada × oceano | 32,5 | 24,5 | 19,0 | 32,7 | 19,0 |
| visto_exigido × listras | 31,8 | 28,9 | 24,5 | 20,0 | 20,0 |
| isento × visto_na_chegada | 55,9 | 45,6 | 36,1 | 21,7 | 21,7 |
| visto_na_chegada × neutro | 35,0 | 29,0 | 21,9 | 31,7 | 21,9 |
| isento × outra_situacao | 31,9 | 31,7 | 31,5 | 23,5 | 23,5 |
| autorizacao_eletronica × sem_informacao | 39,3 | 38,4 | 37,1 | 23,8 | 23,8 |
| autorizacao_eletronica × visto_exigido | 25,3 | 25,3 | 25,4 | 26,4 | 25,3 |
| isento × oceano | 35,0 | 34,6 | 34,6 | 26,8 | 26,8 |
| outra_situacao × neutro | 27,5 | 27,8 | 27,0 | 27,8 | 27,0 |
| outra_situacao × oceano | 29,1 | 29,6 | 28,9 | 31,1 | 28,9 |
| isento × autorizacao_eletronica | 72,4 | 66,1 | 65,3 | 32,5 | 32,5 |
| visto_exigido × outra_situacao | 46,8 | 45,0 | 46,4 | 34,3 | 34,3 |
| outra_situacao × listras | 39,8 | 34,4 | 37,0 | 44,1 | 34,4 |
| autorizacao_eletronica × oceano | 34,5 | 37,7 | 36,3 | 36,8 | 34,5 |
| autorizacao_eletronica × neutro | 46,1 | 44,3 | 43,6 | 35,0 | 35,0 |
| visto_na_chegada × visto_exigido | 42,1 | 35,6 | 44,5 | 44,8 | 35,6 |
| autorizacao_eletronica × listras | 43,5 | 41,4 | 38,7 | 39,5 | 38,7 |
| visto_na_chegada × listras | 59,4 | 40,3 | 44,1 | 58,6 | 40,3 |
| visto_exigido × sem_informacao | 63,1 | 61,3 | 61,9 | 55,3 | 55,3 |
| sem_informacao × listras | 59,5 | 57,1 | 58,4 | 61,1 | 57,1 |
| isento × visto_exigido | 91,1 | 85,6 | 86,5 | 67,0 | 67,0 |
| visto_exigido × oceano | 69,2 | 68,3 | 68,5 | 67,7 | 67,7 |
| visto_exigido × neutro | 75,2 | 72,4 | 73,0 | 68,4 | 68,4 |
| listras × oceano | 76,1 | 74,5 | 75,8 | 75,3 | 74,5 |
| isento × listras | 78,7 | 74,6 | 79,0 | 79,1 | 74,6 |
| listras × neutro | 77,2 | 74,7 | 76,8 | 78,2 | 74,7 |
