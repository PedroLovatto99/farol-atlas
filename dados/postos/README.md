# Postos diplomáticos e consulares do Brasil

Dados para o seed do projeto. Montados em 21/10/2026.

## Arquivos

### `postos_brasileiros.csv`

Um posto por linha: 209 postos em 137 países ou territórios.

| Coluna | O que é |
|---|---|
| `id` | Número sequencial |
| `pais_iso` | Código ISO de 2 letras (use para cruzar com o GeoJSON do mapa e com os alertas) |
| `pais` | Nome do país em português, como na lista do Itamaraty |
| `cidade` | Cidade do posto, em português |
| `tipo` | Embaixada, Consulado-Geral, Consulado, Vice-Consulado, Escritório de Representação ou Escritório Comercial |
| `latitude`, `longitude` | Coordenadas do centro da cidade (não do endereço exato do posto) |
| `regiao` | África, Américas, Ásia, Europa ou Oceania |
| `na_lista_oficial` | `sim` se a cidade aparece na lista de atendimento consular do Itamaraty |
| `observacao` | Preenchida só quando `na_lista_oficial` é `nao` |

Quando a mesma cidade tem embaixada e consulado (Lisboa, Tóquio, Buenos Aires...), aparecem duas linhas com as mesmas coordenadas.

### `jurisdicao_cumulativa.csv`

Os 60 países onde o Brasil não tem posto próprio e qual posto atende cada um (por exemplo, Iêmen → Riade). A Líbia aparece sem posto indicado, como na lista oficial.

## Fontes

- **Postos, tipos e cidades:** [List of diplomatic missions of Brazil](https://en.wikipedia.org/wiki/List_of_diplomatic_missions_of_Brazil), Wikipédia em inglês. Última edição em 03/10/2026, com revisão das referências país a país no fim de agosto de 2026. Não inclui consulados honorários.
- **Coordenadas:** coordenadas principais do artigo de cada cidade na Wikipédia. Ramallah veio do Wikidata.
- **Conferência e nomes em português:** [Repartições Consulares do Brasil](https://www.gov.br/mre/pt-br/assuntos/portal-consular/reparticoes-consulares-do-brasil), Itamaraty, atualizada em 10/07/2026.

Conteúdo derivado da Wikipédia está sob licença CC BY-SA. Cite a fonte na página "Sobre" do projeto.

## Divergências entre as fontes

Seis postos da Wikipédia não aparecem na lista oficial de atendimento consular:

- **Haia, Berna e Abuja:** embaixadas em países onde o atendimento consular fica em outra cidade (Amsterdã, Genebra/Zurique e Lagos). Provavelmente normal.
- **Cartum (Sudão):** o Sudão não aparece na lista oficial. Confirmar se o posto está funcionando.
- **Santa Elena de Uairén (Venezuela) e Saint-Georges de l'Oyapock (Guiana Francesa):** não aparecem na lista oficial. Confirmar.

## Como atualizar

Postos mudam pouco. Uma conferência por ano contra a lista oficial do Itamaraty costuma bastar.
