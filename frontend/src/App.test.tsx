import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import App from "./App";
import { ErroDeApi, type Mapa } from "./servicos/api/cliente";
import { criarApiSimulada } from "./testes/api-simulada";
import { MAPA_EXEMPLO } from "./testes/dados-exemplo";
import { simularMatchMedia, type MediaSimulada } from "./testes/match-media";
import { MapaFalso } from "./testes/mapa-falso";

const CELULAR = "(max-width: 700px)";
const MOVIMENTO_REDUZIDO = "(prefers-reduced-motion: reduce)";

let media: MediaSimulada;
beforeEach(() => {
  media = simularMatchMedia();
});
afterEach(() => {
  cleanup(); // desmonta a tela enquanto o matchMedia simulado ainda existe
  media.restaurar();
});

function desenhado(codigo: string): HTMLElement {
  const lista = screen.getByRole("list", { name: "territórios desenhados" });
  const item = lista.querySelector<HTMLElement>(`[data-codigo="${codigo}"]`);
  if (item === null) throw new Error(`território ${codigo} não foi entregue ao mapa`);
  return item;
}

async function abrir(mapa: Mapa = MAPA_EXEMPLO) {
  const api = criarApiSimulada({ mapa });
  render(<App cliente={api.cliente} Mapa={MapaFalso} />);
  await waitFor(() => expect(desenhado("DK")).toBeInTheDocument());
  return api;
}

describe("App: ver a situação do mundo", () => {
  it("entrega ao mapa os territórios com os níveis vindos de /mapa", async () => {
    await abrir();
    expect(desenhado("DK")).toHaveAttribute("data-nivel", "sem_alerta");
    expect(desenhado("LB")).toHaveAttribute("data-nivel", "evitar");
    expect(desenhado("BO")).toHaveAttribute("data-nivel", "nao_verificado");
    expect(desenhado("GL")).toHaveAttribute("data-nivel", "sem_alerta");
    expect(desenhado("XK")).toHaveAttribute("data-nivel", "sem_alerta");
  });

  it("faz uma única chamada a /mapa e nenhuma por país", async () => {
    const api = await abrir();
    expect(api.obterMapa).toHaveBeenCalledTimes(1);
    expect(api.obterPais).not.toHaveBeenCalled();
  });

  it("país com região de alerta mais grave recebe a borda regional", async () => {
    await abrir();
    expect(desenhado("LB")).toHaveAttribute("data-borda-regional", "nao_viajar");
    expect(desenhado("DK")).toHaveAttribute("data-borda-regional", "");
  });

  it("a borda regional segue a região mais grave", async () => {
    const mapa: Mapa = {
      ...MAPA_EXEMPLO,
      territorios: MAPA_EXEMPLO.territorios.map((t) =>
        t.codigo === "LB" ? { ...t, regioes: [{ nome: "Norte", nivel: "evitar" }] } : t,
      ),
    };
    await abrir(mapa);
    expect(desenhado("LB")).toHaveAttribute("data-borda-regional", "evitar");
  });

  it("sem coleta completa (dados_obtidos falso) nenhum território é 'sem alerta'", async () => {
    // mesmo que o servidor mande outra coisa, o padrão sem dado confirmado é não verificado
    await abrir({ ...MAPA_EXEMPLO, dados_obtidos: false, atualizado_em: null });
    for (const codigo of ["DK", "LB", "BO", "GL", "XK"]) {
      expect(desenhado(codigo)).toHaveAttribute("data-nivel", "nao_verificado");
      expect(desenhado(codigo)).toHaveAttribute("data-borda-regional", "");
    }
    expect(screen.getByText(/ainda não obtivemos os dados/i)).toBeVisible();
  });

  it("enquanto carrega, o mapa não tem nenhum território pintado de 'sem alerta'", async () => {
    const api = criarApiSimulada();
    api.obterMapa.mockReturnValue(new Promise(() => {})); // nunca responde
    render(<App cliente={api.cliente} Mapa={MapaFalso} />);

    expect(screen.getByRole("status")).toHaveTextContent(/carregando/i);
    const lista = screen.getByRole("list", { name: "territórios desenhados" });
    expect(within(lista).queryAllByRole("listitem")).toHaveLength(0);
  });

  it("mostra data da atualização, aviso de site não oficial e link para o Itamaraty", async () => {
    await abrir();
    expect(screen.getByText(/atualizado em 23 de outubro de 2026/i)).toBeVisible();
    expect(screen.getByText(/não é um serviço oficial/i)).toBeVisible();
    expect(screen.getByRole("link", { name: /portal consular do itamaraty/i })).toHaveAttribute(
      "href",
      expect.stringContaining("gov.br/mre"),
    );
  });

  it("avisa quando os dados estão desatualizados", async () => {
    await abrir({ ...MAPA_EXEMPLO, desatualizado: true });
    expect(screen.getByText(/dados desatualizados/i)).toBeVisible();
  });

  it("mostra a legenda em texto, o link 'Sobre as fronteiras' e o 'Sobre'", async () => {
    await abrir();
    const legenda = screen.getByRole("region", { name: "Legenda" });
    expect(legenda).toHaveTextContent("Sem alerta do Itamaraty");
    expect(legenda).toHaveTextContent("Evite viagens não essenciais");
    expect(legenda).toHaveTextContent("Não viaje");
    expect(legenda).toHaveTextContent("Não verificado");
    expect(screen.getByRole("button", { name: "Sobre as fronteiras deste mapa" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Sobre" })).toBeVisible();
  });

  it("não tem a seção 'Notícias' do protótipo", async () => {
    await abrir();
    expect(screen.queryByText(/notícias/i)).not.toBeInTheDocument();
  });

  it("o título da página é 'Farol Atlas'", async () => {
    await abrir();
    expect(screen.getByRole("heading", { level: 1, name: "Farol Atlas" })).toBeVisible();
  });
});

describe("App: erro ao carregar", () => {
  it("mostra o erro e deixa tentar de novo", async () => {
    const usuario = userEvent.setup();
    const api = criarApiSimulada({ mapa: new ErroDeApi(503, "Banco indisponível") });
    render(<App cliente={api.cliente} Mapa={MapaFalso} />);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Banco indisponível");
    expect(alerta).toHaveTextContent(/não verificado/i);

    api.obterMapa.mockResolvedValueOnce(MAPA_EXEMPLO);
    await usuario.click(screen.getByRole("button", { name: "Tentar de novo" }));

    await waitFor(() => expect(desenhado("LB")).toHaveAttribute("data-nivel", "evitar"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(api.obterMapa).toHaveBeenCalledTimes(2);
  });

  it("com erro, o mapa continua mostrando tudo como não verificado (nenhum território pintado)", async () => {
    const api = criarApiSimulada({ mapa: new ErroDeApi(0, "Sem rede") });
    render(<App cliente={api.cliente} Mapa={MapaFalso} />);
    await screen.findByRole("alert");
    const lista = screen.getByRole("list", { name: "territórios desenhados" });
    expect(within(lista).queryAllByRole("listitem")).toHaveLength(0);
  });
});

describe("App: celular e movimento reduzido", () => {
  it("em tela larga a legenda fica aberta", async () => {
    media.definir(CELULAR, false);
    const { container } = render(<App cliente={criarApiSimulada().cliente} Mapa={MapaFalso} />);
    await waitFor(() => expect(container.querySelector("details")).toBeInTheDocument());
    expect(container.querySelector("details")).toHaveProperty("open", true);
  });

  it("em tela de celular a legenda começa recolhida e abre pelo botão 'Legenda'", async () => {
    media.definir(CELULAR, true);
    const usuario = userEvent.setup();
    const { container } = render(<App cliente={criarApiSimulada().cliente} Mapa={MapaFalso} />);
    const detalhes = await waitFor(() => {
      const el = container.querySelector("details");
      if (el === null) throw new Error("sem legenda");
      return el;
    });
    expect(detalhes).toHaveProperty("open", false);

    await usuario.click(screen.getByText("Legenda", { selector: "summary" }));
    expect(detalhes).toHaveProperty("open", true);
  });

  it("passa 'reduzir movimento' ao mapa", async () => {
    media.definir(MOVIMENTO_REDUZIDO, true);
    await abrir();
    expect(screen.getByTestId("mapa-reduzir-movimento")).toHaveTextContent("true");
  });

  it("o mapa começa mostrando o mundo todo, sem seleção", async () => {
    await abrir();
    expect(screen.getByTestId("mapa-camera")).toHaveTextContent("mundo");
    expect(screen.getByTestId("mapa-selecionado")).toBeEmptyDOMElement();
  });
});
