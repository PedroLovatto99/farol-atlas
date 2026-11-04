# Feature Specification: Modo de cores para daltonismo

**Feature Branch**: `004-modo-daltonismo`

**Created**: 2026-11-04

**Status**: Draft

**Input**: User description: "Feature 004 do Farol Atlas: modo de cores para daltonismo. Um botão liga e desliga paletas próprias nos modos Alertas e Vistos, distinguíveis em protanopia, deuteranopia e tritanopia, com padrões no mapa para 'não viaje' e 'evite', preferência lembrada no navegador e nenhuma mudança em regras, dados ou textos."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Alternar para cores acessíveis (Priority: P1)

Uma pessoa com daltonismo abre o globo e não consegue separar alguns níveis só pela cor: no modo "Alertas", por exemplo, "sem alerta" e "evite" ficam quase iguais na protanopia e na deuteranopia. Ela toca no botão "Modo daltonismo" e o globo, as bordas de alerta regional, a legenda, o selo do painel e a variação "Isento com RG" passam a usar paletas próprias, nos modos "Alertas" e "Vistos". "Não viaje" e "evite" ganham padrões no mapa, repetidos na legenda, para que a leitura não dependa só da cor. Na visita seguinte, o site já abre com o modo ligado.

**Why this priority**: é a feature inteira. Hoje, no mapa, a leitura do nível depende da cor, o que vai contra o princípio VI da constituição (cor não pode ser a única forma de transmitir informação).

**Independent Test**: ligar o modo, percorrer "Alertas" e "Vistos", medir as cores de cada modo nas simulações, ver o globo e a legenda em escala de cinza, recarregar a página e depois desligar o modo e comparar com a aparência atual.

**Acceptance Scenarios**:

1. **Given** a primeira visita ao site, **When** a página abre, **Then** o modo daltonismo está desligado e a aparência é exatamente a atual.
2. **Given** o modo desligado, **When** o usuário aciona o botão, **Then** o globo, as bordas de alerta regional, a legenda e o selo do painel passam às paletas do modo daltonismo, sem recarregar a página.
2a. **Given** o modo ligado e "Alertas" ativo, **When** o usuário olha o globo, **Then** o contorno dos países é o escuro do modo "Vistos", e um país "sem alerta" não se confunde com o oceano. Ao desligar, o contorno volta a ser o branco atual.
3. **Given** o modo ligado, **When** o usuário troca entre "Alertas" e "Vistos", **Then** o modo continua ligado e cada um usa a sua paleta acessível.
4. **Given** o modo ligado e "Alertas" ativo, **When** o usuário olha o globo em escala de cinza, **Then** distingue "não viaje" de "evite" pelos padrões, e os dois dos demais níveis, que ficam sem padrão.
5. **Given** o modo ligado e "Alertas" ativo, **When** o usuário olha a legenda, **Then** as amostras de "não viaje" e "evite" mostram o mesmo padrão e as mesmas cores do mapa.
5a. **Given** o modo ligado e "Alertas" ativo, **When** o usuário olha um país com alerta regional e a amostra da legenda, **Then** a borda de "não viaje" é contínua e a de "evite" é tracejada, nos dois lugares, e o texto da legenda é o mesmo do modo desligado.
6. **Given** o modo ligado e "Vistos" ativo, **When** o usuário olha um país "Isento" que aceita o RG, **Then** o país continua listrado, com as cores da paleta acessível, e a amostra "Isento, entrada com RG" da legenda é igual ao mapa.
7. **Given** o modo ligado, **When** o usuário recarrega a página ou volta em outra visita, **Then** o site abre com o modo ligado, sem mostrar antes as cores padrão.
8. **Given** o modo ligado, **When** o usuário desliga o botão, **Then** a aparência volta a ser exatamente a atual, e a próxima visita abre com o modo desligado.
9. **Given** um país selecionado, filtros da legenda marcados, painel aberto e o globo numa posição, **When** o usuário alterna o modo daltonismo, **Then** a seleção, os filtros, o painel, a câmera e o modo do globo ("Alertas" ou "Vistos") continuam como estavam.
10. **Given** um leitor de tela ou o teclado, **When** o usuário chega ao botão, **Then** o nome "Modo daltonismo" e o estado ligado ou desligado são anunciados, e o botão alterna com Enter ou Espaço, com foco visível.
11. **Given** uma tela de 360 px, **When** o botão aparece, **Then** ele pode ser tocado e não cobre a legenda, o painel nem os outros controles.
12. **Given** o modo ligado, **When** o usuário lê o painel, a legenda ou o chat, **Then** os textos, os níveis, as categorias e os dados são idênticos aos do modo desligado.

---

### Edge Cases

- **Navegador sem acesso ao armazenamento** (janela privada, dados bloqueados): o botão funciona durante a visita, só não lembra; nenhum erro aparece.
- **Valor guardado inválido**: vale o modo desligado.
- **Filtro da legenda desmarcado**: o país com padrão se comporta como qualquer outro país desmarcado; o padrão nunca fica aparecendo sozinho.
- **Vistos carregando ou com erro**: o país continua sem preenchimento, como hoje; o modo não pinta nada no lugar.
- **País "sem alerta" com alerta só regional**: fica sem padrão, porque o padrão segue o nível do país; a borda regional usa a cor acessível e o estilo de linha do nível dela.
- **Países muito pequenos ou globo afastado**: o padrão pode não caber na área; a cor continua própria e o painel traz o nível em texto.
- **Duas abas abertas**: a mudança vale para a aba em que foi feita e para as visitas seguintes; a outra aba só muda ao recarregar.
- **Movimento reduzido**: a troca de cores acontece sem animação quando o usuário pede menos movimento.

## Requirements *(mandatory)*

### Functional Requirements

*Botão*

- **FR-001**: A interface MUST ter um botão "Modo daltonismo", sempre disponível nos modos "Alertas" e "Vistos", que liga e desliga o modo. O modo começa desligado.
- **FR-002**: O botão MUST ter nome claro, anunciar o estado ligado ou desligado, ser operável por teclado, com foco visível, e mostrar o estado também de forma visual, sem depender só da cor.
- **FR-003**: O botão MUST funcionar em telas a partir de 360 px sem esconder a legenda, o painel nem os outros controles, com a legenda aberta ou recolhida.
- **FR-004**: Alternar o modo MUST NOT mudar a seleção, os filtros, o painel, a câmera nem o modo do globo, e MUST NOT buscar dados de novo.

*Paletas*

- **FR-005**: Com o modo ligado, o globo, as bordas de alerta regional (no mapa, na legenda e no painel), as amostras da legenda, o selo do nível no painel e as listras de "Isento com RG" MUST usar as paletas do modo daltonismo, nos dois modos do globo.
- **FR-006**: Cada modo do globo MUST ter uma única paleta acessível, válida para as três formas de daltonismo. As cores que aparecem juntas MUST ficar a pelo menos 12 de distância (CIEDE2000) umas das outras, em visão normal e nas simulações de protanopia, deuteranopia e tritanopia:
  - **Alertas**: os quatro níveis, as duas bordas regionais e as cores dos padrões.
  - **Vistos**: as seis situações e a cor das listras do RG.
- **FR-007**: Cada cor do FR-006 MUST ficar também a pelo menos 12 de distância do neutro (Brasil e áreas neutras) e do oceano, nas mesmas quatro visões. O neutro e o oceano não mudam com o modo.
- **FR-008**: A borda de "não viaje" MUST continuar sendo percebida como vermelha e a de "evite" como marrom, para que a frase da legenda ("Borda vermelha… Borda marrom…") continue verdadeira com o modo ligado. Além da diferença de luminosidade, com o modo ligado as bordas regionais MUST ter estilos de linha diferentes no mapa: contínua para "não viaje" e tracejada para "evite". A amostra da legenda MUST mostrar o mesmo estilo, sem mudança no texto da legenda. Com o modo desligado, as bordas ficam como hoje.

*Contorno*

- **FR-008a**: Com o modo ligado, o modo "Alertas" MUST usar o contorno dos países do modo "Vistos", com a mesma cor e a mesma espessura, para que os países "sem alerta" não se confundam com o oceano. O contorno MUST ter contraste de pelo menos 3:1 contra as quatro cores de Alertas e contra o oceano. Com o modo desligado, o contorno fica como hoje.

*Padrões*

- **FR-009**: Com o modo ligado, no modo "Alertas", "não viaje" e "evite" MUST ter padrões diferentes entre si no mapa, distinguíveis em escala de cinza. "Sem alerta" e "não verificado" ficam sem padrão.
- **FR-010**: A legenda MUST mostrar nas amostras de "não viaje" e "evite" o mesmo padrão e as mesmas cores do mapa.
- **FR-011**: Com o modo desligado, nenhum padrão novo aparece.

*Preferência*

- **FR-012**: A escolha MUST ficar guardada no navegador entre visitas, e nenhum dado sobre ela MUST ir ao servidor. Se o navegador não permitir guardar, o modo MUST funcionar durante a visita, sem erro.
- **FR-013**: Ao abrir com o modo guardado como ligado, o site MUST mostrar as paletas acessíveis desde a primeira pintura. O modo do globo ("Alertas" ou "Vistos") continua sem ser lembrado, como hoje.

*Só a aparência*

- **FR-014**: O modo MUST NOT mudar regras, dados, classificações, filtros nem textos; o único texto novo é o do próprio botão.
- **FR-015**: Com o modo desligado, a aparência MUST ser exatamente a atual, cor por cor.

### Key Entities

- **Preferência de cores**: ligado ou desligado; existe só no navegador da pessoa.
- **Paleta acessível**: as cores de um modo do globo, com os padrões de "não viaje" e "evite" (Alertas) e as listras do RG (Vistos).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com o modo ligado, 100% dos pares de cores que aparecem juntas em cada modo (FR-006 e FR-007) ficam a pelo menos 12 de distância, em visão normal e nas três simulações.
- **SC-002**: Em escala de cinza, com o modo ligado, "não viaje" e "evite" são identificados corretamente no mapa e na legenda pelos padrões, sem recorrer à cor nem ao painel.
- **SC-002a**: Em escala de cinza, com o modo ligado, as bordas regionais de "não viaje" (contínua) e "evite" (tracejada) são identificadas corretamente no mapa e na amostra da legenda, sem recorrer à cor nem ao painel.
- **SC-003**: Em 100% das recargas, a preferência se mantém, ligada ou desligada, sem exibir antes a outra aparência.
- **SC-004**: Com o modo desligado, todas as cores do mapa, da legenda e do painel são idênticas às atuais, e nenhum padrão novo aparece.
- **SC-005**: Ligar ou desligar o modo leva um único toque, clique ou tecla, a partir de 360 px, e a mudança é visível em menos de 1 segundo.
- **SC-006**: Nenhum texto, nível, categoria ou dado difere entre o modo ligado e o desligado, salvo o estado do próprio botão.

## Assumptions

- Nome do botão: "Modo daltonismo". O nome é fixo; o estado é anunciado à parte.
- O critério de 12 vale também em visão normal, como na 002, porque quem não tem daltonismo também pode usar o modo.
- O critério vale dentro de cada modo do globo, que é o que aparece junto. Entre cores de modos diferentes não há exigência: as exceções da 002 (Isento × evite; Sem informação × não verificado) são todas entre modos, e o modo ativo e a legenda continuam indicando o que se vê.
- O par neutro × oceano fica fora do critério: as duas cores não mudam com o modo, ficam entre 9,0 e 10,7 de distância hoje e são separadas pelo contorno dos países.
- A marca de seleção, a linha até o posto responsável e os ícones de postos não mudam com o modo. O contorno dos países muda só no modo "Alertas" com o modo ligado (FR-008a); no modo "Vistos" ele já é o escuro.
- As bordas regionais não ganham hachura: distinguem-se pela luminosidade e pelo estilo de linha (FR-008). No painel, a borda de cada região muda só de cor e continua contínua, porque o nível está escrito ao lado.
- O selo do painel é a amostra de cor ao lado do nível e não ganha padrão, porque o nível está escrito logo ao lado. A seção de visto do painel não tem selo colorido, então nada muda nela.
- Na variação "Isento com RG", as listras continuam como são, só com as cores da paleta acessível.
- A paleta de "Vistos" pode reaproveitar cores atuais que já cumprem o critério; o plano decide.
- As simulações são as que a 002 já usa.
- Fora do escopo: tamanho de fonte, alto contraste geral, tema escuro, detecção automática do tipo de daltonismo e paletas separadas por tipo.
