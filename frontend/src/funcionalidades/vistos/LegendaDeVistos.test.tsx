import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TODAS_AS_CHAVES_DE_VISTO, type ChaveDeVisto } from "../../compartilhado/vistos";
import type { EstadoDosVistos } from "../../estado/reducer";
import { VISTOS_EXEMPLO } from "../../testes/dados-exemplo";
import { alternarVisto } from "../legenda/filtroDeVistos";
import { LegendaDeVistos } from "./LegendaDeVistos";

afterEach(cleanup);

const PRONTO: EstadoDosVistos = { situacao: "pronto", dados: VISTOS_EXEMPLO };

function Tela({
  estado = PRONTO,
  inicial = TODAS_AS_CHAVES_DE_VISTO,
  aoTentarDeNovo = vi.fn(),
}: {
  estado?: EstadoDosVistos;
  inicial?: readonly ChaveDeVisto[];
  aoTentarDeNovo?: () => void;
}) {
  const [marcadas, setMarcadas] = useState<readonly ChaveDeVisto[]>(inicial);
  return (
    <LegendaDeVistos
      estado={estado}
      marcadas={marcadas}
      onAlternar={(chave) => setMarcadas((atuais) => alternarVisto(atuais, chave))}
      onTentarDeNovo={aoTentarDeNovo}
    />
  );
}

const caixa = (nome: string) => screen.getByRole("checkbox", { name: new RegExp(`^${nome}`) });
const amostraDe = (nome: string) =>
  caixa(nome).closest("label")?.querySelector<HTMLElement>("[data-amostra]");

describe("LegendaDeVistos: categorias", () => {
  it("lista cada categoria em texto, com uma caixa de marcar, todas marcadas ao abrir", () => {
    render(<Tela />);
    for (const rotulo of [
      "Isento de visto",
      "Isento, entrada com RG",
      "Visto na chegada",
      "Autorização ou visto eletrônico",
      "Visto exigido",
      "Outra situação",
      "Sem informação de visto",
    ]) {
      expect(caixa(rotulo)).toBeChecked();
    }
    expect(screen.getAllByRole("checkbox")).toHaveLength(7);
  });

  it("'Isento, entrada com RG' é um subitem de 'Isento de visto'", () => {
    render(<Tela />);
    const pai = caixa("Isento de visto").closest("li") as HTMLElement;
    expect(within(pai).getByRole("checkbox", { name: /Isento, entrada com RG/ })).toBeVisible();
  });

  it("desmarcar o pai desmarca o subitem, e marcar de novo marca os dois", async () => {
    const usuario = userEvent.setup();
    render(<Tela />);
    await usuario.click(caixa("Isento de visto"));
    expect(caixa("Isento de visto")).not.toBeChecked();
    expect(caixa("Isento, entrada com RG")).not.toBeChecked();
    await usuario.click(caixa("Isento de visto"));
    expect(caixa("Isento de visto")).toBeChecked();
    expect(caixa("Isento, entrada com RG")).toBeChecked();
  });

  it("desmarcar só o subitem deixa o pai em estado misto, por atributo e por texto", async () => {
    render(<Tela />);
    await userEvent.setup().click(caixa("Isento, entrada com RG"));
    expect(caixa("Isento de visto")).toHaveAttribute("aria-checked", "mixed");
    expect(screen.getByText("(parcial)")).toBeVisible();
    expect(caixa("Isento, entrada com RG")).not.toBeChecked();
  });

  it("marcar só o subitem, com o pai desmarcado, também é estado misto", () => {
    render(<Tela inicial={["isento_rg", "visto_exigido"]} />);
    expect(caixa("Isento de visto")).toHaveAttribute("aria-checked", "mixed");
    expect(screen.getByText("(parcial)")).toBeVisible();
  });

  it("sem estado misto, o texto '(parcial)' não aparece e o pai não é 'mixed'", () => {
    render(<Tela />);
    expect(screen.queryByText("(parcial)")).not.toBeInTheDocument();
    expect(caixa("Isento de visto")).not.toHaveAttribute("aria-checked", "mixed");
  });

  it("clicar no pai em estado misto marca os dois", async () => {
    render(<Tela inicial={["isento", "visto_exigido"]} />);
    await userEvent.setup().click(caixa("Isento de visto"));
    expect(caixa("Isento de visto")).toBeChecked();
    expect(caixa("Isento, entrada com RG")).toBeChecked();
  });

  it("as outras categorias alternam sozinhas, pelo teclado também", async () => {
    const usuario = userEvent.setup();
    render(<Tela />);
    caixa("Visto exigido").focus();
    await usuario.keyboard(" ");
    expect(caixa("Visto exigido")).not.toBeChecked();
    expect(caixa("Visto na chegada")).toBeChecked();
  });
});

describe("LegendaDeVistos: amostras", () => {
  it("cada amostra tem borda de contraste (#5F5E5A) e é escondida do leitor de tela", () => {
    render(<Tela />);
    const todas = Array.from(document.querySelectorAll<HTMLElement>("[data-amostra]"));
    expect(todas).toHaveLength(8); // sete itens e o Brasil
    for (const amostra of todas) {
      expect(amostra).toHaveAttribute("aria-hidden", "true");
      expect(amostra.style.borderColor).toBe("rgb(95, 94, 90)");
    }
  });

  it("a amostra do RG é de listras, com os mesmos números da imagem do mapa", () => {
    render(<Tela />);
    const rg = amostraDe("Isento, entrada com RG");
    expect(rg?.style.backgroundImage).toContain("linear-gradient(135deg");
    expect(rg?.style.backgroundSize).toBe("8px 8px");
  });

  it("as demais amostras são de cor lisa, com a cor da categoria", () => {
    render(<Tela />);
    expect(amostraDe("Visto exigido")?.style.backgroundColor).toBe("rgb(59, 28, 107)"); // #3B1C6B
    expect(amostraDe("Visto exigido")?.style.backgroundImage).toBe("");
    expect(amostraDe("Isento de visto")?.style.backgroundColor).toBe("rgb(254, 221, 80)");
    expect(amostraDe("Sem informação de visto")?.style.backgroundColor).toBe("rgb(190, 186, 177)");
  });
});

describe("LegendaDeVistos: Brasil", () => {
  it("é um item informativo, sem caixa de marcar, com a cor neutra explicada em texto", () => {
    render(<Tela />);
    const item = screen.getByText("Brasil: seu país, sem seção de visto");
    expect(item).toBeVisible();
    expect(item.closest("li")?.querySelector('input[type="checkbox"]')).toBeNull();
  });
});

describe("LegendaDeVistos: carregando e erro", () => {
  it("carregando: 'Carregando os vistos…' no lugar dos itens", () => {
    render(<Tela estado={{ situacao: "carregando" }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando os vistos…");
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  });

  it("ainda não pedido conta como carregando (o pedido sai logo depois da escolha do modo)", () => {
    render(<Tela estado={{ situacao: "nao_pedido" }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando os vistos…");
  });

  it("erro: mensagem e 'Tentar de novo', sem itens", async () => {
    const aoTentar = vi.fn();
    render(<Tela estado={{ situacao: "erro", mensagem: "caiu" }} aoTentarDeNovo={aoTentar} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível carregar os vistos.");
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
    await userEvent.setup().click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(aoTentar).toHaveBeenCalledTimes(1);
  });

  it("sem coleta válida a legenda explica o cinza (todos 'sem informação')", () => {
    const dados = { ...VISTOS_EXEMPLO, dados_obtidos: false, coletado_em: null };
    render(<Tela estado={{ situacao: "pronto", dados }} />);
    expect(screen.getByText(/ainda não há dados de visto/i)).toBeVisible();
  });

  it("com dados, não diz que faltam dados", () => {
    render(<Tela />);
    expect(screen.queryByText(/ainda não há dados de visto/i)).not.toBeInTheDocument();
  });
});

describe("LegendaDeVistos: animação", () => {
  it("nenhuma transição ou animação nova fora de prefers-reduced-motion", () => {
    const { container } = render(<Tela />);
    const classes = Array.from(container.querySelectorAll("[class]")).flatMap((e) =>
      e.className.toString().split(/\s+/),
    );
    const animadas = classes.filter(
      (c) => /^(transition|animate|duration|ease)/.test(c) && !c.startsWith("motion-reduce:"),
    );
    expect(animadas).toEqual([]);
  });
});
