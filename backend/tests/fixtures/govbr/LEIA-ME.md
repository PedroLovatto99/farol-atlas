# Páginas do gov.br para os testes

Cópias de páginas reais do Portal Consular, usadas pelos testes da coleta.
Com elas, os testes rodam sem internet e sempre dão o mesmo resultado.

## Como preencher

1. Rode `ferramentas/testar_coleta.py` (troque o `CONTATO` no topo antes).
2. Copie para esta pasta os arquivos que ele cria em `amostras_coleta/`:
   `lista_alertas.html`, `alerta_1.html`, `alerta_2.html`, `alerta_3.html`,
   `reparticoes.html`, `posto_1.html` e `posto_2.html`.

## Quando atualizar

Se o gov.br mudar o layout, rode o script de novo e substitua os arquivos.
Os testes que quebrarem mostram o que precisa mudar na coleta.
