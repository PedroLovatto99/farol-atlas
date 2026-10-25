import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { criarPosto } from "../../testes/dados-exemplo";
import { Posto } from "./Posto";

afterEach(cleanup);

const COM_CONTATO = criarPosto({
  endereco: "Kristianiagade 3, 2100 Copenhague",
  telefone_plantao: "+45 3520 6400",
  contato_coletado_em: "2026-10-23T12:00:00Z",
  contato_fonte_url: "https://www.gov.br/mre/pt-br/embaixada-copenhague",
});

async function expandir() {
  const usuario = userEvent.setup();
  await usuario.click(screen.getByText("Embaixada")); // o tipo fica dentro do resumo
}

describe("Posto", () => {
  it("o resumo mostra o tipo e a cidade e começa recolhido", () => {
    const { container } = render(<Posto posto={COM_CONTATO} />);
    expect(screen.getByText("Embaixada")).toBeVisible();
    expect(screen.getByText("Copenhague")).toBeVisible();
    expect(container.querySelector("details")).toHaveProperty("open", false);
    expect(screen.queryByText("Kristianiagade 3, 2100 Copenhague")).not.toBeVisible();
  });

  it("expandido, mostra endereço, telefone de plantão, fonte e data da coleta", async () => {
    render(<Posto posto={COM_CONTATO} />);
    await expandir();

    expect(screen.getByText("Kristianiagade 3, 2100 Copenhague")).toBeVisible();
    expect(screen.getByRole("link", { name: "+45 3520 6400" })).toHaveAttribute(
      "href",
      "tel:+4535206400",
    );
    const fonte = screen.getByRole("link", { name: /fonte/i });
    expect(fonte).toHaveAttribute("href", "https://www.gov.br/mre/pt-br/embaixada-copenhague");
    expect(fonte).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(screen.getByText(/coletado em 23\/10\/2026/i)).toBeVisible();
  });

  it("sem endereço cadastrado, diz isso e não inventa fonte nem data", async () => {
    render(<Posto posto={criarPosto()} />);
    await expandir();

    expect(screen.getByText(/endereço ainda não cadastrado/i)).toBeVisible();
    expect(screen.getByText(/telefone de plantão ainda não cadastrado/i)).toBeVisible();
    expect(screen.queryByText(/coletado em/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /fonte/i })).not.toBeInTheDocument();
  });

  it("o link 'Abrir no Google Maps' usa o endereço quando há", async () => {
    render(<Posto posto={COM_CONTATO} />);
    await expandir();
    const link = screen.getByRole("link", { name: "Abrir no Google Maps" });
    expect(new URL(link.getAttribute("href") ?? "").searchParams.get("query")).toBe(
      "Kristianiagade 3, 2100 Copenhague",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("sem endereço, o link do Google Maps leva à cidade", async () => {
    render(<Posto posto={criarPosto()} />);
    await expandir();
    const link = screen.getByRole("link", { name: "Abrir no Google Maps" });
    expect(new URL(link.getAttribute("href") ?? "").searchParams.get("query")).toBe(
      "Embaixada do Brasil, Copenhague, Dinamarca",
    );
  });

  it("no posto responsável mostra também o país, onde ele fica", () => {
    render(
      <Posto
        posto={criarPosto({ tipo: "Consulado-Geral", cidade: "Miami", pais: "Estados Unidos" })}
        mostrarPais
      />,
    );
    expect(screen.getByText("Consulado-Geral")).toBeVisible();
    expect(screen.getByText(/Miami/)).toBeVisible();
    expect(screen.getByText(/Estados Unidos/)).toBeVisible();
  });

  it("texto com marcação aparece como texto, nunca como HTML", async () => {
    const { container } = render(
      <Posto posto={criarPosto({ endereco: "<img src=x onerror=alert(1)> Rua <b>A</b>" })} />,
    );
    await expandir();
    expect(screen.getByText("<img src=x onerror=alert(1)> Rua <b>A</b>")).toBeVisible();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
  });

  it("não faz link da fonte quando a URL não é http(s)", async () => {
    render(
      <Posto
        posto={criarPosto({
          endereco: "Rua A",
          contato_coletado_em: "2026-10-23T12:00:00Z",
          contato_fonte_url: "javascript:alert(1)",
        })}
      />,
    );
    await expandir();
    expect(screen.queryByRole("link", { name: /fonte/i })).not.toBeInTheDocument();
    expect(screen.getByText(/coletado em 23\/10\/2026/i)).toBeVisible();
  });
});

describe("Posto: aberto e fechado pelo estado da tela (destaque do ícone, FR-018a)", () => {
  it("o ícone do tipo do posto aparece no resumo, o mesmo do mapa", () => {
    const { container } = render(<Posto posto={criarPosto({ tipo: "Consulado-Geral" })} />);
    expect(container.querySelector("summary .tabler-icon-building")).not.toBeNull();
    cleanup();
    const embaixada = render(<Posto posto={criarPosto({ tipo: "Embaixada" })} />);
    expect(embaixada.container.querySelector("summary .tabler-icon-building-bank")).not.toBeNull();
    cleanup();
    const escritorio = render(<Posto posto={criarPosto({ tipo: "Escritório Comercial" })} />);
    expect(escritorio.container.querySelector("summary .tabler-icon-briefcase")).not.toBeNull();
  });

  it("abre quando a tela manda abrir e fecha quando manda fechar", () => {
    const { container, rerender } = render(<Posto posto={criarPosto()} aberto={false} />);
    const detalhes = container.querySelector("details");
    expect(detalhes).toHaveProperty("open", false);

    rerender(<Posto posto={criarPosto()} aberto />);
    expect(detalhes).toHaveProperty("open", true);
    expect(screen.getByRole("link", { name: "Abrir no Google Maps" })).toBeVisible();

    rerender(<Posto posto={criarPosto()} aberto={false} />);
    expect(detalhes).toHaveProperty("open", false);
  });

  it("avisa a tela quando a pessoa expande e quando recolhe", async () => {
    const aoAlternar = vi.fn();
    render(<Posto posto={criarPosto()} aberto={false} onAlternar={aoAlternar} />);
    const usuario = userEvent.setup();

    await usuario.click(screen.getByText("Embaixada"));
    await waitFor(() => expect(aoAlternar).toHaveBeenLastCalledWith(true));

    await usuario.click(screen.getByText("Embaixada"));
    await waitFor(() => expect(aoAlternar).toHaveBeenLastCalledWith(false));
  });
});
