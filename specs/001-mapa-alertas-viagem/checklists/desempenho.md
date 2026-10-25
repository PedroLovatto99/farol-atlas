# Medição de desempenho (T132)

**Critério**: SC-001, descobrir o nível de qualquer país em até 10 s, pelo toque ou pela busca, e o tempo de carga do `/mapa`.
**Data**: 25/10/2026 · **Ambiente**: `docker compose` local (Windows), banco de desenvolvimento com 18 alertas classificados de verdade.

## Como foi medido

- **No navegador**: Microsoft Edge sem janela, comandado por script, com viewport de 360 × 740 (toque, `isMobile`) e de 1280 × 800. O WebGL do Edge sem janela é por software (SwiftShader), mais lento do que uma GPU de verdade, então o desenho do globo aqui é um limite superior.
- **Na API**: 20 chamadas ao `/mapa` e uma chamada a cada um dos 238 territórios em `/paises/{codigo}`.
- O site rodou no servidor de desenvolvimento do Vite (sem pacote de produção, sem compressão de arquivos estáticos).

## Resultado

| O que | Medida | Limite |
|---|---|---|
| Site aberto até o mapa pronto (celular, 360 px) | 1,2 s | 10 s |
| Site aberto até o mapa pronto (computador) | 1,0 s | |
| **Busca**: do primeiro caractere ao nível do país no painel | 0,18 s | 10 s |
| **Toque** no mapa até o nível do país no painel | 0,23 s | 10 s |
| `/mapa` (20 chamadas) | mediana 52 ms, p95 106 ms, pior 702 ms (a primeira, a frio) | |
| `/paises/{codigo}` (238 territórios) | mediana 35 ms, p95 57 ms, pior 75 ms | |
| Tamanho do `/mapa` | 90 KB; **12 KB com gzip** | |
| `territorios.geojson` | 2,1 MB sem compressão; 704 KB com gzip (era 607 KB e 206 KB, antes de simplificar menos para os postos caírem dentro do país) | |
| Rolagem horizontal em 360 px | nenhuma | |
| Erros no console do navegador | nenhum | |

Os tempos de busca e toque medem só a máquina. O resto do SC-001 (a pessoa achar o campo, digitar, tocar) depende de quem usa, e a tela não pede mais de dois gestos para isso.

## Ajuste feito

O `/mapa` saía sem compressão (90 KB). Em rede de celular lenta isso é o que mais pesa na primeira tela, então a API passou a comprimir respostas acima de 1 KB com gzip (`GZipMiddleware`, antes do CORS): o `/mapa` caiu para 12 KB. Testes em `test_app.py`.

## Sem ajuste

- O `territorios.geojson` (2,1 MB) é o maior arquivo da primeira carga. Em hospedagem estática como a Vercel ele sai comprimido (704 KB, 33% do tamanho); o servidor de desenvolvimento não comprime. Depois de passar de 5% para 20% dos vértices (25/10/2026), a carga até o mapa pronto foi de 1,1 s no celular de 360 px e 0,6 s no computador, no mesmo ambiente das medidas acima (antes: 1,2 s e 1,0 s): o tamanho local não pesou, mas a rede móvel lenta vai sentir os 704 KB.
- O pior caso do `/mapa` (702 ms) foi a primeira chamada, com o banco e a conexão frios.

## O que ficou sem medir

Aparelho real e rede móvel real (3G e 4G). O desenho do globo numa GPU de celular costuma ser mais rápido que o software usado aqui, mas a rede pode ser bem mais lenta que a local. Vale repetir pelo emulador do navegador com "Slow 4G" quando o site estiver publicado.
