# Quickstart: validar o modo daltonismo

Pré-requisitos: os mesmos da 003 (Docker e Node). Cores: [contracts/paletas-e-padroes.md](contracts/paletas-e-padroes.md);
interface: [contracts/interface-do-modo.md](contracts/interface-do-modo.md).

## 1. Verificação automática

```powershell
cd frontend; npm run verificar
```

Esperado: tudo verde. Os testes cobrem:

- os 70 pares de cores do contrato, a pelo menos 12 nas quatro visões, e os contrastes mínimos;
- `contornoDosPaises`: escuro em "Alertas" com o modo ligado e branco com ele desligado, com pelo
  menos 3:1 contra as quatro cores e o oceano;
- hex de `cor.ts` igual aos tokens `--color-daltonismo-*` de `tema.css`;
- paleta padrão idêntica às constantes atuais, sem padrão novo e sem `borda_tracejada` (FR-015);
- preferência: valor válido, valor inválido e `localStorage` que lança erro;
- botão: nome fixo, `aria-pressed`, Enter e Espaço;
- `Tela`: alternar mantém seleção, filtros, painel e câmera, sem novo pedido à API.

`git diff` não deve mostrar nada em `backend/` nem em `esquema.d.ts`.

## 2. Rodar local

```powershell
docker compose up -d
cd frontend; npm run dev
```

## 3. Comportamento

| Passo | Esperado |
|---|---|
| Primeira visita (limpe o `localStorage`) | Modo desligado; aparência atual |
| Selecione um país, desmarque um nível e mova o globo; acione o botão | Cores mudam em menos de 1 s; seleção, filtro, painel e câmera ficam; aba Network sem pedidos novos |
| Troque entre "Alertas" e "Vistos" | O modo continua ligado |
| Em "Alertas", olhe um país "sem alerta" na costa | Contorno escuro; o país não se confunde com o oceano |
| Em "Alertas", olhe um país "não viaje" e um "evite" | Hachura e pontos, iguais às amostras da legenda |
| Olhe um país com alerta regional e a amostra da borda | "Não viaje" contínua e "evite" tracejada, nos dois lugares; texto da legenda igual |
| Em "Vistos", olhe um "Isento" com RG | Listras em `#0E2A20`, iguais à amostra |
| Desmarque "não viaje" na legenda | País e padrão esmaecem juntos, como os demais |
| Recarregue com o modo ligado (CPU em 6x no DevTools) | Nenhum quadro com as cores padrão |
| Desligue e recarregue | Aparência atual, sem padrões, borda de "evite" contínua, contorno branco |
| Bloqueie os dados do site e acione o botão | Funciona na visita; nada no console |
| Vá ao botão com Tab e use Enter e Espaço | Foco visível; leitor de tela anuncia "Modo daltonismo" e o estado |
| Com "reduzir movimento" ligado, alterne | Troca sem animação |

## 4. Largura e densidade

Em 360 px, com a legenda aberta e recolhida, com e sem gaveta aberta: o botão fica visível, tocável e
não cobre nada; o cabeçalho não estoura. Repita num celular de verdade para conferir se hachura e
pontos continuam legíveis.

## 5. Escala de cinza e simulações

No Chrome: DevTools > Rendering > *Emulate vision deficiencies*.

| Emulação | Esperado |
|---|---|
| Achromatopsia (escala de cinza) | Hachura, pontos e sem padrão se distinguem no mapa e na legenda; bordas contínua e tracejada também (SC-002, SC-002a) |
| Protanopia, Deuteranopia, Tritanopia | Níveis e situações se distinguem |

A emulação do Chrome não usa as mesmas matrizes do projeto. Ela serve para conferir a olho; o número
oficial é o do teste do passo 1.
