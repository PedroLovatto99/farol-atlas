# Contrato: textos fixos do chat

Texto final das respostas (a spec deixa o fechamento para o planejamento). Ficam em
`backend/src/farol/chat/textos.py`; cada linha desta página tem um teste. `{país}` é o nome que o
painel mostra (no visto de Kosovo e Malvinas, `territorio_nome`). Datas em `dd/mm/aaaa`, fuso
`America/Sao_Paulo`, como `formatarData` do frontend. Nas mensagens fixas, Kosovo e Malvinas
aparecem como "Kosovo (Sérvia)" e "Malvinas (Argentina)" (`rotulo_busca`). Os rótulos entre aspas são **os mesmos** do
painel (`compartilhado/niveis.ts` e `compartilhado/vistos.ts`); um teste fixa cada um.

Nas frases, `{país}` entra com o artigo de `chat/artigos.yaml`: "para a França", "para o Afeganistão",
"para os Estados Unidos", "para Portugal"; "de {país}" vira "da", "do", "dos" ou "das" quando há artigo.
Em `um_pais_por_vez`, "sobre a França e a Itália". Em `qual_dos_paises`, as opções ficam sem artigo.

Toda resposta é uma lista de parágrafos; cada parágrafo, uma lista de trechos `{texto, url}`
([openapi.yaml](openapi.yaml), `RespostaDoChat`). Ordem (FR-003): frase direta → dados → observação
da fonte → fonte e data → avisos. Em `alerta_e_visto`, o bloco do alerta vem antes do do visto.

Palavras proibidas nos textos fixos (SC-005; o teste confere todas as saídas com dados de exemplo
que não as contêm, já que um título de alerta real pode citar "seguro-viagem"): "seguro", "segura",
"tranquilo", "tranquila", "sem perigo", "pode ir".

## Alerta

| Situação (da `VisaoDoPainel` e da `VisaoDoMapa`) | Frase direta |
|---|---|
| `nao_viajar` | Para {país}, o Itamaraty recomenda não viajar (nível "Não viaje"). |
| `evitar` | Para {país}, o Itamaraty recomenda evitar viagens não essenciais (nível "Evite viagens não essenciais"). |
| `sem_alerta`, sem regiões | Não há alerta de viagem do Itamaraty para {país}. Isso não significa que o governo recomenda a viagem. |
| `sem_alerta` com `regiao_unica_do_alerta` | Para {país}, há "Alerta só para parte do país": ele vale só para a região indicada, não para o país inteiro. Para o restante do país, a ausência de alerta não significa que o governo recomenda a viagem. |
| `nao_verificado`, com coleta | O nível de alerta de {país} não foi verificado: ainda não temos informação confirmada do Itamaraty. |
| `nao_verificado`, sem nenhuma coleta (`dados_obtidos` falso) | Ainda não obtivemos os dados do Itamaraty, então o nível de alerta de {país} não foi verificado. |

Dados, nesta ordem, cada um só quando o painel o tem:

- Regiões (`regioes`): "Regiões com nível próprio: {região} ("{rótulo do nível}"); …".
- Alerta que define o nível (`define_nivel`): "Alerta que define o nível: " + trecho
  `{título}` com `url` do gov.br + " (publicado em {data}; modificado em {data})".
- Não verificado com alerta `pendente`: "Confira o alerta original: " + trecho `{título}` com `url`.
- Observação do território (`observacao`, ex.: dependências): "Observação: {observacao}". Em Kosovo e
  Malvinas (`observacao_no_topo`), a nota vem antes da frase direta, sem o "Observação:", como no painel.

Fonte: "Fonte: " + trecho "Portal Consular do Itamaraty" (url do Portal Consular) + ", atualizado em
{atualizado_em}." Sem coleta, sem a data. Desatualizado (`VisaoDoMapa.desatualizado`): "Dados
desatualizados: a última atualização completa tem mais de 3 dias."

## Visto

| `situacao` | Frase direta |
|---|---|
| `isento` | Não, brasileiros não precisam de visto para {país}. |
| `isento` + `aceita_rg` | Não, brasileiros não precisam de visto para {país}, e a entrada pode ser feita com o RG. |
| `visto_na_chegada` | Brasileiros precisam de visto para {país}, mas ele é obtido na chegada. |
| `autorizacao_eletronica` | Brasileiros precisam de uma autorização ou visto eletrônico para {país}, obtido antes da viagem. |
| `visto_exigido` | Sim, brasileiros precisam de visto para {país}. |
| `outra_situacao` | A situação de visto de {país} não se encaixa nas categorias do site. |
| `sem_informacao` | Sem informação de visto para {país}. Isso não significa que a entrada seja livre. |

Dados (mesmos campos e rótulos da `SecaoVisto`): "Categoria: "{rótulo}"" · "Na fonte: {rotulo_original}"
· "Varia conforme o motivo da viagem" · "Permanência: {texto}" (`padronizada`/`original` pelo texto;
`prazos_divergentes` e `varia_conforme_motivo` pelos rótulos do painel) · origem `soberano`: "Sem
entrada própria na fonte para este território. Vale a entrada do soberano: {soberano_nome}."

Observação da fonte: "Observação da fonte (tradução automática): {traducao}" ou, sem tradução,
"Observação da fonte (não traduzido): {texto_original}".

Fonte: "Fonte: " + trecho "{fonte.nome}" (url da Wikipédia) + " ({licenca}, não oficial), dado de
{dado_de}." e "Informação não oficial. Confirme com o consulado ou embaixada do país antes da
viagem." Desatualizado: "Estes dados podem estar desatualizados: foram lidos da fonte há mais de 14 dias."

## Mensagens fixas

| `tipo` | Texto |
|---|---|
| `qual_dos_paises` | Qual deles você quer saber: {A} ou {B}? Pergunte de novo com o nome do país. (3+ opções: "{A}, {B} ou {C}"; na Geórgia, "Geórgia (país)" e "Geórgia (estado americano)") |
| `pedir_pais` | De qual país você quer saber? Pergunte citando o nome, por exemplo: "Preciso de visto para o Japão?" |
| `um_pais_por_vez` | Entendi que você perguntou sobre {A} e {B}. Pergunte sobre um país de cada vez, por favor. |
| `brasil` | Eu respondo sobre viagens de brasileiros ao exterior. Para qual país você vai? |
| `fora_do_assunto` | Eu informo o nível de alerta do Itamaraty e a situação de visto para brasileiros em cada país, por exemplo: "Como está o alerta para o Peru?". Para o resto, como postos e o conteúdo dos alertas, abra o painel do país no mapa. |
| `reformular` | Não consegui entender de qual país você fala. Pode reformular citando o nome do país? |
| 429 (`detalhe`) | Você chegou ao limite de {n} perguntas por hora. Tente de novo em {m} min. |

## Interface (frontend)

- Aviso fixo da caixa: "As respostas são montadas automaticamente a partir dos dados do site e
  devem ser conferidas no Portal Consular" + link `URL_DO_PORTAL_CONSULAR`.
- Botão flutuante: rótulo acessível "Abrir chat" / "Fechar chat". Campo: rótulo "Sua pergunta",
  `maxLength=300`, contador "{n}/300". Enquanto espera: "Respondendo…".
- Os parágrafos mantêm as quebras de linha do texto (`white-space: pre-line`), como a `SecaoVisto`.
- Falha de rede ou 5xx: "Não foi possível responder agora. Tente de novo em instantes."
