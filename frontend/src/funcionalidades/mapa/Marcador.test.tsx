import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createPortal } from "react-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Marcador } from "./Marcador";
import type { VarianteDoMarcador } from "./marcadores";

const tema = readFileSync(resolve(process.cwd(), "src/compartilhado/tema.css"), "utf-8");

afterEach(cleanup);

function desenhar(sobrescritas: Partial<Parameters<typeof Marcador>[0]> = {}) {
  const onToque = vi.fn();
  const resultado = render(
    <Marcador
      variante="embaixada"
      selo={0}
      rotulo="Embaixada em Washington"
      emDestaque={false}
      reduzirMovimento={false}
      onToque={onToque}
      {...sobrescritas}
    />,
  );
  return { ...resultado, onToque, botao: screen.getByRole("button") };
}

describe("Marcador: o desenho", () => {
  it.each<[VarianteDoMarcador, string]>([
    ["embaixada", "tabler-icon-building-bank"],
    ["consulado", "tabler-icon-building"],
    ["escritorio", "tabler-icon-briefcase"],
    ["sem-posto", "tabler-icon-map-pin-share"],
  ])("%s usa o ícone %s", (variante, classe) => {
    const { botao } = desenhar({ variante });
    expect(botao.querySelector(`.${classe}`)).not.toBeNull();
    expect(botao).toHaveAttribute("data-variante", variante);
  });

  it("é um botão com nome acessível (o ícone não é só desenho)", () => {
    desenhar({ rotulo: "Consulado-Geral em Miami" });
    expect(screen.getByRole("button", { name: "Consulado-Geral em Miami" })).toBeVisible();
  });

  it("ícone compartilhado por dois postos mostra o selo +1", () => {
    desenhar({ selo: 1 });
    expect(screen.getByText("+1")).toBeVisible();
  });

  it("sem o que dividir, não tem selo", () => {
    desenhar({ selo: 0 });
    expect(screen.queryByText(/^\+\d/)).not.toBeInTheDocument();
  });
});

describe("Marcador: o destaque (FR-018a)", () => {
  it("em destaque, expressa isso por estado acessível, não só por cor", () => {
    const { botao } = desenhar({ emDestaque: true });
    expect(botao).toHaveAttribute("aria-current", "true");
    expect(botao).toHaveAttribute("data-em-destaque", "true");
  });

  it("fora do destaque, não tem o estado", () => {
    const { botao } = desenhar({ emDestaque: false });
    expect(botao).not.toHaveAttribute("aria-current");
    expect(botao).toHaveAttribute("data-em-destaque", "false");
  });

  it("o tamanho e o contorno do destaque não ficam em medidas dentro do componente", () => {
    const { botao } = desenhar({ emDestaque: true });
    expect(botao.getAttribute("style")).toBeNull();
  });

  it("o tamanho e o contorno do destaque vêm de tokens de CSS", () => {
    expect(tema).toContain("--marcador-destaque-tamanho");
    expect(tema).toContain("--marcador-destaque-contorno");
  });

  it("com a animação ligada, o destaque anima", () => {
    const { botao } = desenhar({ emDestaque: true, reduzirMovimento: false });
    expect(botao).toHaveAttribute("data-animar", "true");
  });

  it("com movimento reduzido, o destaque aparece sem animação (FR-018f)", () => {
    const { botao } = desenhar({ emDestaque: true, reduzirMovimento: true });
    expect(botao).toHaveAttribute("data-em-destaque", "true");
    expect(botao).toHaveAttribute("data-animar", "false");
  });

  it("fora do destaque nunca anima", () => {
    const { botao } = desenhar({ emDestaque: false, reduzirMovimento: false });
    expect(botao).toHaveAttribute("data-animar", "false");
  });
});

describe("Marcador: o toque", () => {
  it("chama onToque", async () => {
    const { onToque, botao } = desenhar();
    await userEvent.setup().click(botao);
    expect(onToque).toHaveBeenCalledTimes(1);
  });

  it("não deixa o clique chegar ao mapa (o ícone vive dentro do conteiner do mapa)", async () => {
    // No mapa, o ícone é desenhado por portal dentro do elemento do marcador do MapLibre
    const conteinerDoMapa = document.createElement("div");
    const elementoDoMarcador = document.createElement("div");
    conteinerDoMapa.appendChild(elementoDoMarcador);
    document.body.appendChild(conteinerDoMapa);
    const aoClicarNoMapa = vi.fn();
    conteinerDoMapa.addEventListener("click", aoClicarNoMapa);
    const onToque = vi.fn();

    render(
      createPortal(
        <Marcador
          variante="embaixada"
          selo={0}
          rotulo="Embaixada em Washington"
          emDestaque={false}
          reduzirMovimento={false}
          onToque={onToque}
        />,
        elementoDoMarcador,
      ),
    );
    await userEvent.setup().click(screen.getByRole("button"));

    expect(onToque).toHaveBeenCalledTimes(1);
    expect(aoClicarNoMapa).not.toHaveBeenCalled();
    conteinerDoMapa.remove();
  });
});
