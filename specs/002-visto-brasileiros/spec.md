# Feature Specification: Requisitos de visto para brasileiros, por país

**Feature Branch**: `002-visto-brasileiros`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "Feature 002 do Farol Atlas: requisitos de visto para brasileiros, por país. O painel de cada país ganha uma seção \"Visto\" e o globo pode ser colorido por visto, a partir do artigo da Wikipédia em inglês \"Visa requirements for Brazilian citizens\" (CC BY-SA), sem mudar as regras de alerta da feature 001."

## Clarifications

### Session 2026-10-27

- Q: Como tratar casos mistos (rótulos combinados) e qual a lista final de categorias? → A: Vale a categoria mais exigente entre as citadas, na ordem isento de visto < visto na chegada < autorização ou visto eletrônico < visto exigido; "Outra situação" fica fora da ordem, e se qualquer parte de um rótulo combinado cair nela (rótulo desconhecido, entrada proibida, regra especial), o país inteiro fica em "Outra situação", com o rótulo original visível. Continuam as cinco categorias. Quando a fonte indicar que a regra varia conforme o motivo da viagem, o painel mostra a nota "Varia conforme o motivo da viagem", além do rótulo original, e o campo de permanência mostra "Varia conforme o motivo (ver observações)" se os prazos diferirem.
- Q: Quantos países reconhecidos tornam uma coleta de vistos válida? → A: 90% dos países reconhecidos na última coleta válida; na primeira coleta (sem coleta válida anterior), um piso fixo de 150 países reconhecidos.
- Q: A partir de quantos dias os dados contam como "antigos demais"? → A: Mais de 14 dias, contados pela data do dado mostrado para cada país (ver a pergunta sobre vandalismo, abaixo).
- Q: O modo escolhido no globo fica lembrado entre visitas? → A: Não. Toda visita abre em "Alertas".
- Q: O que o painel do Brasil mostra sobre visto? → A: Nada: o painel do Brasil não tem a seção "Visto" (nem "não se aplica"). No modo "Vistos" o Brasil aparece em cor neutra claramente distinta do cinza de "Sem informação de visto". Na informação entregue à interface, a seção ausente vale só para o Brasil; país sem dado vem com estado explícito "sem informação".
- Q: Onde o dono do site revisa os nomes e rótulos que a coleta não reconheceu? → A: No resumo da coleta de vistos (nomes e rótulos não reconhecidos na rodada) e numa lista de todos os pendentes, consultada por um meio restrito ao dono, sem exposição pública, guardados até a revisão; nada aparece no site. Um pendente se resolve sozinho quando uma coleta posterior reconhece o nome ou o rótulo; marcar à mão serve só para "ignorar de propósito", com o motivo registrado. Toda rodada agendada que termine com pendentes escreve uma linha de aviso no registro operacional do sistema, com a quantidade.
- Q: O que fazer com uma coleta válida que muda a categoria de países para menos exigente (risco de vandalismo na fonte)? → A: Cada país tem a sua regra: toda mudança para uma categoria menos exigente (pela ordem de exigência), inclusive de "Outra situação" ou "sem informação" para uma categoria da ordem, fica retida até o dono confirmar (por um meio restrito ao dono), mesmo que seja um único país, e o país mantém os dados anteriores. A **linha do país sair da fonte** (mudança para "sem informação") também fica retida, e o país mantém o último dado válido; se a linha voltar com o valor exibido, a retenção some sozinha. Mudanças para mais exigente e as demais são aplicadas normalmente. O resumo e o registro operacional listam os retidos, e o registro avisa de possível vandalismo em massa se passarem de 10% dos países. A data no painel é a do dado mostrado para aquele país. A primeira coleta não retém nada. Motivo: o erro grave é a direção "menos exigente" (princípio V); reter uma mudança para mais exigente manteria no site a informação mais favorável e desatualizada. Refinamentos aprovados na revisão: passar a aceitar só o documento de identidade (RG) também fica retido, como a categoria; e a retenção vale só para mudanças na fonte: uma transição causada apenas pela atualização do dicionário de rótulos ou de nomes é aplicada sem retenção, porque o dono já decidiu ao atualizar o dicionário.
- Q: Como o modo "Vistos" mostra os países isentos que aceitam só o RG? → A: Com uma variação visual própria do "Isento" (mesmo tom, com padrão ou marca) e item próprio na legenda, "Isento, entrada com RG". Não é uma categoria nova: a categoria continua "Isento de visto", e a ordem de exigência não muda. A variação segue as regras de acessibilidade (contraste WCAG AA, não depender só de cor, legível em 360 px).
- Q: Como mostrar o tempo de permanência, que na fonte é texto livre? → A: Padronizam-se só os formatos conhecidos, com singular e plural ("N days/weeks/months/years" → "N dias/semanas/meses/anos"; "N days in any M-day period" → "N dias a cada período de M dias"). Qualquer outro texto aparece como na fonte, em inglês, com a indicação de que não foi traduzido. Nenhum número é calculado nem convertido, e o serviço de tradução automática não é usado neste campo.
- Q: Onde aparecem a fonte, a data e o aviso de dados desatualizados no modo "Vistos", fora do painel? → A: Numa linha "Vistos: Wikipédia (CC BY-SA), fonte não oficial, coletados em DD/MM/AAAA", com link para o artigo, que fica visível no modo "Vistos" mesmo com a legenda recolhida (inclusive no celular, onde a legenda começa recolhida). O aviso de dados desatualizados (mais de 14 dias) aparece na área de avisos do site, como o da 001, sem abrir o painel.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver o visto no painel do país (Priority: P1)

Quem viaja com passaporte brasileiro abre o painel de um país, tocando no globo ou escolhendo-o na busca que já existe, e vê se precisa de visto. O painel ganha uma seção "Visto", abaixo do alerta, com:

- a **situação**, em uma categoria: isento de visto; autorização ou visto eletrônico; visto na chegada; visto exigido; ou "outra situação", para o que não se encaixa (entrada proibida, regras especiais), sempre com o texto original da fonte disponível;
- o **tempo máximo de permanência**, quando a fonte informa;
- as **observações**, em português e identificadas como tradução automática, com acesso ao texto original em inglês;
- a indicação explícita de que **basta o documento de identidade (RG)**, quando a fonte diz isso;
- a **fonte** (link para o artigo, com o crédito da licença CC BY-SA) e a **data da última coleta válida**;
- o **aviso** de que a informação não é oficial e deve ser conferida com o consulado ou a embaixada do país antes da viagem.

**Why this priority**: é o valor central da feature e já serve sozinho: quem pesquisa um destino passa a ver, no mesmo lugar do alerta, a pergunta seguinte ("preciso de visto?"). Não depende do colorido do globo.

**Independent Test**: com os dados de visto carregados a partir de uma página salva do artigo, abrir o painel de países de cada categoria (por exemplo Argentina, Estados Unidos, Tailândia e Japão), de um país sem informação, de uma dependência e do Brasil, e conferir cada campo da seção.

**Acceptance Scenarios**:

1. **Given** um país cuja fonte diz "visto não exigido", com permanência de 90 dias, **When** o usuário abre o painel, **Then** a seção "Visto" aparece abaixo do alerta com a categoria "Isento de visto" e "90 dias".
2. **Given** um país cuja fonte diz que basta o documento de identidade, **When** o usuário abre o painel, **Then** a seção mostra de forma explícita que o RG é aceito, além da categoria.
3. **Given** um país com observações na fonte, **When** o usuário abre o painel, **Then** vê as observações em português, identificadas como tradução automática, e consegue abrir o texto original.
4. **Given** um país com situação que não se encaixa nas quatro categorias (ex.: entrada proibida), **When** o usuário abre o painel, **Then** vê "Outra situação" junto com o texto original da fonte, sem que o sistema escolha uma das quatro categorias.
5. **Given** um país sem dado de visto, **When** o usuário abre o painel, **Then** a seção mostra "Sem informação de visto" e nenhuma categoria, nunca "isento".
6. **Given** qualquer painel com dado de visto, **When** o usuário o abre, **Then** a seção mostra o link do artigo com o crédito CC BY-SA, a data do dado mostrado para aquele país e o aviso de que a informação não é oficial.
7. **Given** o painel do Brasil, **When** o usuário o abre, **Then** não há seção de visto: nem título, nem fonte, nem aviso, nem "não se aplica".
7a. **Given** a informação entregue à interface para qualquer país com painel que não seja o Brasil, **When** o país não tem dado de visto, **Then** ela traz a seção de visto com o estado explícito "sem informação", e nunca sem a seção.
8. **Given** uma dependência cujo território tem entrada própria na fonte, **When** o usuário abre o painel, **Then** vale a entrada do território.
9. **Given** uma dependência sem entrada própria na fonte, **When** o usuário abre o painel, **Then** vale a entrada do país soberano, com uma nota no painel dizendo isso.
10. **Given** o Kosovo ou as Malvinas, **When** o usuário toca neles, **Then** abre o painel da Sérvia ou da Argentina (convenção da feature 001), com o visto do país soberano.
11. **Given** uma coleta de vistos que falha ou vem inválida, **When** o usuário abre um painel, **Then** os dados da última coleta válida continuam aparecendo, com a data dela.
12. **Given** dados de visto cuja data, para aquele país, tem mais de 14 dias, **When** o usuário abre o painel, **Then** a seção avisa que os dados podem estar desatualizados.
12a. **Given** uma coleta válida em que a fonte passa a dizer "Visa not required" para um país que o site mostra como "Visto exigido", **When** a coleta termina, **Then** o painel desse país continua mostrando "Visto exigido", com a data do dado antigo, e o país aparece como retido no resumo e no registro operacional, até o dono confirmar.
12b. **Given** o mesmo caso com um único país retido e todos os outros inalterados, **When** a coleta termina, **Then** a retenção vale mesmo assim (não há limite mínimo de países), e o registro operacional só avisa de vandalismo em massa se os retidos passarem de 10% dos países reconhecidos.
12c. **Given** uma coleta válida em que a fonte passa a dizer "Visa required" para um país que o site mostra como "Isento de visto", **When** a coleta termina, **Then** a mudança é aplicada normalmente, e o painel já mostra "Visto exigido".
12d. **Given** um país que o site mostra como "Outra situação" ou "Sem informação de visto" e que, por uma mudança no texto da fonte, passa a ser classificado numa categoria da ordem (qualquer uma), **When** a coleta termina, **Then** a mudança fica retida até o dono confirmar, e o painel continua como estava.
12e. **Given** a primeira coleta válida, **When** ela termina, **Then** nenhum país fica retido.
12f. **Given** um país com mudança retida, **When** uma coleta posterior volta ao valor que o site já mostra, **Then** a retenção some sozinha, sem confirmação.
12g. **Given** um país em "Outra situação" por rótulo desconhecido, cujo texto na fonte não mudou, **When** o dono atualiza o dicionário de rótulos e a coleta seguinte reconhece o rótulo, **Then** o país passa à categoria correspondente sem retenção.
12h. **Given** um país "Isento de visto" cuja fonte passa a dizer que basta o documento de identidade (RG), **When** a coleta termina, **Then** a mudança fica retida até o dono confirmar, e o painel continua sem a indicação de RG.
12i. **Given** um país com dado de visto cuja linha desaparece do artigo, **When** a coleta termina, **Then** a saída fica retida: o painel continua com o último dado válido, com a data dele (e o aviso de dados antigos, se passar de 14 dias), e o país aparece como retido no resumo e no registro operacional. **When** uma coleta posterior traz a linha de volta com o valor exibido, **Then** a retenção some sozinha, sem confirmação; **When** o dono confirma, **Then** o país passa a "Sem informação de visto".
13. **Given** um país cuja fonte traz um rótulo combinado, como "eVisa / visto na chegada", **When** o usuário abre o painel, **Then** a categoria é a mais exigente das citadas ("Autorização ou visto eletrônico") e o rótulo original da fonte aparece.
14. **Given** um país cuja fonte indica que a regra varia conforme o motivo da viagem, **When** o usuário abre o painel, **Then** a seção mostra a nota "Varia conforme o motivo da viagem", além do rótulo original e das observações.
15. **Given** um rótulo combinado em que uma parte cai em "Outra situação" (por exemplo, "Visa required / Admission refused" ou "Visa not required / <rótulo desconhecido>"), **When** o usuário abre o painel, **Then** o país inteiro fica em "Outra situação", com o rótulo original visível, e nunca em "Visto exigido" nem em "Isento de visto".
16. **Given** um país cujos prazos de permanência diferem por motivo de viagem, **When** o usuário abre o painel, **Then** o campo de permanência mostra "Varia conforme o motivo (ver observações)" e os prazos aparecem nas observações.
17. **Given** um país cuja fonte diz "90 days in any 180-day period", **When** o usuário abre o painel, **Then** a permanência aparece como "90 dias a cada período de 180 dias".
18. **Given** países cujas fontes dizem "1 month" e "3 months", **When** o usuário abre os painéis, **Then** aparecem "1 mês" e "3 meses", sem conversão para dias.
19. **Given** um país cuja permanência na fonte tem outro formato (por exemplo, "Up to 90 days, extendable"), **When** o usuário abre o painel, **Then** o texto aparece em inglês, como na fonte, com a indicação de que não foi traduzido.

---

### User Story 2 - Colorir o globo por visto (Priority: P2)

Quem planeja uma viagem alterna o globo entre "Alertas" e "Vistos" para ver, de relance, para onde pode ir sem visto. O modo padrão continua sendo "Alertas". No modo "Vistos", cada país é pintado pela categoria de visto, com uma paleta própria e claramente diferente da dos alertas: o verde dos alertas significa apenas "sem alerta publicado" e não pode ser confundido com "isento de visto". Países sem dado ficam em cinza. A legenda muda junto com o modo.

**Why this priority**: dá a visão geral que o painel não dá, mas depende de a P1 (os dados e as categorias) existir. Sem ela, a P1 continua útil; sem a P1, a P2 não tem o que mostrar.

**Independent Test**: com dados de visto carregados, alternar o seletor entre os dois modos, conferir cores, legenda, bordas regionais e o painel aberto por toque em cada modo, também numa janela de 360 px.

**Acceptance Scenarios**:

1. **Given** o site recém-aberto, **When** o usuário olha o globo, **Then** o modo "Alertas" está ativo, exatamente como na feature 001.
2. **Given** o modo "Alertas", **When** o usuário escolhe "Vistos", **Then** cada país passa a ser pintado pela sua categoria de visto, e a legenda passa a explicar as categorias de visto.
3. **Given** o modo "Vistos", **When** o usuário olha o globo, **Then** nenhuma cor de visto se confunde com as cores de alerta (em especial o verde de "sem alerta").
4. **Given** o modo "Vistos", **When** há países sem dado de visto, **Then** eles aparecem em cinza, e a legenda explica o cinza em texto.
5. **Given** o modo "Vistos", **When** o usuário olha países com alerta regional, **Then** as bordas de alerta regional não aparecem; ao voltar para "Alertas", elas reaparecem.
6. **Given** qualquer um dos dois modos, **When** o usuário toca num país, **Then** abre o mesmo painel (alerta, visto e postos), sem diferença entre os modos.
7. **Given** o modo "Vistos" e a legenda, **When** o usuário desmarca uma categoria, **Then** os países daquela categoria ficam esmaecidos, como nos níveis de alerta da feature 001.
8. **Given** uma janela de 360 px de largura, **When** o usuário alterna os modos e abre a legenda, **Then** o seletor, a legenda e o painel continuam utilizáveis, sem depender só de cor.
9. **Given** o modo "Vistos" com a legenda aberta, **When** o usuário olha a legenda, **Then** vê a linha "Vistos: Wikipédia (CC BY-SA), fonte não oficial, coletados em DD/MM/AAAA", com link para o artigo.
10. **Given** o modo "Vistos" com a legenda recolhida (como no celular, ao abrir o site), **When** o usuário olha a tela, **Then** a linha de fonte e data continua visível, sem cobrir o mapa, o aviso nem o "Sobre".
11. **Given** o modo "Alertas", **When** o usuário olha a tela, **Then** a linha de fonte e data dos vistos não aparece, e a legenda recolhida mostra só o botão, como na feature 001.
12. **Given** o modo "Vistos" e dados de visto cuja última coleta válida tem mais de 14 dias, **When** o usuário olha o site sem abrir nenhum painel, **Then** o aviso de dados desatualizados aparece na área de avisos do site.
13. **Given** o modo "Vistos", **When** o usuário olha países "Isento de visto" que aceitam entrada só com o documento de identidade (RG) e países "Isento de visto" que exigem passaporte, **Then** os do RG aparecem com uma variação visual própria do "Isento" (mesmo tom, com padrão ou marca), a legenda tem o item "Isento, entrada com RG", e a diferença não depende só de cor e é legível em 360 px.
14. **Given** o modo "Vistos" e a legenda aberta, **When** o usuário desmarca o subitem "Isento, entrada com RG", **Then** só os países isentos com RG ficam esmaecidos, os demais isentos continuam normais e o item "Isento de visto" mostra o estado misto; **When** desmarca "Isento de visto" e marca só o subitem, **Then** só os países isentos com RG aparecem normais e os demais isentos ficam esmaecidos.

---

### Edge Cases

- **Nunca houve coleta válida de vistos**: todos os países mostram "Sem informação de visto"; no modo "Vistos" o globo fica todo cinza, com a legenda explicando.
- **Coleta de vistos falha, vem em formato diferente ou com poucos países reconhecidos**: nada muda; vale a última coleta válida, com a data dela. Ver FR-010.
- **Mudança na fonte para categoria menos exigente** (inclusive vinda de "Outra situação" ou "sem informação"), **passar a aceitar só o RG** e **a linha do país sair da fonte**: ficam retidas até a confirmação do dono, e o país mantém todos os dados anteriores, com a data deles (FR-010a). **Transição causada só pela atualização do dicionário** (rótulo ou nome que passa a ser reconhecido, com o texto da fonte inalterado): é aplicada sem retenção.
- **Nome da fonte que não corresponde a nenhum país do mapa**: fica registrado para revisão e não afeta nenhum país; nunca é descartado em silêncio.
- **País do mapa sem linha na fonte**: mostra "Sem informação de visto"; o sistema não deduz uma categoria a partir de vizinhos nem de acordos.
- **Rótulo da fonte combinado** (ex.: "eVisa / visto na chegada"; "isento / eVisa") ou que varia conforme o motivo da viagem: ver FR-007 e FR-007a.
- **País em mais de uma linha da fonte com valores diferentes** (ex.: na tabela principal e numa seção de territórios): os valores são tratados como as partes de um rótulo combinado (FR-007): vale a categoria mais exigente, ou "Outra situação" se alguma parte cair nela, e os rótulos originais de todas as linhas aparecem. Se as permanências divergirem, o campo de permanência mostra "Prazos divergentes na fonte (ver observações)", no mesmo padrão do FR-007a, e os textos de todas as linhas aparecem nas observações.
- **Rótulo da fonte desconhecido**, inteiro ou como parte de um rótulo combinado: a categoria é "Outra situação", com o texto original visível (FR-003 e FR-007), o motivo "rótulo desconhecido" e o rótulo registrado para revisão (FR-012a).
- **Permanência num formato que o sistema não conhece**: aparece como na fonte, em inglês, com a indicação de que não foi traduzido; nunca é convertida nem recalculada (FR-004a).
- **Observação sem mudança desde a coleta anterior**: mantém a tradução já feita, sem traduzir de novo.
- **Tradução automática indisponível ou falha**: o painel mostra a observação original em inglês, avisando que ainda não foi traduzida; a categoria e os demais campos não dependem da tradução.
- **Texto da fonte com marcação ou instruções** (por exemplo, HTML ou frases que mandam o sistema fazer algo): é tratado como texto comum, mostrado como está e nunca interpretado.
- **Dependência com entrada própria que difere da do soberano**: vale a do território (FR-013).
- **Kosovo, Malvinas, Taiwan e Porto Rico**: seguem as convenções da feature 001 (FR-013).
- **Brasil e áreas neutras** (Antártida, Saara Ocidental): sem seção de visto e sem categoria; no modo "Vistos" aparecem em cor neutra, e a do Brasil é claramente distinta do cinza de "Sem informação de visto" (FR-023). O Brasil é o único país com painel sem a seção de visto (FR-014).
- **Modo "Vistos" com a legenda recolhida ou com todas as categorias desmarcadas**: valem as mesmas regras da legenda da feature 001 (recolher não altera o filtro; todas desmarcadas mostram mensagem e botão para marcar de novo), com uma exceção: a linha de fonte e data dos vistos continua visível com a legenda recolhida (FR-029).

## Requirements *(mandatory)*

### Functional Requirements

**Painel e informação de visto (P1)**

- **FR-001**: O painel de cada país e território selecionável, exceto o Brasil e as áreas neutras, MUST ter uma seção "Visto", abaixo do alerta, para quem viaja com passaporte brasileiro.
- **FR-002**: A seção MUST mostrar a situação em exatamente uma destas categorias: "Isento de visto", "Autorização ou visto eletrônico", "Visto na chegada", "Visto exigido" ou "Outra situação". A situação MUST também aparecer como texto, e não só como cor ou ícone.
- **FR-003**: Para "Outra situação" (entrada proibida, regras especiais e o que não se encaixa), o painel MUST mostrar sempre o texto original da fonte. O sistema MUST NOT encaixar à força um caso nas outras categorias.
- **FR-004**: A seção MUST mostrar o tempo máximo de permanência quando a fonte o informar, e MUST omitir essa linha quando a fonte não informar (sem inventar "ilimitado" nem "sem prazo").
- **FR-004a**: O tempo de permanência MUST ser padronizado só quando o texto da fonte tem um destes formatos conhecidos, com singular e plural: "N days", "N weeks", "N months" e "N years" viram "N dias", "N semanas", "N meses" e "N anos" ("1 day", "1 week", "1 month" e "1 year" viram "1 dia", "1 semana", "1 mês" e "1 ano"); e "N days in any M-day period" vira "N dias a cada período de M dias" (regra comum na tabela, como a do espaço Schengen). Qualquer outro texto MUST aparecer como a fonte o escreveu, em inglês, com a indicação de que não foi traduzido. O sistema MUST NOT calcular nem converter números (por exemplo, "3 months" não vira "90 dias") e MUST NOT usar o serviço de tradução automática para este campo.
- **FR-005**: A seção MUST mostrar as observações em português, identificadas como tradução automática, com acesso ao texto original em inglês. Se a tradução não estiver disponível, MUST mostrar o texto original, avisando que não foi traduzido.
- **FR-006**: Quando a fonte indicar que basta o documento de identidade (RG), a seção MUST mostrar isso de forma explícita, além da categoria.
- **FR-007**: Quando a fonte usar um rótulo combinado (por exemplo, "eVisa / Visa on arrival" ou "Visa not required / eVisa"), o sistema MUST usar a categoria **mais exigente** entre as que o rótulo cita e MUST NOT escolher a mais favorável. A ordem de exigência, da menos para a mais exigente, é: **isento de visto < visto na chegada < autorização ou visto eletrônico < visto exigido**. "Outra situação" fica fora dessa ordem. Se **qualquer parte** de um rótulo combinado cair em "Outra situação" (rótulo desconhecido, entrada proibida, regra especial), o país inteiro MUST ficar em "Outra situação", e nunca na categoria da outra parte: "Visa required / Admission refused" não pode virar "Visto exigido", e "Visa not required / <rótulo desconhecido>" não pode virar "Isento de visto" (princípio V). O painel MUST mostrar o rótulo original da fonte sempre que ele for combinado, e em "Outra situação" o rótulo original MUST estar visível (FR-003). A lista final de categorias é a das cinco do FR-002. A mesma regra vale para um país que aparece em mais de uma linha da fonte com valores diferentes (por exemplo, na tabela principal e numa seção de territórios): os valores são tratados como as partes de um rótulo combinado, e o painel mostra os rótulos originais de todas as linhas. Se as permanências divergirem, o campo de permanência MUST mostrar "Prazos divergentes na fonte (ver observações)", no mesmo padrão do FR-007a, com os textos de todas as linhas nas observações; o sistema MUST NOT escolher um dos prazos.
- **FR-007a**: Quando a fonte indicar que a regra varia conforme o motivo da viagem (por exemplo, turismo e negócios com regras ou prazos diferentes), o painel MUST mostrar a nota "Varia conforme o motivo da viagem", além do rótulo original e das observações. A categoria continua sendo escolhida pelo FR-007. Quando os prazos de permanência diferem por motivo, o painel MUST mostrar o campo de permanência com o texto "Varia conforme o motivo (ver observações)", e os prazos de cada motivo aparecem nas observações; o sistema MUST NOT escolher um dos prazos para o campo.
- **FR-008**: A seção MUST mostrar a fonte, com link para o artigo da Wikipédia e o crédito da licença CC BY-SA, e a data do dado mostrado para aquele país, em todo painel que mostre dado de visto. A data MUST ser a da coleta em que o dado exibido foi lido da fonte pela última vez, e não a da última coleta do conjunto: um país com mudança retida (FR-010a) continua com a data do dado antigo.
- **FR-009**: A seção MUST mostrar o aviso de que a informação não é oficial e deve ser conferida com o consulado ou a embaixada do país antes da viagem, junto com a informação de visto.

**Regras de dados (P1)**

- **FR-010**: Uma coleta de vistos só MUST substituir os dados atuais se for válida: o artigo foi lido inteiro, no formato esperado, e a quantidade de países reconhecidos atinge o mínimo. Uma coleta inválida MUST NOT alterar nenhum dado; vale a última coleta válida, com a data dela. A unidade dos dois critérios é a mesma, o número de países reconhecidos: o mínimo é **90% dos países reconhecidos na última coleta válida**. Na primeira coleta, quando ainda não existe coleta válida anterior, o mínimo é um piso fixo de **150 países reconhecidos**.
- **FR-010a**: Numa coleta válida, toda **mudança na fonte** que leve um país **para uma categoria menos exigente** MUST ficar retida até o dono confirmar, por um meio restrito ao dono e sem exposição pública, mesmo que seja um único país. "Menos exigente" segue a ordem do FR-007 (isento < visto na chegada < autorização ou visto eletrônico < visto exigido) e inclui a passagem de "Outra situação" ou de "sem informação" para qualquer categoria da ordem. Passar a aceitar **só o documento de identidade (RG)** (FR-006) também MUST ficar retido, como a categoria, e o mesmo vale para **a linha do país deixar de existir na fonte**, que é uma mudança para "sem informação": o país continua com o último dado válido até o dono confirmar. Enquanto a mudança estiver retida, o país MUST continuar com todos os dados anteriores (categoria, permanência, observações e demais campos). Mudanças para uma categoria mais exigente ou para "Outra situação", e as demais mudanças (permanência, observações, outras indicações), MUST ser aplicadas normalmente. Regras do que fica retido:
  - a retenção vale só para mudanças **na fonte**: se o texto da fonte para o país não mudou desde a coleta anterior e a transição vem apenas de uma atualização do dicionário de rótulos ou de nomes (por exemplo, "Outra situação" → categoria, "sem informação" → categoria), ela MUST ser aplicada sem retenção, porque o dono já decidiu ao atualizar o dicionário;
  - a primeira coleta válida não retém nada, porque não há dado anterior;
  - o dado retido é o da coleta mais recente; confirmar aplica esse dado (no caso da linha que saiu da fonte, o país passa a "sem informação"), e se uma coleta posterior voltar ao valor que já é exibido, a retenção some sozinha. Assim, um vandalismo que apaga linhas e é desfeito nunca deixa países em "sem informação" à espera de uma restauração manual;
  - o resumo da coleta e o registro operacional do sistema MUST listar os países retidos, com a categoria exibida e a lida; se os retidos passarem de 10% dos países reconhecidos na coleta, o registro MUST avisar de possível vandalismo em massa na fonte;
  - o dono MUST poder listar os países retidos e confirmar um país ou todos, por esse mesmo meio restrito.
- **FR-011**: O sistema MUST NOT mostrar "Isento de visto" nem qualquer outra categoria para um país sem dado. País sem informação MUST mostrar "Sem informação de visto". Enquanto nunca houver coleta válida, todos os países ficam assim.
- **FR-012**: Cada país da fonte MUST ser ligado ao mesmo país do mapa pelo código ISO. Nomes da fonte que o sistema não reconhece MUST ser registrados para revisão, com o nome e a data, e MUST NOT ser descartados em silêncio.
- **FR-012a**: Cada rótulo de visto da fonte que o sistema não reconhece (inteiro ou como parte de um rótulo combinado) MUST ser registrado para revisão, com o rótulo, o país onde apareceu e a data, e MUST NOT ser descartado em silêncio. Enquanto não for reconhecido, o país fica em "Outra situação" (FR-007), com o motivo "rótulo desconhecido".
- **FR-012b**: O dono do site MUST poder revisar o que a coleta não reconheceu, por um meio restrito ao dono e sem exposição pública, sem que nada disso apareça no site:
  - o resumo da coleta de vistos (no estilo do resumo da coleta de alertas) MUST listar os nomes de países e os rótulos de visto não reconhecidos naquela rodada;
  - os registros MUST ficar guardados como pendentes, e o dono MUST poder listar todos os pendentes;
  - um item pendente MUST ser resolvido automaticamente quando uma coleta posterior reconhecer o nome ou o rótulo (depois de o dicionário ser atualizado);
  - marcar um item manualmente MUST servir só para "ignorar de propósito" (por exemplo, um território que não existe no mapa) e MUST exigir o motivo, que fica registrado;
  - toda rodada agendada que terminar com itens pendentes MUST escrever uma linha de aviso no registro operacional do sistema, com a quantidade de pendentes.
- **FR-013**: Para territórios e dependências, o sistema MUST usar a entrada própria do território, quando a fonte a tiver (ex.: Hong Kong, Macau, territórios ultramarinos). Sem entrada própria, MUST usar a do país soberano e o painel MUST trazer uma nota dizendo isso. As convenções da feature 001 MUST ser mantidas: Kosovo e Malvinas abrem o painel da Sérvia e da Argentina, com o visto do soberano; Taiwan aparece como "Taiwan (China)"; Porto Rico segue a regra das dependências.
- **FR-014**: O painel do Brasil MUST NOT ter a seção "Visto": nem título, nem fonte, nem aviso, e sem texto de "não se aplica". Áreas neutras continuam sem painel. Na informação entregue à interface, a seção de visto ausente MUST valer só para o Brasil. Todo outro país ou território com painel MUST vir sempre com a seção de visto, e um país sem dado de visto MUST vir com um estado explícito de "sem informação", nunca com a seção ausente, para a interface não confundir os dois casos.
- **FR-015**: Se os dados de visto ficarem antigos demais, o painel MUST avisar que podem estar desatualizados. Os dados contam como "antigos demais" quando a data do dado mostrado para aquele país (FR-008) tem **mais de 14 dias** (o dobro do intervalo semanal); assim, um país com mudança retida há mais de 14 dias também recebe o aviso. O aviso do site (FR-029a) vale quando a última coleta válida do conjunto tem mais de 14 dias.
- **FR-016**: Observações cujo texto não mudou desde a última coleta MUST manter a tradução já feita, sem nova tradução. Observações novas ou alteradas MUST ser traduzidas, e a tradução MUST sempre vir marcada como automática.
- **FR-017**: Textos da fonte (nomes, rótulos, observações) e traduções MUST ser tratados como dados: o site MUST NOT inseri-los como HTML sem sanitizar e MUST NOT seguir instruções contidas neles.

**Coleta**

- **FR-018**: Os dados de visto MUST ser atualizados automaticamente, pelo menos uma vez por semana, sem ação do usuário.
- **FR-019**: A coleta de vistos MUST seguir as regras de coleta responsável da constituição: respeitar o `robots.txt` e os termos do site, identificar-se de forma honesta com um contato, pausar entre requisições e parar, registrando o motivo, se for bloqueada ou encontrar verificação humana.
- **FR-020**: Esta feature MUST NOT alterar as regras, os níveis nem as cores de alerta da feature 001, nem a busca por país.

**Colorir o globo por visto (P2)**

- **FR-021**: O site MUST oferecer um seletor "Alertas | Vistos" para alternar o que o globo mostra. O modo padrão MUST ser "Alertas". O modo escolhido MUST NOT ser lembrado entre visitas: toda visita, e todo recarregamento da página, abre em "Alertas".
- **FR-022**: No modo "Vistos", cada país MUST ser pintado pela sua categoria de visto, com uma paleta própria, claramente diferente da dos alertas. Nenhuma cor de visto MUST se confundir com o verde de "sem alerta" nem com as outras cores de alerta.
- **FR-022a**: No modo "Vistos", os países "Isento de visto" que aceitam entrada só com o documento de identidade (RG) (FR-006) MUST ganhar uma variação visual própria do "Isento" (por exemplo, o mesmo tom com padrão ou marca), com item próprio na legenda: "Isento, entrada com RG". Não é uma categoria nova: a categoria continua "Isento de visto", e a ordem de exigência não muda. A variação MUST seguir as regras do FR-027 (contraste WCAG AA, não depender só de cor, legível em 360 px). Na legenda, "Isento, entrada com RG" MUST ser um subitem de "Isento de visto": filtrar por "Isento de visto" inclui os países com RG, e o subitem permite filtrar só os países com RG. O comportamento segue o de uma caixa de marcar com subitem: marcar ou desmarcar "Isento de visto" marca ou desmarca também o subitem; desmarcar só o subitem esmaece apenas os países com RG, e o item pai passa a mostrar o estado misto; marcar só o subitem, com o item pai desmarcado, mostra apenas os países com RG e esmaece os demais isentos. O estado misto MUST ser comunicado também por texto ou atributo acessível, e não só por cor, e o filtro do subitem vale para os países desenhados com a sua aparência (FR-024).
- **FR-023**: No modo "Vistos", países sem dado MUST aparecer em cinza, explicado na legenda. O Brasil e as áreas neutras MUST aparecer em cor neutra, sem categoria. A cor neutra do Brasil MUST ser claramente distinta do cinza de "Sem informação de visto", para ninguém ler o Brasil como um país sem dado; a legenda MUST explicar a cor do Brasil em texto.
- **FR-024**: A legenda MUST mudar junto com o modo, explicar cada categoria com texto e continuar funcionando como filtro (caixa de marcar por categoria; desmarcar esmaece, sem esconder nem pintar de cinza; países esmaecidos continuam tocáveis), como na feature 001. O filtro de cada modo MUST ser independente do filtro do outro.
- **FR-025**: As bordas de alerta regional MUST aparecer só no modo "Alertas".
- **FR-026**: Tocar num país MUST abrir o mesmo painel nos dois modos.
- **FR-027**: O seletor, a legenda e as cores do modo "Vistos" MUST atender às mesmas regras de acessibilidade e de celular da feature 001: contraste WCAG AA, informação que não dependa só de cor, funcionamento em 360 px de largura, respeito à preferência por movimento reduzido e uso pelo teclado.
- **FR-028**: Dependências MUST ser pintadas, no modo "Vistos", pela categoria que vale para elas (a própria ou a do soberano, conforme FR-013). Kosovo MUST ser pintado como a Sérvia e as Malvinas como a Argentina.
- **FR-029**: No modo "Vistos", o site MUST mostrar a linha "Vistos: Wikipédia (CC BY-SA), fonte não oficial, coletados em DD/MM/AAAA", com link para o artigo, onde a data é a da última coleta válida. A linha MUST ficar visível também com a legenda recolhida, inclusive no celular, onde a legenda começa recolhida (FR-024a da feature 001); essa é a única exceção à regra de que a legenda recolhida deixa só o botão. A linha MUST NOT cobrir o mapa, o aviso de site não oficial nem o link "Sobre", MUST caber em 360 px de largura (quebrando em mais de uma linha, se preciso) e MUST NOT aparecer no modo "Alertas". Sem nenhuma coleta válida, a linha MUST dizer que ainda não há dados de visto, em vez de mostrar uma data.
- **FR-029a**: No modo "Vistos", quando os dados de visto estiverem antigos demais (FR-015), o aviso de dados desatualizados MUST aparecer também na área de avisos do site, como o da feature 001, sem precisar abrir um painel.

### Key Entities

- **Requisito de visto**: o que a fonte diz sobre a entrada de brasileiros num país ou território. Atributos: país ou território, categoria de visto, rótulo original da fonte, tempo máximo de permanência (quando houver: o texto original da fonte e, se for um formato conhecido, a versão padronizada em português), indicação de que basta o RG, indicação de que a regra varia conforme o motivo da viagem, motivo de "Outra situação" quando for o caso (rótulo conhecido, mapeado de propósito para ela, ou rótulo desconhecido), observações (original e tradução), se vale a entrada própria do território ou a do soberano.
- **Categoria de visto**: uma entre isento de visto, visto na chegada, autorização ou visto eletrônico e visto exigido (nessa ordem de exigência, da menor para a maior), mais "outra situação", que fica fora da ordem. Cada uma tem texto explicativo e cor própria no globo. "Isento de visto" tem uma variação de exibição para entrada só com o RG, que não é uma categoria nova. Quem não tem dado não tem categoria.
- **Observação de visto**: texto da fonte em inglês, com a tradução automática em português quando existir; só é traduzida de novo se o texto mudar.
- **Coleta de vistos**: uma tentativa de ler o artigo, válida ou não. Só uma coleta válida pode mudar o que é exibido, e cada país mostra a data do dado exibido.
- **Mudança retida**: mudança de um país para uma categoria menos exigente, lida numa coleta válida e ainda não confirmada pelo dono. Atributos: país, categoria exibida, categoria lida, dados lidos e data da coleta. Some quando o dono confirma ou quando a fonte volta ao valor exibido.
- **Nome não reconhecido**: nome da fonte que não corresponde a nenhum país do mapa, guardado para revisão. Estado: pendente, resolvido (reconhecido numa coleta posterior) ou ignorado de propósito, com o motivo.
- **Rótulo desconhecido**: rótulo de visto da fonte que o dicionário de rótulos do sistema não cobre, guardado para revisão com o país onde apareceu e a data. Tem os mesmos estados do nome não reconhecido.
- **Modo do globo**: "Alertas" ou "Vistos"; define como o globo é pintado e qual legenda aparece.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Na primeira coleta válida, pelo menos 95% dos países clicáveis do mapa têm um dado de visto. Contam qualquer das quatro categorias da ordem de exigência e também "Outra situação", mas só quando ela vem de um rótulo conhecido, mapeado de propósito para ela (por exemplo, entrada proibida). País em "Outra situação" por rótulo desconhecido não conta: é lacuna do dicionário de rótulos, não dado. A base de cálculo são os países e territórios que abrem painel, excluindo o Brasil e as áreas neutras sem painel. A meta é fixa em 95%; o resultado da primeira coleta é registrado e, se ficar abaixo, a feature não está pronta.
- **SC-002**: Nenhum país sem dado aparece como "Isento de visto" ou com qualquer outra categoria, nem no painel nem no globo.
- **SC-003**: Todo painel que mostra dado de visto mostra a fonte com o crédito CC BY-SA, a data do dado mostrado para aquele país e o aviso de que a informação não é oficial. No modo "Vistos", a fonte, a indicação de fonte não oficial e a data aparecem também no próprio mapa, sem abrir painel e com a legenda aberta ou recolhida.
- **SC-004**: A partir do site aberto, o usuário descobre se precisa de visto para qualquer país em até 10 segundos, pelo toque ou pela busca.
- **SC-005**: O modo "Vistos" é legível e utilizável numa tela de 360 px de largura: o seletor e a legenda cabem, e o painel abre normalmente.
- **SC-006**: Nenhuma cor do modo "Vistos" pode ser confundida com uma cor do modo "Alertas": cada categoria de visto tem texto próprio na legenda, e as cores de visto têm contraste suficiente para ser distinguidas entre si e do cinza de "sem dado". A variação "Isento, entrada com RG" se distingue do "Isento" comum sem depender só de cor.
- **SC-007**: Uma coleta de vistos inválida nunca altera nenhum dado exibido.
- **SC-008**: Quando a coleta funciona, os dados exibidos têm no máximo 7 dias de atraso em relação ao artigo, exceto os dos países com mudança retida (FR-010a), que mantêm a data do dado antigo.
- **SC-009**: Todo nome da fonte não reconhecido fica registrado: nenhuma linha lida do artigo some sem aparecer em um país ou no registro de nomes para revisão. Os pendentes aparecem no resumo da coleta e na lista de pendentes que o dono consulta (FR-012b).
- **SC-010**: Ao concluir a feature, não há nenhum rótulo desconhecido pendente na tabela atual do artigo: o dicionário de rótulos cobre todos os rótulos existentes, e a lista de pendentes do dono (FR-012b) não mostra nenhum rótulo, pendente nem ignorado, depois da primeira coleta válida. Rótulos novos que o artigo ganhar depois continuam indo para o registro (FR-012a).
- **SC-011**: Nenhuma mudança para uma categoria menos exigente chega ao site sem a confirmação do dono, mesmo que seja um único país; mudanças para mais exigente chegam ao site na mesma coleta.

## Assumptions

- A fonte única é o artigo da Wikipédia em inglês "Visa requirements for Brazilian citizens", de licença CC BY-SA. Ela não é oficial, e o site diz isso. Pelo que se viu do artigo, há uma tabela principal por país (com rótulos como "Visa not required", "Visa on arrival", "eVisa", "Electronic Travel Authorisation", "Visa required" e "Freedom of Movement", este último usado para entrada só com o RG) e seções à parte para territórios dependentes, disputados ou restritos. A estrutura exata é verificada no plano.
- A coluna de reciprocidade e as restrições que não são de visto (validade do passaporte, vacinas, antecedentes) ficam fora do que a seção mostra, salvo quando aparecerem nas observações da linha do país.
- Os países e territórios do mapa são os mesmos da feature 001 (198 países da lista do Itamaraty, mais dependências), e o código ISO deles é a chave de ligação com a fonte.
- Entrada só com o RG ("Freedom of Movement") conta na categoria "Isento de visto", com a indicação explícita do RG.
- O seletor de modo e o filtro da legenda por modo existem só no mapa; a busca por país continua igual.
- O filtro por categoria de cada modo vale enquanto a página estiver aberta; guardá-lo entre visitas não faz parte desta feature, como também não o modo escolhido (FR-021). A escolha de legenda recolhida ou aberta da feature 001 vale para os dois modos.
- A tradução das observações usa o mesmo tipo de serviço de modelo de linguagem já configurável do projeto, sem exigir serviço pago.
- O site continua público, sem login, e todo o conteúdo em português.
- A atualização semanal é suficiente: as regras de visto mudam pouco, e o aviso de "conferir com o consulado" cobre o intervalo.

**Fora do escopo desta especificação**: a busca por país (já existe); vistos para outras nacionalidades; requisitos de saúde, vacinas e documentos além do visto, salvo quando aparecerem nas observações da fonte; o chat com RAG (feature 003); mostrar a reciprocidade; qualquer fonte diferente da Wikipédia. Não criar código preparatório para esses itens.
