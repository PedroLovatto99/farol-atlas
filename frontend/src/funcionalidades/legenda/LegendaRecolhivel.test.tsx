import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NIVEIS, ORDEM_DA_LEGENDA, type NivelId } from "../../compartilhado/niveis";
import { LegendaRecolhivel } from "./LegendaRecolhivel";
import { CHAVE_DA_LEGENDA } from "./preferencia";

beforeEach(() => {
  window.localStorage.clear();
});
afterEach(() => {
  vi.restoreAllMocks();
});

/** A tela guarda os níveis marcados; a legenda só os mostra (como no App). */
function Tela({ telaPequena }: { telaPequena: boolean }) {
  const [marcados, setMarcados] = useState<readonly NivelId[]>(ORDEM_DA_LEGENDA);
  return (
    <LegendaRecolhivel
      telaPequena={telaPequena}
      niveisMarcados={marcados}
      onAlternarNivel={(nivel) =>
        setMarcados((atuais) =>
          atuais.includes(nivel) ? atuais.filter((n) => n !== nivel) : [...atuais, nivel],
        )
      }
    />
  );
}

const botao = () => screen.getByRole("button", { name: "Legenda das cores" });
const caixas = () => screen.queryAllByRole("checkbox");

describe("LegendaRecolhivel: estado inicial", () => {
  it("em tela larga começa aberta", () => {
    render(<Tela telaPequena={false} />);
    expect(botao()).toHaveAttribute("aria-expanded", "true");
    expect(caixas()).toHaveLength(ORDEM_DA_LEGENDA.length);
    expect(screen.getByRole("region", { name: "Legenda" })).toBeVisible();
  });

  it("em tela estreita começa recolhida, e sobra só o botão", () => {
    render(<Tela telaPequena />);
    expect(botao()).toHaveAttribute("aria-expanded", "false");
    expect(botao()).toBeVisible();
    // recolhida, nada da legenda aparece nem recebe foco: nem as caixas, nem o link das fronteiras
    expect(caixas()).toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Sobre as fronteiras deste mapa" })).toBeNull();
    expect(screen.queryByText(/Ausência de alerta/)).not.toBeVisible();
  });

  it("o botão tem texto claro e o ícone é decorativo", () => {
    render(<Tela telaPequena={false} />);
    expect(botao()).toHaveTextContent("Legenda das cores");
    expect(botao().querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });
});

describe("LegendaRecolhivel: abrir e fechar", () => {
  it("o botão recolhe e mostra a legenda, e o aria-expanded acompanha", async () => {
    const usuario = userEvent.setup();
    render(<Tela telaPequena={false} />);

    await usuario.click(botao());
    expect(botao()).toHaveAttribute("aria-expanded", "false");
    expect(caixas()).toHaveLength(0);

    await usuario.click(botao());
    expect(botao()).toHaveAttribute("aria-expanded", "true");
    expect(caixas()).toHaveLength(ORDEM_DA_LEGENDA.length);
  });

  it("o aria-controls aponta para o conteúdo da legenda", () => {
    render(<Tela telaPequena={false} />);
    const alvo = document.getElementById(botao().getAttribute("aria-controls") ?? "");
    expect(alvo).not.toBeNull();
    expect(alvo).toContainElement(screen.getByRole("region", { name: "Legenda" }));
  });

  it("funciona pelo teclado: Tab chega ao botão e Enter ou Espaço alternam", async () => {
    const usuario = userEvent.setup();
    render(<Tela telaPequena />);

    await usuario.tab();
    expect(botao()).toHaveFocus();

    await usuario.keyboard("{Enter}");
    expect(botao()).toHaveAttribute("aria-expanded", "true");
    expect(botao()).toHaveFocus(); // o foco não se perde ao abrir

    await usuario.keyboard(" ");
    expect(botao()).toHaveAttribute("aria-expanded", "false");
    expect(botao()).toHaveFocus();
  });

  it("recolhida, o Tab não entra nas caixas escondidas", async () => {
    const usuario = userEvent.setup();
    render(<Tela telaPequena />);
    await usuario.tab();
    await usuario.tab();
    await usuario.tab();
    expect(document.activeElement?.tagName).not.toBe("INPUT"); // nenhuma caixa escondida
  });
});

describe("LegendaRecolhivel: o filtro por nível não se perde", () => {
  it("o que foi desmarcado continua desmarcado depois de recolher e abrir", async () => {
    const usuario = userEvent.setup();
    render(<Tela telaPequena={false} />);
    await usuario.click(screen.getByRole("checkbox", { name: NIVEIS.nao_viajar.rotulo }));

    await usuario.click(botao());
    await usuario.click(botao());

    expect(screen.getByRole("checkbox", { name: NIVEIS.nao_viajar.rotulo })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: NIVEIS.evitar.rotulo })).toBeChecked();
  });

  it("as caixas seguem funcionando depois de abrir a legenda recolhida", async () => {
    const usuario = userEvent.setup();
    render(<Tela telaPequena />);
    await usuario.click(botao());
    await usuario.click(screen.getByRole("checkbox", { name: NIVEIS.evitar.rotulo }));
    expect(screen.getByRole("checkbox", { name: NIVEIS.evitar.rotulo })).not.toBeChecked();
  });
});

describe("LegendaRecolhivel: estado lembrado entre visitas", () => {
  it("recolher em tela larga vale na próxima visita", async () => {
    const usuario = userEvent.setup();
    const primeira = render(<Tela telaPequena={false} />);
    await usuario.click(botao());
    expect(window.localStorage.getItem(CHAVE_DA_LEGENDA)).toBe("fechada");
    primeira.unmount();

    render(<Tela telaPequena={false} />);
    expect(botao()).toHaveAttribute("aria-expanded", "false");
  });

  it("abrir em tela estreita vale na próxima visita", async () => {
    const usuario = userEvent.setup();
    const primeira = render(<Tela telaPequena />);
    await usuario.click(botao());
    expect(window.localStorage.getItem(CHAVE_DA_LEGENDA)).toBe("aberta");
    primeira.unmount();

    render(<Tela telaPequena />);
    expect(botao()).toHaveAttribute("aria-expanded", "true");
  });

  it("valor guardado que não é de nenhum dos dois estados é ignorado", () => {
    window.localStorage.setItem(CHAVE_DA_LEGENDA, "talvez");
    render(<Tela telaPequena />);
    expect(botao()).toHaveAttribute("aria-expanded", "false");
  });

  it("sem escolha guardada, acompanha a largura da tela", () => {
    const { rerender } = render(<Tela telaPequena={false} />);
    expect(botao()).toHaveAttribute("aria-expanded", "true");
    rerender(<Tela telaPequena />);
    expect(botao()).toHaveAttribute("aria-expanded", "false");
  });

  it("depois de uma escolha da pessoa, mudar a largura não a desfaz", async () => {
    const usuario = userEvent.setup();
    const { rerender } = render(<Tela telaPequena />);
    await usuario.click(botao()); // abriu no celular
    rerender(<Tela telaPequena={false} />);
    rerender(<Tela telaPequena />);
    expect(botao()).toHaveAttribute("aria-expanded", "true");
  });

  it("sem localStorage (leitura e gravação lançam erro), abre na regra da largura e ainda alterna", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    const usuario = userEvent.setup();
    render(<Tela telaPequena={false} />);
    expect(botao()).toHaveAttribute("aria-expanded", "true");

    await usuario.click(botao());
    expect(botao()).toHaveAttribute("aria-expanded", "false");
    expect(within(document.body).queryAllByRole("checkbox")).toHaveLength(0);
  });
});
