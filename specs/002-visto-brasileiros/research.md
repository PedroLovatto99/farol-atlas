# Pesquisa (Fase 0): Requisitos de visto para brasileiros

Este documento registra o que foi conferido na fixture, no `robots.txt` da Wikipédia e no código da 001, as decisões técnicas e os pontos que dependem de aprovação. As escolhas de stack vêm da 001 e não se repetem aqui.

> **Estado: levantamento APROVADO em 28/10/2026** (O1 a O12, seção 4, com os ajustes registrados lá). A seção 3 é o levantamento obrigatório antes do dicionário. O **conteúdo** dos três arquivos do dicionário (rótulos, nomes e regras por país) fica para a implementação: aqui está decidido o que eles têm de dizer, e cada entrada leva um teste (`contracts/dicionario-de-rotulos.md`).

## 1. Conferências feitas

| Item | Resultado |
|---|---|
| `robots.txt` de `en.wikipedia.org` | Lido em 27/10/2026 (HTTP 200, 28 KB). Para `User-agent: *`: `Disallow: /w/`, `Disallow: /api/`, `Disallow: /wiki/Special:`. Sem `Crawl-delay` para robôs genéricos. Testado com o protego e o User-Agent do projeto: a página `/wiki/Visa_requirements_for_Brazilian_citizens` é **permitida**; `/w/api.php`, `/w/index.php?…action=raw`, `/api/rest_v1/…` e `/wiki/Special:Export/…` são **proibidos**. |
| Fixture | Página do artigo salva em `backend/tests/fixtures/wikipedia/` (1,5 MB, revisão 1380975986, última edição em 19/10/2026), com `README.md` de origem, data e licença. Uma requisição à página e uma ao `robots.txt`. |
| Data da última edição | O **JSON-LD** (`dateModified`: `2026-10-19T05:08:59Z`) é legível por máquina e bate com o rodapé ("last edited on 19 October 2026, at 05:08 (UTC)") e com `wgRevisionId`. O cabeçalho HTTP `Last-Modified` dizia **26/10/2026 19:44 GMT**, uma semana depois da edição (reflete o cache), e **não serve**. Decisão: ler `dateModified`; se faltar ou não for uma data, cair no rodapé; se nenhum dos dois valer, a coleta é rejeitada como "formato inesperado". |
| Falso positivo do cliente HTTP | O cliente da 001 (`parece_verificacao`) procura "captcha" no HTML inteiro. A página da Wikipédia o contém **4 vezes**, todas dentro de um `<script>` de configuração (`wgConfirmEditCaptchaNeededForGenericEdit`). Sem correção, **a coleta pararia achando que caiu na verificação humana**. Fora do **conteúdo inline** de `<script>` e `<style>` a página não tem nenhum dos três sinais (conferido: 4 ocorrências no total, 0 fora). Decisão (aprovada, sem enfraquecer a detecção da 001): o detector descarta só o **texto entre as tags** de `<script>` e `<style>`; atributos (`src`, `class`, `id`, `data-*`) e o texto visível continuam sendo examinados. Assim, `<iframe src=".../recaptcha/...">`, `<div class="g-recaptcha">` / `h-captcha`, um `<script src=".../captcha.js">` e as frases "testing whether you are a human" / "prevent automated spam" continuam sendo detectados. Testes: os da 001 passam **sem alteração** (só os imports mudam); mais um com desafio real (iframe e div de captcha visíveis) que tem de continuar sendo detectado; mais um com a fixture, que não pode ser. |
| User-Agent | O código **já usa "FarolAtlas/0.1"** (`NOME_DO_PROJETO`); "MapaAlertasBR" só aparece em `ferramentas/testar_coleta.py` (o script antigo). O formato atual, `FarolAtlas/0.1 (projeto pessoal; contato: <contato>)`, não traz a biblioteca. A política da Wikimedia pede `nome/versão (contato) biblioteca/versão`. Decisão: `FarolAtlas/0.1 (<contato>; projeto pessoal) python-requests/<versão>`, com `CONTATO_COLETA=https://github.com/PedroLovatto99/farol-atlas`. O valor de exemplo do `.env.example` (`https://github.com/seu-usuario`) continua bloqueando a coleta, como hoje. |
| Onde estão o cliente HTTP e o `Baixador` | `ClienteEducado`, `Pagina`, `SessaoHttp`, `RespostaHttp` e `parece_verificacao` estão em `farol.coleta.cliente_educado`; o `Baixador` (Protocol), em `farol.coleta.servico_alertas`. O módulo `vistos` não pode importar `coleta`. Decisão: mover os cinco para `farol.infra` (`infra/cliente_http.py`), sem mudar o comportamento, exceto a correção acima e o User-Agent. |
| `pycountry` em produção | Está no grupo `geo` (desenvolvimento), **fora da imagem**. A ligação de nomes aos códigos ISO não pode depender dele em produção. Decisão: um dicionário de nomes versionado no pacote (seção 3.4); o `pycountry` serviu só para este levantamento. |
| Contrato da API e testes | `tests/contrato` compara o OpenAPI gerado com `specs/001-…/contracts/openapi.yaml` **por inteiro** (mesmas rotas, mesmos esquemas). Acrescentar `/vistos` e o campo `visto` quebraria esses testes. Decisão (aprovada com condição): `specs/002-…/contracts/openapi.yaml` é o contrato **completo** (001 + mudanças da 002), e os testes passam a apontar para ele. O arquivo da 001 fica como histórico da v1.0. **Condição: a parte da 001 não muda.** Conferido por script: as rotas `/mapa`, `/paises/{codigo}` e `/saude` são idênticas às da 001, todos os esquemas da 001 são idênticos, **exceto `Pais`**, que só ganha a propriedade `visto` (e a coloca em `required`); os outros 10 esquemas e a rota `/vistos` são novos. Para travar isso, um teste de contrato próprio (`tests/contrato/test_contrato_002_preserva_001.py`) lê os dois arquivos e **falha** se, em relação à 001: uma rota ou operação sumir ou mudar; um parâmetro ou uma resposta mudar; um esquema sumir; uma propriedade existente sumir, mudar de tipo ou deixar de ser obrigatória; ou aparecer qualquer propriedade nova fora da lista aprovada (hoje só `Pais.visto`). |
| Job semanal x job mensal de postos | O job de postos roda no **dia 1, 05:43**. Segunda-feira 05:43 coincidiria com ele quando o dia 1 cai numa segunda. Como o worker tem um fio só, o de vistos esperaria os ~45 minutos dos postos (dentro da tolerância de atraso, mas desnecessário). Proposta: **segunda-feira 05:13** (ver O5). |

## 2. Decisões

### D1. Módulo `vistos` e fronteiras (import-linter)
- Camadas: `api | worker` > `mapa | coleta | classificacao | vistos` > `dominio` > `infra`. O contrato "casos de uso independentes" ganha `vistos`; ganha também o contrato "só a interface pública de vistos" (`farol.vistos.*` proibido para todos os outros) e `farol.vistos` entra como origem nos outros contratos "só a interface pública". Passam de 7 para 8 contratos.
- `vistos` importa só `dominio` e `infra`. `mapa` não conhece `vistos`: quem junta painel e visto é a `api`, numa função de composição fina (`api/composicao.py`) que chama `montar_painel` e `montar_visto_do_pais`; a rota só converte e devolve. Nenhuma regra de negócio na rota (princípio III).
- O Brasil (`BR`) vira constante do `dominio` (hoje é local de `mapa/painel.py`), usada por `mapa` e `vistos`.
- O tradutor é um Protocol de `vistos` (`Tradutor`); o adaptador `TradutorLangChain` usa `init_chat_model` + `with_structured_output` (Pydantic). Os **argumentos por provedor** (chave, URL do Ollama, tempo limite) saem de `classificacao/cadeia.py` para uma função pura em `infra` (`argumentos_do_modelo`), que não importa LangChain; os dois módulos a usam. Variável nova: `LLM_TRADUTOR` (padrão: o mesmo modelo do classificador). Nos testes, um tradutor falso.

### D2. Fonte: só a página do artigo
- Uma requisição à página (e a leitura do `robots.txt`, em cache por execução), pelo `ClienteEducado` movido para a `infra`: protego antes da requisição, pausa, User-Agent honesto, parada em bloqueio (403/429) ou verificação humana.
- **Não usar `/w/api.php` nem `/api/rest_v1`** (proibidos, seção 1). A alternativa seria o dump mensal da Wikimedia, descartada: gigante e mensal, sem ganho para um artigo de 1,5 MB.
- O texto das células vira **texto puro** (marcas de referência `[2]` e `<sup>` removidas; nenhum HTML da fonte é guardado nem exibido; princípio VIII).

### D3. Quando coletar
- Job semanal no APScheduler, segunda-feira, fuso `America/Sao_Paulo`, no mesmo executor de um fio (um job por vez). Horário: ver O5.
- **Estabilidade:** com a página baixada, lê-se `dateModified`. Se a última edição for de menos de 24 horas, a rodada é **adiada** (nada é processado, a página é descartada, a tentativa é registrada como `adiada`) e repete no dia seguinte. Depois de 3 adiamentos seguidos, coleta mesmo assim; a retenção protege. Isso custa 2 requisições por tentativa (a página e o `robots.txt`).
- **Falha técnica** (timeout, 5xx, formato inesperado): nova tentativa no dia seguinte, até 3 falhas seguidas; depois, só na próxima segunda (limite meu, ver O6). **Bloqueio** (403, 429, verificação humana): para sem insistir e registra o motivo; a próxima tentativa é a da segunda seguinte.
- Na partida do worker: coleta se a última tentativa for de mais de 7 dias, ou se foi `adiada`/`falhou` em dia anterior e ainda cabe tentar. O estado vem da tabela `coleta_vistos`, não de memória.

### D4. Dados, hashes, tradução e retenção
- **Hash de linha:** SHA-256 do JSON canônico das linhas normalizadas da fonte de um território (nome, rótulo, permanência, notas; várias linhas ordenadas). Serve para (a) saber se a **fonte mudou** (retenção, FR-010a) e (b) a tradução: o hash do **texto de cada observação** é a chave para reaproveitar a tradução.
- **Regra de retenção** (função pura `decidir_retencao`, testada em tabela): compara o candidato (leitura de hoje, já passada pelo dicionário) com o exibido.
  1. Hash da fonte igual ao exibido e derivados diferentes ⇒ mudança do **dicionário**: aplica, sem retenção.
  2. Hash da fonte diferente e a mudança é para categoria menos exigente (ordem do FR-007; vindo de "Outra situação" ou "sem informação" para qualquer categoria da ordem) **ou** passa a aceitar só o RG ⇒ **retém**.
  3. Qualquer outra mudança ⇒ aplica.
  4. Primeira coleta válida ⇒ aplica tudo.
- **Estados da retenção:** `pendente`, `confirmada`, `rejeitada` (vale enquanto a fonte mantiver **o mesmo hash lido**), `revertida` (a fonte voltou ao valor exibido: resolução automática) e `superada` (a fonte mudou de novo para outro valor; o registro antigo fecha e a decisão recomeça). O estado `superada` é acréscimo meu (O7).
- **Tradução em lote:** só as observações novas ou alteradas (hash novo), em chamadas de até 20 observações, com saída estruturada (lista de pares índice → tradução, validada pelo Pydantic: mesma quantidade, nada vazio, tamanho limitado). O texto da fonte vai entre delimitadores e o modelo recebe a instrução de tratá-lo como dado (princípio VIII). Se a chamada falhar, a observação fica sem tradução (o painel mostra o original, avisando) e **tenta de novo na coleta seguinte**: a tradução ausente não impede a coleta de ser válida.
- **Uma coleta só substitui os dados se for válida** (FR-010): artigo lido inteiro, no formato esperado (tabela principal com os 4 cabeçalhos esperados), e países reconhecidos ≥ 90% dos reconhecidos na última coleta válida, ou ≥ 150 na primeira. "Reconhecidos" = códigos distintos do mapa ligados a alguma linha, sem contar os ignorados de propósito.
- Os pendentes de nomes e rótulos (FR-012b) ficam na tabela `item_para_revisao`; somem sozinhos (`resolvido`) quando uma coleta posterior reconhece o nome ou o rótulo. Só nome pode ser `ignorado`, com motivo. A mesma tabela guarda a **lista de revisão das regras por país** (tipo `regra`, decisão O4): cada entrada de `regras_por_pais.yaml` guarda o hash da observação em que se baseou; quando a observação do país muda e o hash deixa de bater, o país entra nessa lista até o dono reconfirmar a regra. Regra pendente **não** invalida a coleta e **não** pode ser "ignorada".

### D5. Dicionários dentro do pacote
- `backend/src/farol/vistos/dicionario/rotulos.yaml`, `nomes.yaml` e `regras_por_pais.yaml`. O `nomes.yaml` lista **todos** os nomes da fonte (cerca de 250: os ~228 que se ligam a um código e os 21 ignorados), porque o `pycountry` não vai para produção; um script de desenvolvimento gera o rascunho a partir dele e as 18 aliases são feitas à mão. Ficam no pacote (e não em `dados/`) porque são regras de leitura do código, testadas com ele, e a imagem do Docker só copia `src` (`dados/` é montado só na migração). Cada entrada tem um teste (tabela parametrizada).
- A ligação usa a lista de territórios do banco (`territorio.codigo`) e as convenções da 001 que já estão nele: `identidade_do_soberano` (Kosovo, Malvinas), dependências e soberanos. As observações e regras especiais continuam em `dados/territorios/observacoes.yaml`; nada é duplicado.

### D6. API e contrato
- Só leitura. `GET /paises/{codigo}` ganha `visto` (objeto; **nulo só para o Brasil**; um país sem dado vem com `situacao = sem_informacao`). Rota nova `GET /vistos`: resposta leve para o globo (`codigo`, `situacao`, `aceita_rg` por território, mais fonte, data da última coleta válida e `desatualizado`), com `nao_se_aplica` explícito para o Brasil. Tem teste que limita o número de consultas.
- `/mapa` **não muda**. O frontend busca `/vistos` **sob demanda**, ao escolher o modo "Vistos" pela primeira vez, e não no carregamento (princípio III; ver O10). **Se a busca falhar** (rede, 5xx, resposta fora do contrato), a legenda do modo Vistos mostra o erro com o botão "Tentar de novo" e os territórios **não são pintados de cinza**: cinza significa só "sem informação de visto" (`contracts/mapa-props-vistos.md`, "Carregamento e erro").
- Contrato completo em `contracts/openapi.yaml` (seção 1, "Contrato da API e testes").

### D7. Frontend
- **Estado:** `modo` (`alertas` | `vistos`, padrão `alertas`, nunca guardado) e `vistosMarcados` (filtro do modo Vistos, independente do filtro de alertas, só em memória), no mesmo reducer.
- **Mapa:** `TerritorioDesenhado` troca `nivel` por `preenchimento: { cor, padrao }`, calculado fora do adaptador por funções puras (uma para alertas, uma para vistos). `bordaRegional` vem `null` no modo Vistos (FR-025). O adaptador continua sendo o único que importa `maplibre-gl`.
- **"Isento, entrada com RG":** uma segunda camada `fill` com `fill-pattern` (listras diagonais brancas semitransparentes sobre o tom do "Isento"), filtrada pelas feições com `padrao = rg`. A imagem é **gerada por código** (matriz de pixels, sem canvas, para ser testável no jsdom) e registrada com `map.addImage`. É preciso confirmar no navegador (Edge sem interface, como na 001) que o padrão aparece no globo. **Plano B se não aparecer:** uma camada `line` tracejada interna, na cor do "Isento" escurecida, só nas feições com RG. Isso é uma tarefa de verificação (spike) antes das demais da P2.
- **Legenda:** `LegendaDeVistos` com o subitem "Isento, entrada com RG" (caixa de marcar com estado misto: `aria-checked="mixed"` e texto "(parcial)", sem depender de cor); filtro puro em `legenda/filtroDeVistos.ts`. A linha "Vistos: Wikipédia (CC BY-SA), fonte não oficial, coletados em DD/MM/AAAA" fica **fora** da parte recolhível de `LegendaRecolhivel`, só no modo Vistos.
- **Painel:** `SecaoVisto` abaixo de `AlertasDoPais`; ausente quando `visto === null` (Brasil).

### D8. Meios restritos ao dono
O padrão da 001 é `python -m farol.worker <comando>`, dentro do contêiner do worker. Para vistos: `coletar --vistos` e o grupo `vistos` com `pendentes`, `confirmar`, `rejeitar` e `ignorar-nome` (`contracts/comandos-do-dono.md`). Nenhuma rota de escrita, nenhuma interface pública. Toda rodada com pendências escreve **uma** linha de aviso no log (JSON, campo `dados`) com as quantidades.

### D9. Testes
Sem rede e sem LLM de verdade: sessão HTTP falsa, tradutor falso, fixture real. Unidade: `tests/unidade/vistos`; integração com PostgreSQL: `tests/integracao/vistos`; um teste de ponta a ponta com a fixture inteira (no estilo do teste do Líbano da 001); contrato: `tests/contrato` apontando para o contrato da 002. As pastas são as mesmas que o CI já roda (`tests/unidade tests/contrato` e `tests/integracao`); não há tarefa nova do poe.

## 3. Levantamento obrigatório (a partir da fixture) — APROVADO em 28/10/2026

As marcas "a confirmar" das versões anteriores deste documento foram resolvidas pelas respostas O1 a O4 (seção 4). Onde a decisão mudou a proposta, a tabela mostra o valor final.

Fixture: `backend/tests/fixtures/wikipedia/visa_requirements_for_brazilian_citizens.html` (revisão 1380975986). Normalização aplicada: remove `<sup>`/marcas `[2]`, troca espaços não separáveis, colapsa espaços, uniformiza a barra (`A/B` → `A / B`) e a diferença entre aspas e apóstrofos. Maiúsculas e minúsculas **não** mudam nenhuma contagem (não há variantes só de caixa).

### 3.1 Rótulos da coluna de situação (23 valores distintos, depois de normalizados)

**Regra geral de categoria (O1, a registrar no `rotulos.yaml`):** a categoria reflete **o que é preciso fazer antes de embarcar**. As palavras "online" e "e-" descrevem só o **canal**, não a categoria. Um **processo de visto completo** é "Visto exigido", mesmo quando feito online; um **pedido online simplificado** (autorização, e-visa de pedido rápido, e-VOA) é "Autorização ou visto eletrônico"; algo obtido **na chegada** é "Visto na chegada". Rótulos novos que não caibam na regra caem em "Outra situação" até o dono decidir.

**Tabela principal (193 linhas, 18 rótulos):**

| # | Rótulo normalizado | Linhas | Exemplos | Categoria proposta | Obs. |
|---|---|---|---|---|---|
| 1 | Visa not required | 97 | Albânia, Andorra, Angola | Isento de visto | |
| 2 | eVisa | 31 | Afeganistão, Benin | Autorização ou visto eletrônico | |
| 3 | Visa required | 18 | Argélia, Brunei | Visto exigido | |
| 4 | eVisa / Visa on arrival | 14 | Bahrein, Camboja, Egito | Autorização ou visto eletrônico | combinado; inclui "eVisa/Visa on arrival" (Egito, sem espaços) |
| 5 | Freedom of Movement | 8 | Argentina, Chile, Uruguai | Isento de visto, **com RG** | ver 3.2 |
| 6 | Visa on arrival | 6 | Comores, Ilhas Marshall | Visto na chegada | |
| 7 | Electronic Travel Authorisation | 3 | Quênia, Saint Kitts e Nevis | Autorização ou visto eletrônico | grafia britânica |
| 8 | Free visa on arrival | 3 | Líbano, Maldivas, Palau | Visto na chegada | "Free" = sem taxa |
| 9 | Electronic Travel Authorization | 2 | Israel, Coreia do Sul | Autorização ou visto eletrônico | grafia americana |
| 10 | Online Visa / Visa on arrival | 2 | Burundi, Nepal | Autorização ou visto eletrônico | combinado |
| 11 | Visa not required / eVisa | 2 | Omã, Tajiquistão | Autorização ou visto eletrônico | combinado: vale o mais exigente (FR-007) |
| 12 | ETA / Visa on arrival | 1 | Sri Lanka | Autorização ou visto eletrônico | combinado |
| 13 | Electronic Travel Authority | 1 | Nova Zelândia | Autorização ou visto eletrônico | grafia australiana |
| 14 | Entry permit on arrival | 1 | Samoa | Visto na chegada | aprovado (O1): obtido na chegada |
| 15 | Free Visitor's permit on arrival | 1 | Ilhas Salomão | Visto na chegada | aprovado (O1): obtido na chegada |
| 16 | Online visa required | 1 | Austrália | **Visto exigido** | aprovado (O1): é um visto completo, só pedido online |
| 17 | Visa not required / e-VOA | 1 | Indonésia | Autorização ou visto eletrônico | aprovado (O1); combinado: vale o mais exigente das partes |
| 18 | e-VOA | 1 | Libéria | Autorização ou visto eletrônico | aprovado (O1): pedido online simplificado |

**Atômicos do dicionário afetados pela regra geral:** `online visa required` → `visto_exigido`; `e-voa` → `autorizacao_eletronica`; `entry permit on arrival` e `free visitor's permit on arrival` → `visto_na_chegada`. **Ponto que eu interpretei (confira):** a parte `online visa` (sem "required"), que só aparece no combinado `Online Visa / Visa on arrival` (Burundi, Nepal), fica em `autorizacao_eletronica`: sem "required", e como alternativa ao visto na chegada, é o pedido online simplificado, e o combinado vale o mais exigente das partes (autorização eletrônica). Se você a quiser como visto completo, o combinado dos dois países sobe para "Visto exigido".

**Tabelas de territórios (56 linhas, 9 rótulos; 4 já aparecem acima):**

| Rótulo normalizado | Linhas | Exemplos | Categoria proposta |
|---|---|---|---|
| Visa not required | 39 | Hong Kong, Macau, Groenlândia, Palestina | Isento de visto |
| Visa required | 7 | Taiwan, Porto Rico, Guam | Visto exigido |
| Permit required | 3 | Tokelau, Jan Mayen, Geórgia do Sul | **Outra situação** (rótulo conhecido) |
| Special permit required | 2 | Clipperton, Território Britânico do Oceano Índico | **Outra situação** (rótulo conhecido) |
| Entry permit required | 1 | Samoa Americana | **Outra situação** (rótulo conhecido) |
| Permission required | 1 | Tristão da Cunha | **Outra situação** (rótulo conhecido) |
| Visa on arrival | 1 | Somalilândia | Visto na chegada |
| Visa regime undefined | 1 | República Árabe Saaraui Democrática | **Outra situação** (rótulo conhecido); o nome é ignorado (área neutra) |
| eVisa | 1 | Ilha de Ascensão | Autorização ou visto eletrônico |

**Como os combinados são lidos.** Cada rótulo é separado na barra " / " (o separador que a própria fonte usa para alternativas) e cada parte precisa existir no dicionário; vale a categoria **mais exigente** das partes (isento < visto na chegada < autorização ou visto eletrônico < visto exigido), e **qualquer parte** em "Outra situação" ou desconhecida leva o país inteiro a "Outra situação" (FR-007). Partes que a fonte usa em combinados: `visa not required`, `visa on arrival`, `evisa`, `online visa`, `eta`, `e-voa`. Os 5 combinados da fixture ficam cobertos por testes de ponta a ponta, e o dicionário tem **20 entradas atômicas** (uma por rótulo isolado ou parte), cada uma com seu teste.

### 3.2 Como aparece o caso "basta o RG"

- **Aparece no rótulo, e as notas confirmam.** Os 8 países com o rótulo `Freedom of Movement` (Argentina, Bolívia, Chile, Colômbia, Equador, Paraguai, Peru, Uruguai) trazem nas notas a frase "Entry is allowed with a valid ID card that is less than 10 years old". Nenhum outro rótulo carrega essa informação.
- **Falso positivo a evitar:** Guiana (`Visa not required`) tem na nota "Brief visits just to the border town of Lethem are possible with a valid Brazilian ID card": o RG vale só para uma visita curta na fronteira. **Não** conta como "basta o RG".
- **Conferência pedida na aprovação (O2).** Os 8 países que entram: **Argentina, Bolívia, Chile, Colômbia, Equador, Paraguai, Peru e Uruguai**. Dos 9 do Mercosul e associados, fica de fora a **Venezuela**: a fonte a lista como `Visa not required`, 90 dias, **sem nenhuma nota** (nem "Freedom of Movement", nem "ID card"). Ela é "Isento de visto" **sem** RG, porque a fonte não afirma o RG (princípio V). Busca por menção a documento de identidade (`ID`, `ID card`, `identity`, `identification`, `RG`, `DNI`, `cédula`) em **todas** as notas das três tabelas: além dos 8 acima, só a **Guiana** aparece (visita à fronteira, descartada). Nenhum outro país nem território menciona documento de identidade. Suriname, México e os demais vizinhos não têm menção. Se um dia a Venezuela ou outro país passar a ter o rótulo `Freedom of Movement` com a frase, a regra o inclui sozinha, e como "passar a aceitar o RG" é mudança retida (FR-010a), o dono confirma antes de valer.
- **Regra aprovada (sem heurística geral):** `aceita_rg` é verdadeiro **se e somente se** o rótulo normalizado é `Freedom of Movement` **e** a nota contém "ID card". Se o rótulo vier sem a frase, a categoria continua "Isento" e o RG **não** é afirmado (princípio V); um aviso vai para o log. Teste: 8 de 8 na fixture, Guiana de fora. A "validade menor que 10 anos" fica nas observações (traduzidas); o RG em si é só o indicador.

### 3.3 Formatos de permanência

Coluna "Allowed stay" da tabela principal (153 linhas com valor, 40 em branco):

| Formato | Linhas | Cai nos formatos do FR-004a? |
|---|---|---|
| `N days` (90, 30, 15, 180, 120, 14, 28, 31, 45, 59, 60, 7) | 120 | Sim → "N dias" |
| `N months` (3, 6, 4) e `1 month` | 28 | Sim → "N meses", "1 mês" |
| `6 weeks` | 1 | Sim → "6 semanas" |
| `1 year` | 1 | Sim → "1 ano" |
| `up to 90 days` (Etiópia) | 1 | **Não** → aparece em inglês, como na fonte |
| `14 days / 30 days` (Omã), `30 days / 60 days` (Tajiquistão) | 2 | **Não** → aparece em inglês, como na fonte |
| em branco | 40 | sem campo de permanência |
| **`N days in any M-day period`** | **0** | **Não ocorre nesta coluna** |

Nas tabelas de territórios **não há coluna de permanência**: o prazo vem dentro da coluna "Notes". Das 56 notas, 13 são só um prazo simples (ex.: "90 days", "3 months"), **10 são "N days|months within any M-day|month period"** (note: a fonte escreve **"within any"**, e não "in any"; e há "3 months within any 6-month period"), 16 estão em branco e 17 são outros textos. Decisão O3 (**aprovada**): **não** ler prazo das notas dos territórios; o campo de permanência fica omitido e o texto da nota vai para as observações. Só se estende o FR-004a com "within any" se um dia isso mudar.

### 3.4 Tabelas, seções e duplicatas

| Parte da página | Estrutura | Linhas | Uso |
|---|---|---|---|
| Visa requirements | tabela principal (`Country`, `Visa requirement`, `Allowed stay`, `Notes (excluding departure fees)`, `Reciprocity`) | 193 | países |
| Unrecognized or partially recognized countries | tabela (`Territory`, `Conditions of access`, `Notes`) | 9 | Taiwan, Palestina; os outros são ignorados |
| Dependent and autonomous territories | tabela agrupada por soberano (linha de grupo com 1 célula) | 47 | dependências |
| Other territories | **lista de texto** (`<ul>`), não tabela (ex.: "Crimea. Visa not required…") | — | **não lida** nesta feature |
| Non-visa restrictions | texto | — | fora do escopo |

**Sem duplicatas de nome** na tabela principal (193 nomes distintos) nem entre tabelas. **Vários nomes para o mesmo código do mapa:** Ilha de Santa Helena, Ilha de Ascensão e Tristão da Cunha → `SH` (rótulos `Visa not required`, `eVisa`, `Permission required`: vale "Outra situação", pela regra dos combinados). E uma linha para vários códigos: "United Kingdom and Crown dependencies" → `GB`; Guernsey, Jersey e Ilha de Man (sem linha própria) caem no soberano, que é a mesma linha.

**Nomes que o pycountry não liga sozinho (18 aliases à mão):** Brunei → BN, Cape Verde → CV, Democratic Republic of the Congo → CD, Micronesia → FM, Russia → RU, Turkey → TR, Vatican City → VA, United Kingdom and Crown dependencies → GB, Palestine → PS, Macau → MO, Saint Martin → MF, Sint Maarten → SX, Pitcairn Islands → PN, Saint Helena / Ascension Island / Tristan da Cunha → SH, Clipperton Island → CLP, U.S. Virgin Islands → VI.

**Ignorados de propósito (21 nomes), cada um com motivo, no arquivo `nomes.yaml`:**
- por convenção da 001: Kosovo (usa a identidade da Sérvia), Falkland Islands (usa a da Argentina);
- território não reconhecido sem desenho no mapa: Abkhazia, South Ossetia, Northern Cyprus, Somaliland, Transnistria;
- área neutra: Sahrawi Arab Democratic Republic (Saara Ocidental);
- parte de outro país no mapa: Guadeloupe, Martinique, Mayotte, Réunion (França), Bonaire, Sint Eustatius, Saba (Países Baixos);
- sem desenho próprio: Tokelau, Jan Mayen, Svalbard, Akrotiri and Dhekelia, British Indian Ocean Territory, South Georgia and the South Sandwich Islands.

**Cobertura projetada (SC-001), só pela ligação de nomes:** os 194 países e as 43 dependências do mapa (sem o Brasil) têm linha própria ou do soberano: **237 de 237**. A conta definitiva depende dos rótulos ficarem fora de "Outra situação por rótulo desconhecido": com o dicionário proposto, **nenhum** rótulo da fixture é desconhecido. **Códigos reconhecidos** (base do FR-010): 226 (193 da tabela principal e 33 dos territórios, sem Kosovo e Malvinas); 90% de 226 é 204, bem acima do piso de 150 da primeira coleta.

### 3.5 "Varia conforme o motivo" (O4, aprovado com acréscimo)

**"Varia conforme o motivo da viagem" (FR-007a).** A fonte **não tem marca estruturada** para isso: está em texto livre. Das 193 notas, 22 casam com palavras de motivo (business, tourism, work, study...), mas várias são ruído (os 8 países do Mercosul dizem "live and work legally") e só poucas dizem que a regra ou o prazo **diferem** por motivo: Jamaica ("90 days (business), 6 months (tourist)") e Zâmbia ("business … 30 days in any 1-year period. Tourists … 90 days"). Angola e Líbano só limitam o turismo. Detectar isso por palavras-chave seria heurística geral (e erraria), então proponho uma **lista curada por código** em `regras_por_pais.yaml` (hoje: `JM` e `ZM`, com `prazos_diferem_por_motivo`), que você pode ampliar. Um teste confere que a nota da fixture desses países cita os dois motivos. Quando a nota mudar, a lista pode ficar defasada; o dano é só uma nota informativa a mais ou a menos, nunca uma categoria errada (O4).

**Acréscimo aprovado: a regra guarda a observação em que se baseou.** Cada entrada de `regras_por_pais.yaml` tem `hash_observacao`: SHA-256 (UTF-8) das **notas normalizadas** das linhas da fonte daquele código, na ordem da fonte, unidas por quebra de linha. A cada coleta válida, se o hash calculado de um país da lista for diferente do guardado, o país entra na **lista de revisão** (`item_para_revisao`, tipo `regra`; `vistos pendentes` mostra o texto novo e o hash novo; um aviso no log, como nas outras pendências). A regra segue valendo enquanto o dono não reconfirmar (dano só informativo, como acima). O dono **reconfirma** colando o hash novo no arquivo (ou tira o país da lista); a coleta seguinte vê o hash igual e fecha o item sozinha (`resolvido`). Testes: o hash da fixture bate com o das duas entradas; uma nota alterada abre o item; o hash igual o fecha.

**México (pergunta da aprovação).** Não achei o México na spec nem nos artefatos do clarify (busca textual nos arquivos da feature: nenhuma ocorrência), então não foi uma exclusão registrada; se foi um exemplo seu em outra conversa, me diga qual era a ideia. Na fonte, o México é `eVisa`, 180 dias, e a nota diz que o documento "vale para turismo, viagens de negócios e trânsito, sem autorização para atividades remuneradas": o **mesmo** eVisa e o **mesmo** prazo para todos os motivos. Fica **fora de propósito**, porque a nota lista os motivos mas não diz que a regra ou o prazo diferem entre eles. É o mesmo critério que deixa Angola e Líbano de fora (só limitam o turismo). Só `JM` e `ZM` entram, e o dono amplia a lista pelo arquivo, com o hash.

## 4. Decisões (todas aprovadas em 28/10/2026)

Numeração: a resposta do usuário chamou de "O8" a condição sobre o contrato; no texto abaixo ela está em **O9**, onde o contrato é tratado. O8 (arquivo `nomes.yaml`) foi aprovado junto dos desvios.

| # | Decisão | Decisão final |
|---|---|---|
| O1 | Categoria dos rótulos 14 a 18 | Samoa e Ilhas Salomão → Visto na chegada; Indonésia e Libéria → Autorização ou visto eletrônico; **Austrália ("Online visa required") → Visto exigido**. Regra geral registrada em 3.1 e no dicionário: a categoria reflete o que é preciso fazer antes de embarcar; "online" e "e-" descrevem o canal |
| O2 | Regra do RG | Rótulo `Freedom of Movement` **e** "ID card" na nota; Guiana de fora. Os 8 países e a conferência dos demais estão em 3.2 |
| O3 | Permanência dos territórios | Não ler prazo das notas; campo omitido, texto nas observações |
| O4 | "Varia conforme o motivo" | Lista curada por código (`JM`, `ZM`), **com `hash_observacao` por entrada**; observação alterada ⇒ país entra na lista de revisão. México fora de propósito (3.5) |
| O5 | Horário do job | Segunda-feira **05:13** (e não 05:43) |
| O6 | Falhas técnicas seguidas | Até 3 tentativas diárias, depois só na próxima segunda |
| O7 | Estado `superada` | Aprovado |
| O8 | Nomes ignorados por convenção ou sem desenho | Em `nomes.yaml` (versionado); `ignorar-nome` continua para casos novos |
| O9 | Contrato | `contracts/openapi.yaml` da 002 é o contrato completo e os testes apontam para ele, **com a parte da 001 intacta**, travada por teste que falha em qualquer rota ou campo da 001 alterado ou removido (seção 1) |
| O10 | `/vistos` sob demanda | Aprovado. Falha na busca: erro na legenda com "Tentar de novo"; os países **não** são pintados de cinza (cinza = "sem informação de visto") |
| O11 | Cliente HTTP na `infra`, "captcha", User-Agent | Aprovado. A correção do "captcha" não pode enfraquecer a detecção da 001 (seção 1); os testes da 001 do cliente passam mudando só os imports |
| O12 | Paleta (inclui o "Sem informação" mais escuro que o dos alertas) | Aprovada |

## 5. Riscos que o plano aceita

- **O artigo muda de forma** (cabeçalhos, tabelas, ordem das seções): a coleta é rejeitada como "formato inesperado" e o site segue com a última coleta válida. A fixture detecta quebras só na hora de atualizá-la; a coleta real detecta na semana seguinte.
- **Vandalismo ou erro de edição:** coberto pela retenção por país (FR-010a). Não cobre uma edição maldosa que **torne um país mais exigente**: ela é aplicada (decisão do usuário: o erro grave é o oposto) e some quando a fonte for corrigida.
- **Tradução automática errada:** sempre marcada como automática, com o original à mão. Não afeta categoria nem prazo (esses não passam pelo modelo).
- **Cota do LLM:** uma chamada por lote e só para observações novas; na primeira coleta são cerca de 150 observações em ~8 lotes. Falha de cota deixa o original em inglês até a próxima coleta.
- **Padrão no globo:** `fill-pattern` no MapLibre 6 com projeção de globo não foi testado ainda. Há plano B (`research.md`, D7) e uma tarefa de verificação antes do resto da P2.
- **SC-008 (7 dias):** adiamentos e falhas técnicas somam até 3 dias, então o atraso pode passar de 7 dias em semanas ruins; o critério já vale só "quando a coleta funciona".
