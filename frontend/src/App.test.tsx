import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import App from "./App";
import type { MapaProps } from "./funcionalidades/mapa/tipos";
import { limparCacheDaGeometria } from "./funcionalidades/mapa/useGeometria";
import { ErroDeApi, type Mapa, type Pais } from "./servicos/api/cliente";
import { criarApiSimulada } from "./testes/api-simulada";
import {
  ALERTA_EXEMPLO,
  criarPais,
  GEOMETRIA_EXEMPLO,
  MAPA_COM_POSTOS,
  MAPA_EXEMPLO,
  PAIS_COM_DOIS_POSTOS,
  PAIS_EXEMPLO,
  PAIS_SEM_POSTO,
} from "./testes/dados-exemplo";
import { simularMatchMedia, type MediaSimulada } from "./testes/match-media";
import { MapaFalso } from "./testes/mapa-falso";

const CELULAR = "(max-width: 700px)";
const MOVIMENTO_REDUZIDO = "(prefers-reduced-motion: reduce)";

let media: MediaSimulada;
beforeEach(() => {
  media = simularMatchMedia();
  limparCacheDaGeometria();
});
afterEach(() => {
  window.localStorage.clear(); // a escolha da legenda não pode vazar de um teste para o outro
  cleanup(); // desmonta a tela enquanto o matchMedia simulado ainda existe
  media.restaurar();
});

function desenhado(codigo: string): HTMLElement {
  const lista = screen.getByRole("list", { name: "territórios desenhados" });
  const item = lista.querySelector<HTMLElement>(`[data-codigo="${codigo}"]`);
  if (item === null) throw new Error(`território ${codigo} não foi entregue ao mapa`);
  return item;
}

/** O arquivo de geometria, servido de mentira (o mapa de verdade o carrega pela rede). */
const buscarGeometria: typeof fetch = () =>
  Promise.resolve(new Response(JSON.stringify(GEOMETRIA_EXEMPLO), { status: 200 }));

/** Mapa falso que também guarda as últimas props, para o teste chamar a tela como o mapa chamaria. */
const espiao: { props: MapaProps | null } = { props: null };
function propsDoMapa(): MapaProps {
  if (espiao.props === null) throw new Error("o mapa ainda não foi desenhado");
  return espiao.props;
}
function MapaEspiao(props: MapaProps) {
  useEffect(() => {
    espiao.props = props;
  });
  return <MapaFalso {...props} />;
}

async function abrir(
  mapa: Mapa = MAPA_EXEMPLO,
  paises: Readonly<Record<string, Pais>> = { DK: PAIS_EXEMPLO },
) {
  const api = criarApiSimulada({ mapa, paises });
  render(<App cliente={api.cliente} Mapa={MapaEspiao} buscar={buscarGeometria} />);
  await waitFor(() => expect(desenhado("DK")).toBeInTheDocument());
  return api;
}

async function tocar(codigo: string) {
  await userEvent.setup().click(screen.getByRole("button", { name: `tocar ${codigo}` }));
}

function painel() {
  return screen.queryByRole("complementary", { name: "Detalhes do país" });
}

const KOSOVO = criarPais({
  codigo: "XK",
  nome: "Sérvia",
  bandeira: "RS",
  tipo: "dependencia",
  soberano: "RS",
  identidade_do_soberano: true,
  observacao: "Kosovo: o Brasil não reconhece a independência.",
  observacao_no_topo: true,
});

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
    render(<App cliente={criarApiSimulada().cliente} Mapa={MapaFalso} />);
    const botao = await screen.findByRole("button", { name: "Legenda das cores" });
    expect(botao).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("region", { name: "Legenda" })).toBeVisible();
  });

  it("em tela de celular a legenda começa recolhida e abre pelo botão 'Legenda das cores'", async () => {
    media.definir(CELULAR, true);
    const usuario = userEvent.setup();
    render(<App cliente={criarApiSimulada().cliente} Mapa={MapaFalso} />);
    const botao = await screen.findByRole("button", { name: "Legenda das cores" });
    expect(botao).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();

    await usuario.click(botao);
    expect(botao).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("region", { name: "Legenda" })).toBeVisible();
  });

  it("o filtro por nível continua valendo com a legenda recolhida", async () => {
    media.definir(CELULAR, false);
    const usuario = userEvent.setup();
    render(<App cliente={criarApiSimulada().cliente} Mapa={MapaFalso} />);
    const botao = await screen.findByRole("button", { name: "Legenda das cores" });
    await usuario.click(screen.getByRole("checkbox", { name: "Não viaje" }));

    await usuario.click(botao); // recolhe
    await usuario.click(botao); // abre

    expect(screen.getByRole("checkbox", { name: "Não viaje" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Evite viagens não essenciais" })).toBeChecked();
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

describe("App: ver os detalhes de um país", () => {
  it("tocar num território faz uma única chamada a /paises/{codigo} e abre o painel", async () => {
    const api = await abrir();
    await tocar("DK");

    expect(await screen.findByRole("heading", { level: 2, name: "Dinamarca" })).toBeVisible();
    expect(painel()).toBeInTheDocument();
    expect(api.obterPais).toHaveBeenCalledTimes(1);
    expect(api.obterPais).toHaveBeenCalledWith("DK", expect.anything());
    expect(screen.getByTestId("mapa-selecionado")).toHaveTextContent("DK");
  });

  it("o mapa se aproxima: pede o enquadramento do território, com zoom máximo 5,5", async () => {
    await abrir();
    await tocar("DK");

    await waitFor(() => expect(propsDoMapa().camera.tipo).toBe("enquadrar"));
    expect(propsDoMapa().camera).toMatchObject({
      tipo: "enquadrar",
      caixa: [
        [8, 54.5],
        [15, 57.8],
      ],
      zoomMaximo: 5.5,
    });
  });

  it("no computador a margem deixa o lado do painel livre", async () => {
    media.definir("(max-width: 700px)", false);
    await abrir();
    await tocar("DK");
    await waitFor(() => expect(propsDoMapa().camera.tipo).toBe("enquadrar"));
    expect(propsDoMapa().camera).toMatchObject({ margem: { direita: 380, baixo: 20 } });
    expect(await screen.findByRole("complementary")).toHaveAttribute("data-modo", "lateral");
  });

  it("no celular a margem deixa a parte de baixo livre e o painel vira gaveta", async () => {
    media.definir("(max-width: 700px)", true);
    await abrir();
    await tocar("DK");
    await waitFor(() => expect(propsDoMapa().camera.tipo).toBe("enquadrar"));
    expect(propsDoMapa().camera).toMatchObject({
      margem: { direita: 20, baixo: Math.round(window.innerHeight * 0.55) },
    });
    expect(await screen.findByRole("complementary")).toHaveAttribute("data-modo", "gaveta");
  });

  it("tocar em Kosovo chama /paises/XK, abre o painel da Sérvia com a observação no topo e enquadra a Sérvia", async () => {
    const api = await abrir(MAPA_EXEMPLO, { XK: KOSOVO });
    await tocar("XK");

    expect(await screen.findByRole("heading", { level: 2, name: "Sérvia" })).toBeVisible();
    expect(api.obterPais).toHaveBeenCalledWith("XK", expect.anything());
    expect(screen.getByText("Kosovo: o Brasil não reconhece a independência.")).toBeVisible();
    expect(screen.getByTestId("mapa-selecionado")).toHaveTextContent("XK");
    // o grupo "RS" tem a Sérvia e o Kosovo; a caixa é a da Sérvia
    expect(propsDoMapa().camera).toMatchObject({
      tipo: "enquadrar",
      caixa: [
        [18.8, 42.2],
        [23, 46.2],
      ],
    });
  });

  it("os alertas do país aparecem no painel, com o que define o nível", async () => {
    await abrir(MAPA_EXEMPLO, {
      DK: criarPais({ nivel: "evitar", alertas: [ALERTA_EXEMPLO] }),
    });
    await tocar("DK");
    expect(await screen.findByText("Define o nível atual")).toBeVisible();
    expect(screen.getByRole("link", { name: ALERTA_EXEMPLO.titulo })).toBeVisible();
  });

  it("o oceano não abre painel", async () => {
    const api = await abrir();
    await userEvent.setup().click(screen.getByRole("button", { name: "tocar no oceano" }));
    expect(painel()).not.toBeInTheDocument();
    expect(api.obterPais).not.toHaveBeenCalled();
  });

  it("área neutra e códigos que o mapa não conhece não abrem painel", async () => {
    const api = await abrir();
    act(() => propsDoMapa().onSelecionarTerritorio("EH"));
    expect(painel()).not.toBeInTheDocument();
    expect(api.obterPais).not.toHaveBeenCalled();
    expect(screen.getByTestId("mapa-selecionado")).toBeEmptyDOMElement();
  });

  it("trocar de país abre o painel do novo, com uma chamada para cada", async () => {
    const api = await abrir(MAPA_EXEMPLO, {
      DK: PAIS_EXEMPLO,
      LB: criarPais({ codigo: "LB", nome: "Líbano", bandeira: "LB" }),
    });
    await tocar("DK");
    await screen.findByRole("heading", { level: 2, name: "Dinamarca" });
    await tocar("LB");

    expect(await screen.findByRole("heading", { level: 2, name: "Líbano" })).toBeVisible();
    expect(screen.queryByRole("heading", { level: 2, name: "Dinamarca" })).not.toBeInTheDocument();
    expect(api.obterPais).toHaveBeenCalledTimes(2);
  });

  it("erro ao carregar o país mostra a mensagem e deixa tentar de novo", async () => {
    const api = await abrir(MAPA_EXEMPLO, {});
    await tocar("DK"); // a API simulada responde 404 para o que não conhece

    expect(await screen.findByRole("alert")).toHaveTextContent("Território não encontrado");
    api.obterPais.mockResolvedValueOnce(PAIS_EXEMPLO);
    await userEvent.setup().click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(await screen.findByRole("heading", { level: 2, name: "Dinamarca" })).toBeVisible();
    expect(api.obterPais).toHaveBeenCalledTimes(2);
  });

  it("Esc fecha o painel e volta a câmera ao mundo", async () => {
    await abrir();
    await tocar("DK");
    await screen.findByRole("heading", { level: 2, name: "Dinamarca" });
    expect(propsDoMapa().camera.tipo).toBe("enquadrar");

    await userEvent.setup().keyboard("{Escape}");

    expect(painel()).not.toBeInTheDocument();
    expect(propsDoMapa().camera.tipo).toBe("mundo");
    expect(screen.getByTestId("mapa-selecionado")).toBeEmptyDOMElement();
  });

  it("o botão 'Ver mundo' fecha o painel e volta a câmera ao mundo", async () => {
    await abrir();
    await tocar("DK");
    await screen.findByRole("heading", { level: 2, name: "Dinamarca" });

    await userEvent.setup().click(screen.getByRole("button", { name: "Ver mundo" }));

    expect(painel()).not.toBeInTheDocument();
    expect(propsDoMapa().camera.tipo).toBe("mundo");
    expect(screen.getByTestId("mapa-selecionado")).toBeEmptyDOMElement();
  });

  it("tocar de novo no mesmo país enquadra outra vez (a pessoa pode ter movido o mapa)", async () => {
    await abrir();
    await tocar("DK");
    await waitFor(() => expect(propsDoMapa().camera.tipo).toBe("enquadrar"));
    const primeira = propsDoMapa().camera;

    await tocar("DK");
    await waitFor(() => expect(propsDoMapa().camera).not.toBe(primeira));
    expect(propsDoMapa().camera.tipo).toBe("enquadrar");
  });

  it("Esc com um modal aberto fecha só o modal, não o painel", async () => {
    await abrir();
    await tocar("DK");
    await screen.findByRole("heading", { level: 2, name: "Dinamarca" });
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Sobre" }));
    expect(screen.getByRole("dialog")).toBeVisible();

    await usuario.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(painel()).toBeInTheDocument();
  });

  it("com movimento reduzido, o mapa recebe a preferência junto do pedido de câmera", async () => {
    media.definir("(prefers-reduced-motion: reduce)", true);
    await abrir();
    await tocar("DK");
    await waitFor(() => expect(propsDoMapa().camera.tipo).toBe("enquadrar"));
    expect(propsDoMapa().reduzirMovimento).toBe(true);
  });

  it("sem a geometria carregada, tocar abre o painel e mantém a câmera", async () => {
    const api = criarApiSimulada();
    const semGeometria: typeof fetch = () => Promise.reject(new TypeError("sem rede"));
    render(<App cliente={api.cliente} Mapa={MapaEspiao} buscar={semGeometria} />);
    await waitFor(() => expect(desenhado("DK")).toBeInTheDocument());

    await tocar("DK");

    expect(await screen.findByRole("heading", { level: 2, name: "Dinamarca" })).toBeVisible();
    expect(propsDoMapa().camera.tipo).toBe("manter");
  });
});

describe("App: postos no mapa", () => {
  const PAISES = { DK: PAIS_EXEMPLO, US: PAIS_COM_DOIS_POSTOS, PR: PAIS_SEM_POSTO };
  const WASHINGTON = "38.9,-77";
  const MIAMI = "25.76,-80.19";

  function icone(grupo: string): HTMLElement {
    const lista = screen.getByRole("list", { name: "ícones de postos" });
    const item = lista.querySelector<HTMLElement>(`[data-grupo="${grupo}"]`);
    if (item === null) throw new Error(`ícone ${grupo} não foi entregue ao mapa`);
    return item;
  }

  function resumo(tipo: string): HTMLElement {
    return screen.getByText(tipo, { selector: "summary span" });
  }

  function aberto(tipo: string): boolean {
    return resumo(tipo).closest("details")?.open ?? false;
  }

  function destaque(): HTMLElement {
    return screen.getByTestId("mapa-grupo-em-destaque");
  }

  async function abrirComPostos() {
    return abrir(MAPA_COM_POSTOS, PAISES);
  }

  async function tocarIcone(grupo: string) {
    await userEvent.setup().click(screen.getByRole("button", { name: `tocar ícone ${grupo}` }));
  }

  it("entrega ao mapa um ícone por cidade, com os dois postos de Washington juntos", async () => {
    await abrirComPostos();
    expect(icone(WASHINGTON)).toHaveAttribute("data-tipos", "Embaixada|Consulado-Geral");
    expect(icone(MIAMI)).toHaveAttribute("data-tipos", "Consulado-Geral");
    expect(icone("55.6761,12.5683")).toHaveAttribute("data-tipos", "Embaixada");
  });

  it("entrega os países sem posto, ligados ao posto responsável", async () => {
    await abrirComPostos();
    const lista = screen.getByRole("list", { name: "ícones de países sem posto" });
    expect(lista.querySelector('[data-territorio="PR"]')).toHaveAttribute(
      "data-responsavel",
      MIAMI,
    );
    expect(lista.querySelector('[data-territorio="LY"]')).toHaveAttribute("data-responsavel", "");
  });

  it("tocar num ícone abre o painel do país com os postos expandidos e o ícone em destaque", async () => {
    const api = await abrirComPostos();
    await tocarIcone(WASHINGTON);

    expect(await screen.findByRole("heading", { level: 2, name: "Estados Unidos" })).toBeVisible();
    expect(api.obterPais).toHaveBeenCalledTimes(1);
    expect(api.obterPais).toHaveBeenCalledWith("US", expect.anything());
    expect(destaque()).toHaveTextContent(WASHINGTON);
    expect(screen.getByTestId("mapa-selecionado")).toHaveTextContent("US");
    // o ícone é compartilhado por dois postos: os dois abrem
    expect(aberto("Embaixada")).toBe(true);
    expect(aberto("Consulado-Geral")).toBe(true);
  });

  it("tocar num ícone não reenquadra o mapa (FR-018g)", async () => {
    await abrirComPostos();
    await tocarIcone(WASHINGTON);
    await screen.findByRole("heading", { level: 2, name: "Estados Unidos" });
    expect(propsDoMapa().camera.tipo).toBe("manter");
  });

  it("tocar num ícone de outro país troca o painel, sem reenquadrar", async () => {
    const api = await abrirComPostos();
    await tocar("DK");
    await screen.findByRole("heading", { level: 2, name: "Dinamarca" });
    expect(propsDoMapa().camera.tipo).toBe("enquadrar");

    await tocarIcone(WASHINGTON);

    expect(await screen.findByRole("heading", { level: 2, name: "Estados Unidos" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Dinamarca" })).not.toBeInTheDocument();
    expect(propsDoMapa().camera.tipo).toBe("manter");
    expect(api.obterPais).toHaveBeenCalledTimes(2);
  });

  it("tocar no ícone de um país sem posto seleciona o país, como o toque no território", async () => {
    await abrirComPostos();
    await userEvent.setup().click(screen.getByRole("button", { name: "tocar ícone sem posto PR" }));
    expect(await screen.findByRole("heading", { level: 2, name: /Porto Rico/ })).toBeVisible();
    expect(propsDoMapa().camera.tipo).toBe("enquadrar");
  });

  it("expandir um posto no painel põe o ícone dele em destaque", async () => {
    await abrirComPostos();
    await tocar("US");
    await screen.findByRole("heading", { level: 2, name: "Estados Unidos" });
    expect(destaque()).toBeEmptyDOMElement();

    await userEvent.setup().click(resumo("Embaixada"));

    await waitFor(() => expect(destaque()).toHaveTextContent(WASHINGTON));
  });

  it("expandir um posto pede ao mapa só para garantir que o ícone esteja visível", async () => {
    await abrirComPostos();
    await tocar("US");
    await screen.findByRole("heading", { level: 2, name: "Estados Unidos" });

    await userEvent.setup().click(resumo("Embaixada"));

    await waitFor(() => expect(propsDoMapa().camera.tipo).toBe("garantir-visivel"));
    expect(propsDoMapa().camera).toMatchObject({
      latitude: 38.9,
      longitude: -77,
      margem: { direita: 380 },
    });
  });

  it("recolher o posto tira o destaque", async () => {
    await abrirComPostos();
    await tocar("US");
    await screen.findByRole("heading", { level: 2, name: "Estados Unidos" });
    const usuario = userEvent.setup();

    await usuario.click(resumo("Embaixada"));
    await waitFor(() => expect(destaque()).toHaveTextContent(WASHINGTON));
    await usuario.click(resumo("Embaixada"));

    await waitFor(() => expect(destaque()).toBeEmptyDOMElement());
  });

  it("fechar o painel tira o destaque", async () => {
    await abrirComPostos();
    await tocarIcone(WASHINGTON);
    await screen.findByRole("heading", { level: 2, name: "Estados Unidos" });

    await userEvent.setup().click(screen.getByRole("button", { name: "Ver mundo" }));

    expect(destaque()).toBeEmptyDOMElement();
  });

  it("expandir o posto responsável de um país sem posto destaca o ícone dele, em outro país (FR-018e)", async () => {
    await abrirComPostos();
    await tocar("PR");
    await screen.findByRole("heading", { level: 2, name: /Porto Rico/ });

    await userEvent.setup().click(resumo("Consulado-Geral"));

    await waitFor(() => expect(destaque()).toHaveTextContent(MIAMI));
  });

  it("diz ao mapa quais ícones o painel aberto usa, para aparecerem em qualquer zoom", async () => {
    await abrirComPostos();
    expect(screen.getByTestId("mapa-grupos-do-painel")).toBeEmptyDOMElement();

    await tocar("US");
    await screen.findByRole("heading", { level: 2, name: "Estados Unidos" });
    expect(screen.getByTestId("mapa-grupos-do-painel")).toHaveTextContent(WASHINGTON);

    await userEvent.setup().click(screen.getByRole("button", { name: "Ver mundo" }));
    expect(screen.getByTestId("mapa-grupos-do-painel")).toBeEmptyDOMElement();
  });

  it("no painel de um país sem posto, o ícone do posto responsável também fica à mostra", async () => {
    await abrirComPostos();
    await tocar("PR");
    await screen.findByRole("heading", { level: 2, name: /Porto Rico/ });
    expect(screen.getByTestId("mapa-grupos-do-painel")).toHaveTextContent(MIAMI);
  });
});

describe("App: filtrar o mapa por nível (P5)", () => {
  const legenda = () => screen.getByRole("region", { name: "Legenda" });
  const caixa = (nome: string) => within(legenda()).getByRole("checkbox", { name: nome });

  it("abre com todos os níveis marcados e nenhum território esmaecido", async () => {
    await abrir();
    for (const codigo of ["DK", "LB", "BO", "GL", "XK"]) {
      expect(desenhado(codigo)).toHaveAttribute("data-esmaecido", "false");
    }
    expect(within(legenda()).getAllByRole("checkbox")).toHaveLength(4);
  });

  it("desmarcar 'sem alerta' esmaece só os países desse nível; marcar devolve a cor", async () => {
    await abrir();
    const usuario = userEvent.setup();
    await usuario.click(caixa("Sem alerta do Itamaraty"));

    expect(desenhado("DK")).toHaveAttribute("data-esmaecido", "true");
    expect(desenhado("GL")).toHaveAttribute("data-esmaecido", "true");
    expect(desenhado("LB")).toHaveAttribute("data-esmaecido", "false");
    // continua desenhado, com o nível e a cor: esmaecer não esconde nem pinta de cinza
    expect(desenhado("DK")).toHaveAttribute("data-nivel", "sem_alerta");

    await usuario.click(caixa("Sem alerta do Itamaraty"));
    expect(desenhado("DK")).toHaveAttribute("data-esmaecido", "false");
  });

  it("Líbano com só 'não viaje' marcado continua visível, por causa do Sul do Líbano (FR-027)", async () => {
    await abrir();
    const usuario = userEvent.setup();
    for (const nome of [
      "Sem alerta do Itamaraty",
      "Evite viagens não essenciais",
      "Não verificado",
    ]) {
      await usuario.click(caixa(nome));
    }
    expect(desenhado("LB")).toHaveAttribute("data-esmaecido", "false");
    expect(desenhado("DK")).toHaveAttribute("data-esmaecido", "true");
    expect(desenhado("BO")).toHaveAttribute("data-esmaecido", "true");
  });

  it("país esmaecido ainda abre o painel ao ser tocado (FR-026)", async () => {
    await abrir();
    const usuario = userEvent.setup();
    await usuario.click(caixa("Sem alerta do Itamaraty"));
    await tocar("DK");
    expect(await screen.findByRole("heading", { level: 2, name: "Dinamarca" })).toBeVisible();
  });

  it("sem coleta completa o filtro age sobre 'não verificado', como o mapa mostra", async () => {
    await abrir({ ...MAPA_EXEMPLO, dados_obtidos: false, atualizado_em: null });
    await userEvent.setup().click(caixa("Não verificado"));
    expect(desenhado("DK")).toHaveAttribute("data-esmaecido", "true");
    expect(desenhado("LB")).toHaveAttribute("data-esmaecido", "true");
  });

  it("com tudo desmarcado aparece a mensagem; o botão marca todos de novo", async () => {
    await abrir();
    const usuario = userEvent.setup();
    expect(screen.queryByText(/nenhum nível marcado/i)).not.toBeInTheDocument();
    for (const caixaDoNivel of within(legenda()).getAllByRole("checkbox")) {
      await usuario.click(caixaDoNivel);
    }
    expect(screen.getByText(/nenhum nível marcado/i)).toBeVisible();
    expect(desenhado("LB")).toHaveAttribute("data-esmaecido", "true");

    await usuario.click(screen.getByRole("button", { name: "Marcar todos os níveis" }));
    expect(screen.queryByText(/nenhum nível marcado/i)).not.toBeInTheDocument();
    expect(desenhado("LB")).toHaveAttribute("data-esmaecido", "false");
    for (const c of within(legenda()).getAllByRole("checkbox")) expect(c).toBeChecked();
  });

  it("mexer no filtro não fecha o painel aberto", async () => {
    await abrir();
    const usuario = userEvent.setup();
    await tocar("DK");
    await screen.findByRole("heading", { level: 2, name: "Dinamarca" });
    await usuario.click(caixa("Evite viagens não essenciais"));
    expect(painel()).toBeInTheDocument();
  });
});
