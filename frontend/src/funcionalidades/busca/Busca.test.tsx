import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../../App";
import type { Pais } from "../../servicos/api/cliente";
import { criarApiSimulada } from "../../testes/api-simulada";
import {
  criarPais,
  GEOMETRIA_EXEMPLO,
  MAPA_EXEMPLO,
  PAIS_EXEMPLO,
} from "../../testes/dados-exemplo";
import { MapaFalso } from "../../testes/mapa-falso";
import { simularMatchMedia, type MediaSimulada } from "../../testes/match-media";
import { limparCacheDaGeometria } from "../mapa/useGeometria";
import { Busca } from "./Busca";

let media: MediaSimulada;
beforeEach(() => {
  media = simularMatchMedia();
  limparCacheDaGeometria();
});
afterEach(() => {
  cleanup();
  media.restaurar();
});

describe("Busca (componente)", () => {
  function desenhar() {
    const aoEscolher = vi.fn<(codigo: string) => void>();
    render(<Busca territorios={MAPA_EXEMPLO.territorios} onEscolher={aoEscolher} />);
    return aoEscolher;
  }

  it("é um combobox e só abre a lista de sugestões quando há o que sugerir", async () => {
    desenhar();
    const campo = screen.getByRole("combobox", { name: /buscar país/i });
    expect(campo).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();

    await userEvent.setup().type(campo, "din");
    expect(campo).toHaveAttribute("aria-expanded", "true");
    const lista = screen.getByRole("listbox");
    expect(
      within(lista)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Dinamarca", "Groenlândia (Dinamarca)"]);
  });

  it("sugere enquanto digita, sem diferença de acento e de maiúsculas", async () => {
    desenhar();
    await userEvent.setup().type(screen.getByRole("combobox"), "GROENLANDIA");
    expect(screen.getByRole("option", { name: "Groenlândia (Dinamarca)" })).toBeVisible();
  });

  it("escolher uma sugestão com o mouse chama onEscolher com o código e limpa o campo", async () => {
    const aoEscolher = desenhar();
    const usuario = userEvent.setup();
    await usuario.type(screen.getByRole("combobox"), "gro");
    await usuario.click(screen.getByRole("option", { name: "Groenlândia (Dinamarca)" }));
    expect(aoEscolher).toHaveBeenCalledExactlyOnceWith("GL");
    expect(screen.getByRole("combobox")).toHaveValue("");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("navega pelo teclado: setas movem a opção ativa, Enter escolhe, Esc fecha", async () => {
    const aoEscolher = desenhar();
    const usuario = userEvent.setup();
    const campo = screen.getByRole("combobox");
    await usuario.type(campo, "din");

    await usuario.keyboard("{ArrowDown}");
    const primeira = screen.getByRole("option", { name: "Dinamarca" });
    expect(campo).toHaveAttribute("aria-activedescendant", primeira.id);
    expect(primeira).toHaveAttribute("aria-selected", "true");

    await usuario.keyboard("{ArrowDown}");
    expect(campo).toHaveAttribute(
      "aria-activedescendant",
      screen.getByRole("option", { name: "Groenlândia (Dinamarca)" }).id,
    );

    await usuario.keyboard("{ArrowUp}{Enter}");
    expect(aoEscolher).toHaveBeenCalledExactlyOnceWith("DK");

    await usuario.type(campo, "din");
    await usuario.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("Enter sem opção ativa escolhe a primeira sugestão", async () => {
    const aoEscolher = desenhar();
    await userEvent.setup().type(screen.getByRole("combobox"), "bol{Enter}");
    expect(aoEscolher).toHaveBeenCalledExactlyOnceWith("BO");
  });

  it("sem resultado mostra a mensagem e não escolhe nada", async () => {
    const aoEscolher = desenhar();
    await userEvent.setup().type(screen.getByRole("combobox"), "xyzzy{Enter}");
    expect(screen.getByRole("status")).toHaveTextContent(/nenhum país encontrado/i);
    expect(aoEscolher).not.toHaveBeenCalled();
  });

  it("a mensagem some quando o campo é apagado", async () => {
    desenhar();
    const usuario = userEvent.setup();
    await usuario.type(screen.getByRole("combobox"), "xyzzy");
    await usuario.clear(screen.getByRole("combobox"));
    expect(screen.queryByText(/nenhum país encontrado/i)).not.toBeInTheDocument();
  });

  it("o texto digitado nunca vira HTML", async () => {
    desenhar();
    await userEvent.setup().type(screen.getByRole("combobox"), "xyz{{img src=x}}");
    expect(document.querySelector("img")).toBeNull();
  });
});

describe("Busca dentro do App (como no toque)", () => {
  const KOSOVO: Pais = criarPais({
    codigo: "XK",
    nome: "Sérvia",
    bandeira: "RS",
    tipo: "dependencia",
    soberano: "RS",
    identidade_do_soberano: true,
    observacao: "Kosovo: o Brasil não reconhece a independência.",
    observacao_no_topo: true,
  });
  const GROENLANDIA: Pais = criarPais({
    codigo: "GL",
    nome: "Groenlândia (Dinamarca)",
    bandeira: "GL",
    tipo: "dependencia",
    soberano: "DK",
    observacao: "Território da Dinamarca.",
  });

  // A geometria de exemplo não tem a Groenlândia: sem ela não há o que enquadrar
  const GEOMETRIA = {
    ...GEOMETRIA_EXEMPLO,
    features: [
      ...GEOMETRIA_EXEMPLO.features,
      {
        type: "Feature",
        properties: {
          codigo: "GL",
          tipo: "dependencia",
          soberano: "DK",
          titulo: "Groenlândia",
          zoom: "GL",
        },
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [-55, 60],
              [-20, 60],
              [-20, 80],
              [-55, 80],
              [-55, 60],
            ],
          ],
        },
      },
    ],
  };
  const buscarGeometria: typeof fetch = () =>
    Promise.resolve(new Response(JSON.stringify(GEOMETRIA), { status: 200 }));

  async function abrir() {
    const api = criarApiSimulada({
      mapa: MAPA_EXEMPLO,
      paises: { DK: PAIS_EXEMPLO, XK: KOSOVO, GL: GROENLANDIA },
    });
    render(<App cliente={api.cliente} Mapa={MapaFalso} buscar={buscarGeometria} />);
    await screen.findByRole("list", { name: "territórios desenhados" });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "tocar DK" })).toBeInTheDocument(),
    );
    return api;
  }

  it("'groenlandia': escolher a sugestão abre o painel e pede a câmera", async () => {
    const api = await abrir();
    const usuario = userEvent.setup();
    await usuario.type(screen.getByRole("combobox"), "groenlandia");
    await usuario.click(screen.getByRole("option", { name: "Groenlândia (Dinamarca)" }));

    expect(api.obterPais).toHaveBeenCalledWith("GL", expect.anything());
    expect(await screen.findByRole("complementary", { name: "Detalhes do país" })).toBeVisible();
    expect(screen.getByTestId("mapa-selecionado")).toHaveTextContent("GL");
    await waitFor(() => expect(screen.getByTestId("mapa-camera")).toHaveTextContent("enquadrar"));
  });

  it("'kosovo': abre o painel da Sérvia, com a bandeira e a observação no topo", async () => {
    const api = await abrir();
    const usuario = userEvent.setup();
    await usuario.type(screen.getByRole("combobox"), "kosovo");
    await usuario.click(screen.getByRole("option", { name: "Kosovo (Sérvia)" }));

    expect(api.obterPais).toHaveBeenCalledWith("XK", expect.anything());
    const painel = await screen.findByRole("complementary", { name: "Detalhes do país" });
    expect(await within(painel).findByRole("heading", { name: "Sérvia" })).toBeVisible();
    expect(painel.querySelector(".fi-rs")).not.toBeNull();
    expect(
      within(painel).getByText("Kosovo: o Brasil não reconhece a independência."),
    ).toBeVisible();
    expect(screen.getByTestId("mapa-selecionado")).toHaveTextContent("XK");
    // o enquadramento usa o grupo do soberano (Sérvia), não um grupo próprio
    await waitFor(() => expect(screen.getByTestId("mapa-camera")).toHaveTextContent("enquadrar"));
  });

  it("sem resultado mostra a mensagem e o mapa não se move nem abre painel", async () => {
    const api = await abrir();
    await userEvent.setup().type(screen.getByRole("combobox"), "atlantida{Enter}");
    expect(screen.getByText(/nenhum país encontrado/i)).toBeVisible();
    expect(screen.getByTestId("mapa-camera")).toHaveTextContent("mundo");
    expect(screen.getByTestId("mapa-selecionado")).toBeEmptyDOMElement();
    expect(api.obterPais).not.toHaveBeenCalled();
  });

  it("país esmaecido pelo filtro continua encontrável pela busca (FR-026)", async () => {
    await abrir();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("checkbox", { name: "Sem alerta do Itamaraty" }));
    await usuario.type(screen.getByRole("combobox"), "dinamarca");
    await usuario.click(screen.getByRole("option", { name: "Dinamarca" }));
    expect(await screen.findByRole("complementary", { name: "Detalhes do país" })).toBeVisible();
  });

  it("antes de /mapa chegar a busca não tem o que sugerir", async () => {
    const api = criarApiSimulada();
    api.obterMapa.mockReturnValue(new Promise(() => {}));
    render(<App cliente={api.cliente} Mapa={MapaFalso} buscar={buscarGeometria} />);
    await userEvent.setup().type(screen.getByRole("combobox"), "din");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
