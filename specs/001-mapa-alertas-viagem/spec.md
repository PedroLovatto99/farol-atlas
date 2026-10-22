# Feature Specification: Mapa de alertas de viagem para brasileiros

**Feature Branch**: `001-mapa-alertas-viagem`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Mapa de alertas de viagem para brasileiros — mapa-múndi com o nível de alerta do Itamaraty para cada país e a lista de postos brasileiros no exterior."

## Clarifications

### Session 2026-10-22

- Q: Quando um país pode ser mostrado como "sem alerta"? → A: Quando não consta na lista de alertas da última **coleta completa**. Uma coleta é completa quando a lista foi lida inteira, no formato esperado, com pelo menos um alerta, e pelo menos 70% das páginas esperadas foram lidas. Uma coleta que falha não muda os níveis: vale o resultado da última coleta completa, com a data dela. Um país só fica "não verificado" por falta de dado se nunca houve uma coleta completa.
- Q: Que nível mostrar para um país que consta na lista de alertas, mas cuja página não foi lida numa coleta completa? → A: Se o alerta é o mesmo já conhecido (mesmo link e mesma data da última coleta completa), o país mantém o nível anterior. Se o alerta é novo ou mudou, o país fica "não verificado", com link para o alerta original. Para um alerta novo cuja página não foi lida, o país é identificado pelo título que aparece na lista de alertas.
- Q: Qual a cor de um país que só tem alerta para uma região? → A: A cor do país segue só os alertas que valem para o país inteiro. Se há apenas alerta regional, o país fica "sem alerta", com o destaque de região, e o painel diz que o alerta vale só para aquela região. Os alertas regionais aparecem só no destaque, no painel e no filtro.
- Q: Uma dependência com alerta próprio herda o nível do país soberano ou o alerta prevalece? → A: Para qualquer dependência, o alerta específico prevalece sobre o nível herdado, como no Taiwan. Sem alerta específico, herda o nível do país soberano.

## User Scenarios & Testing *(mandatory)*

Quem vai viajar precisa saber se o Itamaraty publicou algum alerta para o destino e onde fica a representação brasileira mais próxima. Hoje a informação está espalhada em páginas de texto do gov.br e numa tabela de repartições consulares, sem visão geral do mundo. **Ausência de alerta não significa que o governo recomenda a viagem**, e o site deve deixar isso claro.

Quem usa:

- Brasileiros planejando uma viagem, que querem uma resposta rápida sobre o destino.
- Brasileiros que já estão no exterior e precisam achar a embaixada ou o consulado responsável, quase sempre pelo celular.

### User Story 1 - Ver a situação do mundo no mapa (Priority: P1)

O usuário abre o site e vê um mapa-múndi em que cada país tem a cor do seu nível de alerta: *sem alerta do Itamaraty*, *evite viagens não essenciais*, *não viaje* ou *não verificado* (o padrão quando não há dado confirmado). Países com alerta mais grave apenas para uma região (ex.: sul do Líbano) recebem um destaque visual a mais. Uma legenda explica cada nível com texto. O site mostra a data da última atualização e avisa que não é um serviço oficial, com link para o portal do Itamaraty.

**Why this priority**: é a entrega central do produto; sozinha já responde "qual a situação do meu destino?" e é a base visual para todas as outras histórias.

**Independent Test**: abrir o site com dados de alerta de exemplo e verificar que cada país aparece na cor do seu nível, que a legenda descreve os quatro níveis em texto, que a data de atualização e o aviso de site não oficial estão visíveis e que países sem dado aparecem como "não verificado".

**Acceptance Scenarios**:

1. **Given** dados de alerta carregados, **When** o usuário abre o site, **Then** vê o mapa-múndi com cada país colorido conforme seu nível e uma legenda com o nome de cada nível em texto.
2. **Given** um país sem nenhum dado confirmado, **When** o mapa é exibido, **Then** o país aparece como "não verificado", nunca como "sem alerta".
3. **Given** um país com alerta mais grave só para uma região, **When** o mapa é exibido, **Then** o país mostra um destaque visual adicional além da cor do seu nível geral.
4. **Given** o site aberto, **When** o usuário olha a página, **Then** vê a data da última atualização, o aviso de que não é um serviço oficial e um link para o portal do Itamaraty.
5. **Given** o site aberto, **When** o usuário lê a legenda ou o aviso, **Then** entende que "sem alerta" não significa que o governo recomenda a viagem.

---

### User Story 2 - Ver os detalhes de um país e onde buscar ajuda (Priority: P2)

Ao tocar em um país, o mapa se aproxima dele e abre um painel com: bandeira e nome; nível de alerta com texto explicativo; regiões com alerta mais grave; link para o alerta original no gov.br, com a data; e a lista dos postos brasileiros no país (embaixadas, consulados e escritórios). Cada posto mostra o tipo e a cidade e pode ser expandido para mostrar endereço, telefone de plantão e um link "Abrir no Google Maps". Se o país não tem posto brasileiro, o painel indica qual posto, em outro país, atende quem está lá.

**Why this priority**: transforma o panorama em informação acionável — o que fazer e a quem recorrer — e atende diretamente quem já está no exterior.

**Independent Test**: tocar em um país com alerta e postos, em um país sem posto e no Brasil, e verificar o conteúdo do painel em cada caso.

**Acceptance Scenarios**:

1. **Given** o mapa exibido, **When** o usuário toca em um país, **Then** o mapa se aproxima dele e abre o painel com bandeira, nome, nível de alerta e texto explicativo.
2. **Given** um país com alerta, **When** o painel é aberto, **Then** mostra o link para o alerta original no gov.br com a data do alerta.
3. **Given** um país com região de alerta mais grave, **When** o painel é aberto, **Then** lista essas regiões e seu nível.
4. **Given** um país com postos brasileiros, **When** o painel é aberto, **Then** lista cada posto com tipo e cidade, e ao expandir um posto mostra endereço, telefone de plantão e o link "Abrir no Google Maps".
5. **Given** um país sem posto brasileiro e com posto responsável indicado, **When** o painel é aberto, **Then** informa qual posto, em qual país, atende quem está lá.
6. **Given** o usuário toca no Brasil, **When** o painel é aberto, **Then** mostra o painel próprio do Brasil, sem lista de postos.

---

### User Story 3 - Ver os postos no mapa (Priority: P3)

A partir de certo nível de zoom, o mapa mostra ícones nas cidades com posto brasileiro, com ícones diferentes para embaixada, consulado e escritório. Países sem posto têm um ícone próprio, ligado visualmente ao posto responsável.

**Why this priority**: ajuda a localizar a representação geograficamente, mas o essencial já está na lista do painel (P2).

**Independent Test**: aproximar o mapa de uma região com postos e verificar os ícones por tipo; verificar o ícone e a ligação visual de um país sem posto.

**Acceptance Scenarios**:

1. **Given** o mapa em zoom afastado, **When** o usuário o observa, **Then** os ícones de postos não aparecem.
2. **Given** o usuário aproxima o mapa além do nível definido, **When** o mapa é exibido, **Then** aparecem ícones nas cidades com posto, distintos para embaixada, consulado e escritório.
3. **Given** um país sem posto próprio e com posto responsável, **When** os ícones são exibidos, **Then** o país mostra um ícone próprio ligado visualmente ao posto responsável.

---

### User Story 4 - Buscar um país pelo nome (Priority: P4)

Um campo de busca sugere países enquanto o usuário digita. A busca ignora acentos e maiúsculas e encontra também territórios e dependências (ex.: Groenlândia). Ao escolher um resultado, o mapa vai até o país e abre o painel, como no toque.

**Why this priority**: caminho mais rápido para quem sabe o destino e único caminho viável para países minúsculos no celular.

**Independent Test**: digitar nomes parciais, com e sem acento, em maiúsculas e minúsculas, e escolher uma sugestão.

**Acceptance Scenarios**:

1. **Given** o campo de busca, **When** o usuário digita "mexi", **Then** vê sugestões que incluem "México".
2. **Given** o campo de busca, **When** o usuário digita "GRO" ou "groenlandia", **Then** a Groenlândia (dependência) aparece nas sugestões.
3. **Given** uma lista de sugestões, **When** o usuário escolhe um resultado, **Then** o mapa vai até o país e abre o painel, como no toque.
4. **Given** um termo sem correspondência, **When** o usuário busca, **Then** vê uma mensagem de que nada foi encontrado e o mapa não se move.

---

### User Story 5 - Filtrar o mapa por nível (Priority: P5)

A legenda funciona também como filtro: cada nível tem uma caixa de marcar e todas vêm marcadas ao abrir o site. Desmarcar um nível esmaece os países daquele nível, sem escondê-los nem pintá-los de cinza; marcar de novo devolve a cor. Países esmaecidos continuam podendo ser tocados e encontrados pela busca. Um país com região de alerta mais grave também aparece quando o nível dessa região está marcado. Se todos os níveis forem desmarcados, o mapa mostra uma mensagem e um botão para marcar todos de novo.

**Why this priority**: conveniência para quem quer ver, por exemplo, só os países de "não viaje"; o produto já é útil sem ela.

**Independent Test**: desmarcar e marcar níveis na legenda e verificar o esmaecimento, a interação com países esmaecidos e a mensagem de "nenhum nível marcado".

**Acceptance Scenarios**:

1. **Given** o site recém-aberto, **When** o usuário vê a legenda, **Then** todas as caixas de nível estão marcadas.
2. **Given** todos os níveis marcados, **When** o usuário desmarca "sem alerta", **Then** os países desse nível ficam esmaecidos, sem sumir e sem ficar cinza.
3. **Given** um nível desmarcado, **When** o usuário o marca de novo, **Then** os países voltam à cor original.
4. **Given** um país esmaecido, **When** o usuário o toca ou o busca, **Then** o painel abre normalmente.
5. **Given** só "não viaje" marcado, **When** o mapa é exibido, **Then** o Líbano aparece em destaque por causa da região sul, apesar de seu nível geral ser outro.
6. **Given** todos os níveis desmarcados, **When** o mapa é exibido, **Then** aparece uma mensagem e um botão que, ao ser acionado, marca todos os níveis de novo.

---

### Edge Cases

- **Coleta falha, é parcial ou gov.br fora do ar**: nada muda; o site continua mostrando o resultado da última coleta completa, com a data dela; se tiver mais de 3 dias, mostra aviso de dados desatualizados.
- **Nunca houve uma coleta completa**: todos os países aparecem como "não verificado" e o site informa que os dados ainda não foram obtidos.
- **País com mais de um alerta**: a cor do país segue o mais grave entre os que valem para o país inteiro.
- **Dependência com alerta específico**: o alerta da dependência prevalece sobre o nível herdado do país soberano.
- **País com alerta só para uma região**: o país fica "sem alerta" com o destaque de região, e o painel informa que o alerta vale só para aquela região.
- **País sem posto e sem posto responsável indicado** (hoje, a Líbia): o painel orienta a procurar o Itamaraty.
- **Posto sem endereço exato cadastrado**: o painel mostra a cidade, e o link do Google Maps leva à cidade.
- **Países muito pequenos** (Vaticano, Mônaco), difíceis de tocar no celular: são alcançáveis pela busca.
- **Busca sem resultado**: mostra mensagem e não move o mapa.
- **Toque no oceano ou numa área neutra**: não abre painel de país.
- **Alerta novo ou alterado cujo nível não pode ser determinado com segurança** (inclusive página não lida): o país aparece como "não verificado", com link para o alerta original, até a próxima atualização.
- **Alerta já conhecido (mesmo link e mesma data) cuja página não foi lida numa coleta completa**: o país mantém o nível anterior.
- **Países com territórios distantes** (Rússia, França): o enquadramento do zoom abrange a maior parte do território, sem mostrar o mundo inteiro.
- **Usuário com preferência por movimento reduzido**: as animações do mapa respeitam essa preferência.

## Requirements *(mandatory)*

### Functional Requirements

**Mapa e níveis (P1)**

- **FR-001**: O sistema MUST exibir um mapa-múndi em que cada país tem a cor correspondente ao seu nível: sem alerta, evite viagens não essenciais, não viaje ou não verificado.
- **FR-002**: O sistema MUST usar "não verificado" como nível padrão de qualquer país sem dado confirmado, e MUST NOT exibir "sem alerta" sem confirmação. Um país só conta como "sem alerta" quando não consta na lista de alertas da última coleta completa (FR-040); enquanto nunca tiver havido uma coleta completa, todos os países MUST aparecer como "não verificado".
- **FR-003**: O sistema MUST exibir uma legenda que explica cada nível com texto, de modo que a informação não dependa só da cor.
- **FR-004**: O sistema MUST dar destaque visual adicional a países com alerta para apenas uma região (mais grave que o nível do país, ou único alerta do país).
- **FR-005**: O sistema MUST exibir a data da última atualização dos dados (a data da última coleta completa) e um aviso de que não é um serviço oficial, com link para o portal do Itamaraty.
- **FR-006**: O sistema MUST deixar claro que ausência de alerta não significa que o governo recomenda a viagem.
- **FR-007**: A cor do país MUST seguir o alerta mais grave entre os que valem para o país inteiro. Alertas regionais MUST NOT alterar a cor do país: aparecem só no destaque visual, no painel e no filtro. Se o país só tem alerta regional, ele fica "sem alerta" com o destaque de região, e o painel MUST informar que o alerta vale só para aquela região.
- **FR-008**: Se não for possível determinar com segurança o nível de um alerta novo ou alterado (inclusive quando a página do alerta não foi lida), o sistema MUST mostrar o país como "não verificado", com link para o alerta original, até a próxima atualização. Para um alerta novo cuja página não foi lida, o país MUST ser identificado pelo título do alerta na lista de alertas.
- **FR-008a**: Se um alerta consta na lista com o mesmo link e a mesma data da última coleta completa, mas sua página não foi lida na coleta atual, o país MUST manter o nível anterior.

**Detalhes do país e postos (P2)**

- **FR-009**: Ao tocar em um país, o sistema MUST aproximar o mapa dele e abrir um painel com bandeira, nome, nível de alerta com texto explicativo e regiões com alerta mais grave.
- **FR-010**: O painel MUST mostrar o link para o alerta original no gov.br e a data do alerta.
- **FR-011**: O painel MUST listar os postos brasileiros no país (embaixadas, consulados e escritórios), cada um com tipo e cidade, expansível para endereço, telefone de plantão e o link "Abrir no Google Maps".
- **FR-012**: Para um posto sem endereço exato cadastrado, o painel MUST mostrar a cidade, e o link do Google Maps MUST levar à cidade.
- **FR-013**: Para um país sem posto brasileiro, o painel MUST indicar qual posto, em outro país, atende quem está lá.
- **FR-014**: Para um país sem posto e sem posto responsável indicado (hoje, a Líbia), o painel MUST orientar a procurar o Itamaraty.
- **FR-015**: O painel do Brasil MUST ser próprio e MUST NOT incluir lista de postos.
- **FR-016**: Tocar no oceano ou numa área neutra MUST NOT abrir painel de país.

**Postos no mapa (P3)**

- **FR-017**: A partir de um nível de zoom definido, o sistema MUST exibir ícones nas cidades com posto brasileiro, distintos para embaixada, consulado e escritório.
- **FR-018**: Países sem posto MUST ter um ícone próprio, ligado visualmente ao posto responsável.

**Busca (P4)**

- **FR-019**: O sistema MUST oferecer um campo de busca que sugere países enquanto o usuário digita.
- **FR-020**: A busca MUST ignorar acentos e maiúsculas e MUST encontrar também territórios e dependências (ex.: Groenlândia).
- **FR-021**: Ao escolher um resultado, o sistema MUST levar o mapa até o país e abrir o painel, como no toque.
- **FR-022**: Em busca sem resultado, o sistema MUST mostrar uma mensagem e MUST NOT mover o mapa.
- **FR-023**: Todo país, inclusive os muito pequenos (Vaticano, Mônaco), MUST ser alcançável pela busca.

**Filtro por nível (P5)**

- **FR-024**: A legenda MUST funcionar também como filtro, com uma caixa de marcar por nível, todas marcadas ao abrir o site.
- **FR-025**: Desmarcar um nível MUST esmaecer os países daquele nível, sem escondê-los nem pintá-los de cinza; marcá-lo de novo MUST devolver a cor.
- **FR-026**: Países esmaecidos MUST continuar podendo ser tocados e encontrados pela busca.
- **FR-027**: Um país com região de alerta mais grave MUST aparecer (não esmaecido) quando o nível dessa região estiver marcado.
- **FR-028**: Com todos os níveis desmarcados, o sistema MUST mostrar uma mensagem e um botão para marcar todos de novo.

**Regras do mapa**

- **FR-029**: O mapa MUST cobrir os 198 países da lista do Itamaraty, incluindo o Brasil, e todos MUST poder ser selecionados.
- **FR-030**: O mapa MUST seguir a posição do Brasil sobre territórios: o Kosovo aparece como parte da Sérvia, com a observação de que o Brasil não reconhece a independência; tocar nele abre o painel da Sérvia com essa observação.
- **FR-031**: Dependências (ex.: Groenlândia, territórios ultramarinos) MUST herdar o nível do país soberano e aparecer como "Nome (País)", com a própria bandeira. Quando houver alerta específico para a dependência, esse alerta MUST prevalecer sobre o nível herdado. A Guiana Francesa MUST aparecer separada da França, com o nível da França (salvo alerta específico).
- **FR-032**: Antártida, Saara Ocidental e outras áreas sem soberania reconhecida MUST aparecer neutras, sem nível.
- **FR-033**: Taiwan MUST aparecer como "Taiwan (China)", sem bandeira, e seguir a regra das dependências do FR-031: herda o nível da China, exceto quando houver alerta específico para Taiwan, que então prevalece.
- **FR-034**: As Malvinas MUST aparecer como parte da Argentina; ao tocá-las, o painel da Argentina MUST abrir com, no topo, a observação de que são administradas pelo Reino Unido e de que o Brasil apoia os direitos argentinos e defende a negociação entre os dois países.
- **FR-035**: O painel de cada lugar com regra especial (Kosovo, Taiwan, Malvinas, Saara Ocidental, Antártida e dependências) MUST mostrar uma observação curta com link para a explicação "Sobre as fronteiras deste mapa".
- **FR-036**: Ao lado da legenda, o sistema MUST oferecer o link "Sobre as fronteiras deste mapa", que abre uma explicação curta: o mapa segue a posição oficial do Brasil e lista os casos especiais.
- **FR-037**: O zoom MUST enquadrar a maior parte do território do país, de modo que países com territórios distantes (Rússia, França) não mostrem o mundo inteiro.
- **FR-038**: Para um país sem posto, o enquadramento MUST incluir o posto responsável, a menos que a área fique larga demais.
- **FR-039**: As animações MUST respeitar a preferência do sistema por movimento reduzido.

**Atualização e frescor dos dados**

- **FR-040**: Os níveis exibidos MUST vir sempre da última **coleta completa**. Uma coleta é completa quando a lista de alertas foi lida inteira, no formato esperado, com pelo menos um alerta, e pelo menos 70% das páginas esperadas foram lidas. Uma coleta que não seja completa (falha, gov.br fora do ar ou leitura parcial) MUST NOT alterar nenhum nível: o sistema continua mostrando o resultado da última coleta completa, com a data dela.
- **FR-041**: Se a última coleta completa tiver mais de 3 dias, o sistema MUST mostrar um aviso de dados desatualizados.

**Uso em celular**

- **FR-042**: Todas as funções MUST funcionar em tela de celular com 360 px de largura.

### Key Entities

- **País ou território**: lugar selecionável no mapa. Atributos: nome, bandeira (exceto Taiwan), país soberano (para dependências), indicação de área neutra (sem nível), observação de fronteira quando aplicável.
- **Nível de alerta**: um de sem alerta, evite viagens não essenciais, não viaje ou não verificado, com texto explicativo e ordem de gravidade.
- **Alerta**: publicação do Itamaraty sobre um país. Atributos: nível, data, link para o original no gov.br e abrangência (país inteiro ou região). Um país pode ter vários alertas.
- **Região de alerta**: parte de um país com alerta próprio, que não altera a cor do país (ex.: sul do Líbano, com nível mais grave que o do resto do país).
- **Posto brasileiro**: embaixada, consulado ou escritório. Atributos: tipo, cidade, país, endereço (quando existir), telefone de plantão, localização para o Google Maps.
- **Atendimento por outro posto**: relação entre um país sem posto próprio e o posto, em outro país, que atende quem está lá (pode não existir, como na Líbia).
- **Coleta**: uma tentativa de obter os alertas, completa ou não (ver FR-040). Só a última coleta completa define os níveis exibidos, a data de atualização e o aviso de dados desatualizados.
- **Nota sobre fronteiras**: explicação curta sobre a posição do Brasil e cada caso especial, com observações curtas por lugar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A partir do site aberto, o usuário descobre o nível de alerta de qualquer país em até 10 segundos, pelo toque ou pela busca.
- **SC-002**: Os 198 países da lista do Itamaraty aparecem no mapa e podem ser selecionados.
- **SC-003**: Nenhum país sem dado confirmado aparece como "sem alerta".
- **SC-004**: Quando a coleta funciona, os dados exibidos têm no máximo 24 horas de atraso em relação ao gov.br.
- **SC-005**: Todas as funções descritas funcionam numa tela de celular com 360 px de largura.
- **SC-006**: Todo país com posto brasileiro mostra pelo menos um posto com link funcional para o Google Maps.
- **SC-007**: Toda informação de alerta exibida mostra a data e leva ao alerta original; o aviso de site não oficial está visível em toda visita.
- **SC-008**: Uma coleta que falha ou vem incompleta nunca altera o nível de nenhum país.

## Assumptions

- Os dados de postos brasileiros e de atendimento por outro posto já existem na pasta `arquivos_iniciais/dados/postos` (209 postos em 137 países ou territórios e 60 países atendidos por outro posto) e servem de ponto de partida; as localizações são do centro da cidade, não do endereço exato do posto.
- Os níveis de alerta vêm das páginas públicas do Itamaraty no gov.br.
- A atualização dos dados é feita automaticamente, pelo menos uma vez por dia, sem ação do usuário.
- O site é de uso público, sem login, e todo o conteúdo está em português.
- A legenda e o painel usam texto, e não só cor, para comunicar o nível (acessibilidade).
- O telefone de plantão e o endereço de cada posto podem não estar disponíveis para todos os postos; nesses casos vale a regra de usar a cidade.
- O site exibe a atribuição das fontes de dados, inclusive a licença dos dados de postos, numa página "Sobre" simples.

**Fora do escopo desta especificação**: chat sobre os alertas (especificação separada); vistos, notícias e tela de administração (fases futuras); login, contas de usuário e notificações; outros idiomas além do português. Não criar código preparatório para esses itens.
