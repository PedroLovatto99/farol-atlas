import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { MapaProps } from "../funcionalidades/mapa/tipos";
import { MapaFalso } from "./mapa-falso";

function propsBase(): MapaProps {
  return {
    territorios: [{ codigo: "DK", nivel: "sem_alerta", bordaRegional: null, esmaecido: false }],
    postos: [
      {
        grupo: "g1",
        cidade: "Copenhague",
        latitude: 1,
        longitude: 2,
        tipos: ["Embaixada"],
        territorios: ["DK"],
      },
    ],
    paisesSemPosto: [],
    selecionado: "DK",
    grupoEmDestaque: "g1",
    gruposDoPainel: ["g1"],
    reduzirMovimento: true,
    onSelecionarTerritorio: vi.fn(),
    onSelecionarGrupo: vi.fn(),
    onLimparSelecao: vi.fn(),
    camera: { tipo: "mundo" },
  };
}

describe("mapa falso dos testes", () => {
  it("mostra o que recebeu por props", () => {
    render(<MapaFalso {...propsBase()} />);
    expect(screen.getByTestId("mapa-selecionado")).toHaveTextContent("DK");
    expect(screen.getByTestId("mapa-grupo-em-destaque")).toHaveTextContent("g1");
    expect(screen.getByTestId("mapa-camera")).toHaveTextContent("mundo");
    expect(screen.getByTestId("mapa-reduzir-movimento")).toHaveTextContent("true");
  });

  it("simula os toques do usuário", async () => {
    const props = propsBase();
    const usuario = userEvent.setup();
    render(<MapaFalso {...props} />);
    await usuario.click(screen.getByRole("button", { name: "tocar DK" }));
    await usuario.click(screen.getByRole("button", { name: "tocar ícone g1" }));
    await usuario.click(screen.getByRole("button", { name: "tocar no oceano" }));
    expect(props.onSelecionarTerritorio).toHaveBeenCalledWith("DK");
    expect(props.onSelecionarGrupo).toHaveBeenCalledWith("g1");
    expect(props.onLimparSelecao).toHaveBeenCalledOnce();
  });
});
