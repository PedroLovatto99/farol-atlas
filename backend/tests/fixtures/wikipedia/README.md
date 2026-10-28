# Fixture da Wikipédia: vistos para brasileiros

Cópia, sem nenhuma alteração, da página do artigo usada pela coleta de vistos (feature 002). Com ela, os
testes rodam sem internet e sempre dão o mesmo resultado.

| Item | Valor |
|---|---|
| Arquivo | `visa_requirements_for_brazilian_citizens.html` (1.578.966 bytes) |
| SHA-256 | `5c8366d3ef57b59cbbf0409ef341bd9fe987b15251390da23a3ef8b2dcc25040` |
| Origem | https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens |
| Baixada em | 27/10/2026, 23:45 em Brasília (28/10/2026, 02:45 UTC). O cabeçalho `Date` da resposta, 21:30 UTC, é de quando o cache da Wikipédia gerou a página (`Age` de 5 h). |
| Revisão do artigo | 1380975986 (`wgRevisionId`) |
| Última edição (JSON-LD `dateModified`) | 2026-10-19T05:08:59Z |
| Licença | Texto da Wikipédia em inglês: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Atribuição: autores do artigo, conforme o histórico de edições da página. Não é fonte oficial. |

## Como foi baixada

Uma requisição à página do artigo (e uma ao `robots.txt`), com `curl` e este User-Agent:

```text
FarolAtlas/0.1 (https://github.com/PedroLovatto99/farol-atlas; projeto pessoal) curl
```

Não use a API da Wikipédia (`/w/api.php`) nem a API REST (`/api/`): o `robots.txt` da Wikipédia as proíbe para
robôs genéricos. As páginas de artigo (`/wiki/…`) são permitidas.

Para atualizar a cópia (só quando o formato do artigo mudar e um teste precisar), repita a requisição e atualize
esta tabela (data, revisão, `dateModified` e SHA-256):

```powershell
curl -sS -A "FarolAtlas/0.1 (https://github.com/PedroLovatto99/farol-atlas; projeto pessoal) curl" --compressed `
  https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens `
  -o backend/tests/fixtures/wikipedia/visa_requirements_for_brazilian_citizens.html
```

## O que há de relevante na página

- A data da última edição está em três lugares: o JSON-LD (`dateModified`, legível por máquina), o rodapé
  ("This page was last edited on 19 October 2026, at 05:08 (UTC)") e `wgRevisionId`. O cabeçalho HTTP
  `Last-Modified` desta resposta dizia 26/10/2026 19:44 GMT, uma semana depois da edição: reflete o cache da
  Wikipédia, **não** a última edição, e não deve ser usado.
- A palavra "captcha" aparece 4 vezes, mas só dentro de um `<script>` de configuração
  (`wgConfirmEditCaptchaNeededForGenericEdit`). Não é página de verificação humana. Um teste usa esta fixture
  para garantir que o cliente HTTP não a confunda com uma.
- Tabelas (`table.wikitable`): a principal (193 linhas de países), "Unrecognized or partially recognized
  countries" (9 linhas) e "Dependent and autonomous territories" (47 linhas de território, em grupos por
  soberano). A seção "Other territories" é uma lista de texto, não uma tabela.
