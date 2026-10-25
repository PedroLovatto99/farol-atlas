import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CeuEstrelado, limparCacheDoCeu } from "./CeuEstrelado";
import { QUANTIDADE_DE_ESTRELAS, TAMANHO_DO_CEU } from "./estrelas";

function simularCanvas() {
  const contexto = {
    arc: vi.fn(),
    beginPath: vi.fn(),
    fill: vi.fn(),
    fillRect: vi.fn(),
    createRadialGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
    fillStyle: "",
  };
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
    contexto as unknown as CanvasRenderingContext2D,
  );
  const paraUrl = vi
    .spyOn(HTMLCanvasElement.prototype, "toDataURL")
    .mockReturnValue("data:image/png;base64,CEU");
  return { contexto, paraUrl };
}

beforeEach(() => limparCacheDoCeu());
afterEach(() => vi.restoreAllMocks());

const ceu = () => screen.getByTestId("ceu-estrelado");

describe("CeuEstrelado", () => {
  it("fica atrás do mapa, é decorativo e não pega toque", () => {
    render(<CeuEstrelado />);
    expect(ceu()).toHaveAttribute("aria-hidden", "true");
    expect(ceu()).toHaveClass("pointer-events-none", "absolute", "inset-0", "bg-ceu");
  });

  it("sem canvas (jsdom, navegador antigo) continua sendo só o fundo escuro, sem erro", async () => {
    render(<CeuEstrelado />);
    await new Promise((resolver) => setTimeout(resolver, 10));
    expect(ceu().style.backgroundImage).toBe("");
  });

  it("desenha as estrelas uma vez e as usa como imagem de fundo repetida", async () => {
    const { contexto, paraUrl } = simularCanvas();
    render(<CeuEstrelado />);

    await waitFor(() => expect(ceu().style.backgroundImage).toContain("data:image/png"));
    expect(ceu().style.backgroundRepeat).toBe("repeat");
    expect(ceu().style.backgroundSize).toBe(`${TAMANHO_DO_CEU}px ${TAMANHO_DO_CEU}px`);
    expect(contexto.arc).toHaveBeenCalledTimes(QUANTIDADE_DE_ESTRELAS);
    expect(paraUrl).toHaveBeenCalledTimes(1);
  });

  it("não redesenha ao renderizar de novo nem ao montar outra vez", async () => {
    const { paraUrl } = simularCanvas();
    const primeira = render(<CeuEstrelado />);
    await waitFor(() => expect(ceu().style.backgroundImage).not.toBe(""));

    primeira.rerender(<CeuEstrelado />);
    primeira.unmount();
    render(<CeuEstrelado />);
    await waitFor(() => expect(ceu().style.backgroundImage).not.toBe(""));

    expect(paraUrl).toHaveBeenCalledTimes(1);
  });

  it("não tem animação nenhuma (nem brilho), com ou sem reduzir movimento", async () => {
    simularCanvas();
    render(<CeuEstrelado />);
    await waitFor(() => expect(ceu().style.backgroundImage).not.toBe(""));
    expect(ceu().style.animation).toBe("");
    expect(ceu().className).not.toMatch(/animate|transition/);
  });
});
