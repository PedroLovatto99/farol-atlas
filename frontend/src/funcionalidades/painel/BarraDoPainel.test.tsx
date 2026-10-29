import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ALERTA_SO_REGIONAL, NIVEIS } from "../../compartilhado/niveis";
import { ROTULOS_DE_VISTO } from "../../compartilhado/vistos";
import type { Pais } from "../../servicos/api/cliente";
import {
  criarPais,
  criarVisto,
  PAIS_EXEMPLO,
  VISTO_EXIGIDO,
  VISTO_SEM_INFORMACAO,
} from "../../testes/dados-exemplo";
import type { ModoDoGlobo } from "../mapa/tipos";
import { BarraDoPainel } from "./BarraDoPainel";

afterEach(cleanup);

interface Opcoes {
  pais?: Pais;
  modoDoGlobo?: ModoDoGlobo;
  posicao?: "lateral" | "gaveta";
}

function abrir({ pais = PAIS_EXEMPLO, modoDoGlobo = "alertas", posicao = "lateral" }: Opcoes = {}) {
  const onAlternar = vi.fn();
  const onFechar = vi.fn();
  const resultado = render(
    <BarraDoPainel
      pais={pais}
      modoDoGlobo={modoDoGlobo}
      modo={posicao}
      onAlternar={onAlternar}
      onFechar={onFechar}
    />,
  );
  return { ...resultado, onAlternar, onFechar };
}

function barra() {
  return screen.getByRole("complementary", { name: "Detalhes do país (recolhido)" });
}

function expandir() {
  return screen.getByRole("button", { name: /^Expandir painel/ });
}

function todosOsElementos(): Element[] {
  return [barra(), ...Array.from(barra().querySelectorAll("*"))];
}

describe("BarraDoPainel: conteúdo", () => {
  it("mostra bandeira, nome e o nível, na horizontal, nos dois formatos", () => {
    for (const posicao of ["lateral", "gaveta"] as const) {
      const { container } = abrir({ posicao });
      expect(container.querySelector(".fi-dk")).not.toBeNull();
      expect(within(barra()).getByText("Dinamarca")).toBeVisible();
      expect(within(barra()).getByText("Sem alerta")).toBeVisible();
      for (const el of todosOsElementos()) {
        expect(el.className.toString()).not.toMatch(/vertical|rotate-90/);
        expect((el as HTMLElement).style.writingMode).toBe("");
      }
      cleanup();
    }
  });

  it("só a classe de posição muda entre os formatos", () => {
    abrir({ posicao: "lateral" });
    const classesLateral = barra().className;
    expect(classesLateral).toMatch(/right-2/);
    expect(classesLateral).toMatch(/top-16/);
    expect(classesLateral).toMatch(/w-\[340px\]/);
    const conteudoLateral = barra().innerHTML;
    cleanup();

    abrir({ posicao: "gaveta" });
    const classesGaveta = barra().className;
    expect(classesGaveta).toMatch(/inset-x-2/);
    expect(classesGaveta).toMatch(/bottom-2/);
    expect(classesGaveta).not.toMatch(/w-\[340px\]/);
    expect(barra().innerHTML).toBe(conteudoLateral);
    expect(barra()).toHaveAttribute("data-modo", "gaveta");
  });

  it("no modo Alertas mostra o rótulo do nível", () => {
    abrir({ pais: criarPais({ nivel: "nao_viajar" }) });
    expect(within(barra()).getByText("Não viaje")).toBeVisible();
    cleanup();
    abrir({ pais: criarPais({ nivel: "evitar" }) });
    expect(within(barra()).getByText("Evite")).toBeVisible();
    cleanup();
    abrir({ pais: criarPais({ nivel: "nao_verificado" }) });
    expect(within(barra()).getByText("Não verificado")).toBeVisible();
  });

  it("alerta só regional mostra o rótulo próprio", () => {
    abrir({ pais: criarPais({ nivel: "sem_alerta", regiao_unica_do_alerta: true }) });
    expect(within(barra()).getByText("Alerta regional")).toBeVisible();
  });

  it("no modo Vistos mostra a categoria, ou 'Sem informação de visto'", () => {
    abrir({ pais: criarPais({ visto: VISTO_EXIGIDO }), modoDoGlobo: "vistos" });
    expect(within(barra()).getByText("Exigido")).toBeVisible();
    cleanup();
    abrir({ pais: criarPais({ visto: VISTO_SEM_INFORMACAO }), modoDoGlobo: "vistos" });
    expect(within(barra()).getByText("Sem informação")).toBeVisible();
  });

  it("Kosovo e Malvinas mostram a categoria da própria linha, com o nome do território", () => {
    abrir({
      pais: criarPais({
        nome: "Sérvia",
        visto: criarVisto({ situacao: "visto_na_chegada", territorio_nome: "Kosovo" }),
      }),
      modoDoGlobo: "vistos",
    });
    expect(within(barra()).getByText("Kosovo: Na chegada")).toBeVisible();
    cleanup();
    abrir({
      pais: criarPais({
        nome: "Argentina",
        visto: criarVisto({ situacao: "isento", territorio_nome: "Ilhas Malvinas" }),
      }),
      modoDoGlobo: "vistos",
    });
    expect(within(barra()).getByText("Ilhas Malvinas: Isento")).toBeVisible();
  });

  it("o Brasil mostra só bandeira e nome, em qualquer modo", () => {
    for (const modoDoGlobo of ["alertas", "vistos"] as const) {
      const { container } = abrir({
        pais: criarPais({
          codigo: "BR",
          nome: "Brasil",
          bandeira: "BR",
          eh_brasil: true,
          visto: null,
        }),
        modoDoGlobo,
      });
      expect(within(barra()).getByText("Brasil")).toBeVisible();
      expect(container.querySelector(".fi-br")).not.toBeNull();
      expect(barra().querySelector("[data-situacao]")).toBeNull();
      expect(expandir()).toHaveAccessibleName("Expandir painel: Brasil");
      cleanup();
    }
  });

  it("texto com marcação aparece como texto, não vira HTML", () => {
    const { container } = abrir({
      pais: criarPais({
        nome: "<b>Nome</b>",
        visto: criarVisto({ territorio_nome: "<i>Terr</i>" }),
      }),
      modoDoGlobo: "vistos",
    });
    expect(screen.getByText("<b>Nome</b>")).toBeVisible();
    expect(screen.getByText(/<i>Terr<\/i>:/)).toBeVisible();
    expect(container.querySelector("b, i")).toBeNull();
  });
});

describe("BarraDoPainel: interação", () => {
  it("o botão principal tem nome acessível com país e situação e aria-expanded=false", () => {
    abrir();
    expect(expandir()).toHaveAccessibleName(
      `Expandir painel: Dinamarca, ${NIVEIS.sem_alerta.rotulo}`,
    );
    expect(expandir()).toHaveAttribute("aria-expanded", "false");
  });

  it("no modo Vistos o nome acessível leva a categoria", () => {
    abrir({ pais: criarPais({ visto: VISTO_EXIGIDO }), modoDoGlobo: "vistos" });
    expect(expandir()).toHaveAccessibleName(
      `Expandir painel: Dinamarca, ${ROTULOS_DE_VISTO.visto_exigido}`,
    );
  });

  it("a barra mostra o rótulo curto; o completo, com o prefixo de território, vai no title e no nome acessível", () => {
    const casos = [
      { visto: criarVisto({ situacao: "isento" }), curta: "Isento", completa: "Isento de visto" },
      {
        visto: criarVisto({ situacao: "visto_na_chegada" }),
        curta: "Na chegada",
        completa: "Visto na chegada",
      },
      {
        visto: criarVisto({ situacao: "autorizacao_eletronica" }),
        curta: "Eletrônico",
        completa: "Autorização ou visto eletrônico",
      },
      { visto: VISTO_EXIGIDO, curta: "Exigido", completa: "Visto exigido" },
      {
        visto: criarVisto({ situacao: "outra_situacao" }),
        curta: "Outra situação",
        completa: "Outra situação",
      },
      { visto: VISTO_SEM_INFORMACAO, curta: "Sem informação", completa: "Sem informação de visto" },
      {
        visto: criarVisto({
          situacao: "autorizacao_eletronica",
          territorio_nome: "Ilhas Malvinas",
        }),
        curta: "Ilhas Malvinas: Eletrônico",
        completa: "Ilhas Malvinas: Autorização ou visto eletrônico",
      },
      {
        visto: criarVisto({ situacao: "isento", territorio_nome: "Kosovo" }),
        curta: "Kosovo: Isento",
        completa: "Kosovo: Isento de visto",
      },
    ];
    for (const { visto, curta, completa } of casos) {
      abrir({ pais: criarPais({ visto }), modoDoGlobo: "vistos" });
      const situacao = within(barra()).getByText(curta);
      expect(situacao).toHaveAttribute("title", completa);
      expect(expandir()).toHaveAccessibleName(`Expandir painel: Dinamarca, ${completa}`);
      cleanup();
    }
  });

  it("nos alertas, o rótulo curto também tem o completo no title e no nome acessível", () => {
    const casos = [
      {
        pais: criarPais({ nivel: "sem_alerta" }),
        curta: "Sem alerta",
        completa: NIVEIS.sem_alerta.rotulo,
      },
      { pais: criarPais({ nivel: "evitar" }), curta: "Evite", completa: NIVEIS.evitar.rotulo },
      {
        pais: criarPais({ nivel: "nao_viajar" }),
        curta: "Não viaje",
        completa: NIVEIS.nao_viajar.rotulo,
      },
      {
        pais: criarPais({ nivel: "nao_verificado" }),
        curta: "Não verificado",
        completa: NIVEIS.nao_verificado.rotulo,
      },
      {
        pais: criarPais({ nivel: "sem_alerta", regiao_unica_do_alerta: true }),
        curta: "Alerta regional",
        completa: ALERTA_SO_REGIONAL.rotulo,
      },
    ];
    for (const { pais, curta, completa } of casos) {
      abrir({ pais });
      expect(within(barra()).getByText(curta)).toHaveAttribute("title", completa);
      expect(expandir()).toHaveAccessibleName(`Expandir painel: Dinamarca, ${completa}`);
      cleanup();
    }
  });

  it("clique, Enter e Espaço expandem", async () => {
    const usuario = userEvent.setup();
    const { onAlternar } = abrir();
    await usuario.click(expandir());
    expect(onAlternar).toHaveBeenCalledTimes(1);
    expandir().focus();
    await usuario.keyboard("{Enter}");
    expect(onAlternar).toHaveBeenCalledTimes(2);
    await usuario.keyboard(" ");
    expect(onAlternar).toHaveBeenCalledTimes(3);
  });

  it("'Ver mundo' fecha e não expande", async () => {
    const usuario = userEvent.setup();
    const { onFechar, onAlternar } = abrir();
    await usuario.click(screen.getByRole("button", { name: "Ver mundo" }));
    expect(onFechar).toHaveBeenCalledTimes(1);
    expect(onAlternar).not.toHaveBeenCalled();
  });

  it("o foco vai para o botão de expandir quando a barra aparece", () => {
    abrir();
    expect(expandir()).toHaveFocus();
  });
});

describe("BarraDoPainel: medidas e movimento", () => {
  it("alvos de 44 px, altura mínima de 56 px, sem largura fixa em px (fora a do painel lateral)", () => {
    abrir({ posicao: "gaveta" });
    expect(barra().className).toMatch(/min-h-14/);
    expect(expandir().className).toMatch(/min-h-11/);
    const verMundo = screen.getByRole("button", { name: "Ver mundo" });
    expect(verMundo.className).toMatch(/min-h-11/);
    expect(verMundo.className).toMatch(/min-w-11/);
    for (const el of todosOsElementos()) {
      expect(el.className.toString()).not.toMatch(/(^|\s)w-\[\d+px\]/);
    }
  });

  it("o nome fica em uma linha, com reticências, e o completo está no title e no nome acessível", () => {
    const longo = "Ilha Christmas e Ilhas Cocos (Austrália)";
    abrir({ pais: criarPais({ nome: longo }) });
    const nome = screen.getByText(longo);
    expect(nome.className.split(" ")).toContain("truncate");
    expect(nome.className).not.toMatch(/line-clamp|break-words/);
    expect(nome).toHaveAttribute("title", longo);
    expect(expandir()).toHaveAttribute("title", longo);
    expect(expandir()).toHaveAccessibleName(expect.stringContaining(longo));
  });

  it("a situação fica sempre em uma linha: rótulo curto e, se ainda assim não couber, reticências", () => {
    abrir();
    const situacao = screen.getByText("Sem alerta");
    expect(situacao.className.split(" ")).toContain("truncate");
    expect(situacao.className).not.toMatch(/line-clamp|break-words/);
  });

  it("nenhuma transição ou animação fora de motion-reduce", () => {
    abrir();
    for (const el of todosOsElementos()) {
      for (const classe of el.className.toString().split(/\s+/)) {
        expect(classe).not.toMatch(/^(transition|animate-|duration-)/);
      }
    }
  });
});
