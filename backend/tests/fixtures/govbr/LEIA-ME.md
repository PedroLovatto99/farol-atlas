# Páginas do gov.br para os testes

Cópias de páginas reais do Portal Consular, usadas pelos testes da coleta.
Com elas, os testes rodam sem internet e sempre dão o mesmo resultado.

## Como preencher

1. Rode `ferramentas/testar_coleta.py` (troque o `CONTATO` no topo antes).
2. Copie para esta pasta os arquivos que ele cria em `amostras_coleta/`:
   `lista_alertas.html`, `alerta_1.html`, `alerta_2.html`, `alerta_3.html`,
   `reparticoes.html`, `posto_1.html` e `posto_2.html`.

## Subpáginas de postos (coleta de endereço e telefone)

Salvas em 24/10/2026 com `ferramentas/testar_coleta.py --somente-urls --urls ...`
(pausa de 2 s entre pedidos, `robots.txt` consultado, User-Agent com contato). O script
dá a cada arquivo o nome `extra_<host>-<caminho>.html`; aqui eles foram renomeados.

| Arquivo | URL de origem |
|---|---|
| `milao_emergencias.html` | `https://www.gov.br/mre/pt-br/consulado-milao/emergencias` |
| `milao_fale_conosco.html` | `https://www.gov.br/mre/pt-br/consulado-milao/fale-conosco-1` |
| `milao_horarios_como_chegar.html` | `https://www.gov.br/mre/pt-br/consulado-milao/horarios-e-como-chegar` |
| `pretoria_inicio.html` | `http://pretoria.itamaraty.gov.br/pt-br/` (o link da tabela de repartições; redireciona para `https://www.gov.br/mre/pt-br/embaixada-pretoria`) |
| `pretoria_fale_conosco.html` | `https://www.gov.br/mre/pt-br/embaixada-pretoria/fale-conosco-1` |

O que cada uma tem (a coleta de postos é melhor esforço, então os testes cobrem os dois lados):

- **Milão**: o telefone do plantão está em `emergencias` ("Plantão Consular do Consulado-Geral
  do Brasil em Milão: +39 335 727 8117"), junto de outro número, o do plantão do Ministério em
  Brasília, que **não** é o do posto. Nenhuma das três páginas traz endereço de rua.
- **Pretória**: o endereço está em `fale-conosco-1` ("Endereço 152 Dallas Avenue ..."); a página
  não traz telefone de plantão (só a linha geral da embaixada).
- `posto_1.html` (Amã) não tem menu de abas no HTML estático: serve de caso "sem nada".

## Quando atualizar

Se o gov.br mudar o layout, rode o script de novo e substitua os arquivos.
Os testes que quebrarem mostram o que precisa mudar na coleta.
