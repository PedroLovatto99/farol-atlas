import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Aviso } from "./Aviso";

const PORTAL = "https://www.gov.br/mre/pt-br/assuntos/portal-consular";

const BASE = {
  dadosObtidos: true,
  atualizadoEm: "2026-10-23T12:00:00Z",
  desatualizado: false,
};

describe("Aviso", () => {
  it("mostra a data da última atualização dos dados", () => {
    render(<Aviso {...BASE} />);
    expect(screen.getByText(/atualizado em 23 de outubro de 2026/i)).toBeVisible();
  });

  it("usa a data de Brasília, não a do UTC", () => {
    render(<Aviso {...BASE} atualizadoEm="2026-10-24T01:30:00Z" />); // 22h30 de 23/10 em Brasília
    expect(screen.getByText(/23 de outubro de 2026/i)).toBeVisible();
  });

  it("avisa que não é um serviço oficial, com link para o portal do Itamaraty", () => {
    render(<Aviso {...BASE} />);
    expect(screen.getByText(/não é um serviço oficial/i)).toBeVisible();
    const link = screen.getByRole("link", { name: /portal consular do itamaraty/i });
    expect(link).toHaveAttribute("href", PORTAL);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("o aviso de site não oficial aparece sempre, mesmo sem dados", () => {
    render(<Aviso dadosObtidos={false} atualizadoEm={null} desatualizado={false} />);
    expect(screen.getByText(/não é um serviço oficial/i)).toBeVisible();
    expect(screen.getByRole("link", { name: /portal consular do itamaraty/i })).toBeVisible();
  });

  it("avisa que os dados estão desatualizados", () => {
    render(<Aviso {...BASE} desatualizado />);
    expect(screen.getByRole("status")).toHaveTextContent(/dados desatualizados/i);
    expect(screen.getByRole("status")).toHaveTextContent(/mais de 3 dias/i);
  });

  it("sem aviso de desatualização quando os dados estão em dia", () => {
    render(<Aviso {...BASE} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("diz que os dados ainda não foram obtidos e não mostra data", () => {
    render(<Aviso dadosObtidos={false} atualizadoEm={null} desatualizado={false} />);
    expect(screen.getByRole("status")).toHaveTextContent(/ainda não obtivemos os dados/i);
    expect(screen.getByRole("status")).toHaveTextContent(/não verificado/i);
    expect(screen.queryByText(/atualizado em/i)).not.toBeInTheDocument();
  });

  describe("vistos desatualizados (FR-029a)", () => {
    it("com a última coleta de vistos antiga, avisa na área de avisos, sem painel aberto", () => {
      render(<Aviso {...BASE} vistosDesatualizados />);
      const aviso = screen.getByText(/dados de visto desatualizados/i);
      expect(aviso).toBeVisible();
      expect(aviso).toHaveTextContent(/mais de 14 dias/i);
      expect(aviso.closest("section")).toHaveAccessibleName("Avisos");
    });

    it("sem o sinal (modo 'Alertas' ou vistos em dia), o aviso não aparece", () => {
      const { rerender } = render(<Aviso {...BASE} />);
      expect(screen.queryByText(/dados de visto desatualizados/i)).not.toBeInTheDocument();
      rerender(<Aviso {...BASE} vistosDesatualizados={false} />);
      expect(screen.queryByText(/dados de visto desatualizados/i)).not.toBeInTheDocument();
    });

    it("convive com o aviso de alertas desatualizados", () => {
      render(<Aviso {...BASE} desatualizado vistosDesatualizados />);
      expect(screen.getByText(/mais de 3 dias/i)).toBeVisible();
      expect(screen.getByText(/dados de visto desatualizados/i)).toBeVisible();
    });
  });
});
