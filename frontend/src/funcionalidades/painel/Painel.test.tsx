import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Pais } from "../../servicos/api/cliente";
import {
  ALERTA_EXEMPLO,
  criarPais,
  criarPosto,
  criarVisto,
  PAIS_EXEMPLO,
  VISTO_DESATUALIZADO,
  VISTO_EXIGIDO,
  VISTO_HERDADO,
  VISTO_ISENTO_COM_RG,
  VISTO_OUTRA_SITUACAO,
  VISTO_SEM_INFORMACAO,
} from "../../testes/dados-exemplo";
import { Painel } from "./Painel";
import type { EstadoDoPais } from "./usePais";

afterEach(cleanup);

function abrir(pais: Pais, onFechar = vi.fn()) {
  const estado: EstadoDoPais = { situacao: "pronto", pais };
  const resultado = render(<Painel estado={estado} onFechar={onFechar} onTentarDeNovo={vi.fn()} />);
  return { ...resultado, onFechar };
}

function painel() {
  return screen.getByRole("complementary", { name: "Detalhes do país" });
}

function bandeiras(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll(".fi")).map((el) => el.className);
}

const LIBANO = criarPais({
  codigo: "LB",
  nome: "Líbano",
  bandeira: "LB",
  nivel: "evitar",
  regioes: [{ nome: "Sul do Líbano", nivel: "nao_viajar" }],
  alertas: [
    {
      ...ALERTA_EXEMPLO,
      titulo: "Alerta Consular. Oriente Médio.",
      url: "https://www.gov.br/mre/pt-br/alertas/oriente-medio",
      define_nivel: true,
    },
    {
      ...ALERTA_EXEMPLO,
      titulo: "Alerta de viagem – Líbano (antigo)",
      url: "https://www.gov.br/mre/pt-br/alertas/libano-antigo",
      publicado_em: "2026-03-01T15:00:00Z",
      define_nivel: false,
    },
  ],
});

describe("Painel: cabeçalho e nível", () => {
  it("mostra bandeira, nome, nível e o texto explicativo", () => {
    const { container } = abrir(LIBANO);
    expect(within(painel()).getByRole("heading", { level: 2, name: "Líbano" })).toBeVisible();
    expect(bandeiras(container)).toEqual([expect.stringContaining("fi-lb")]);
    expect(within(painel()).getByText("Evite viagens não essenciais")).toBeVisible();
    expect(within(painel()).getByText(/recomenda evitar viagens não essenciais/i)).toBeVisible();
  });

  it("'sem alerta' diz que isso não é recomendação de viagem", () => {
    abrir(PAIS_EXEMPLO);
    expect(within(painel()).getByText("Sem alerta do Itamaraty")).toBeVisible();
    expect(within(painel()).getByText(/não significa que o governo recomenda/i)).toBeVisible();
  });

  it("não verificado aparece como tal", () => {
    abrir(criarPais({ nivel: "nao_verificado" }));
    expect(within(painel()).getByText("Não verificado")).toBeVisible();
  });

  it("Taiwan não mostra bandeira", () => {
    const { container } = abrir(
      criarPais({ codigo: "TW", nome: "Taiwan (China)", bandeira: null, tipo: "dependencia" }),
    );
    expect(bandeiras(container)).toEqual([]);
    expect(screen.getByRole("heading", { name: "Taiwan (China)" })).toBeVisible();
  });

  it("Kosovo mostra o nome e a bandeira da Sérvia, nunca uma própria", () => {
    const { container } = abrir(
      criarPais({
        codigo: "XK",
        nome: "Sérvia",
        bandeira: "RS",
        tipo: "dependencia",
        soberano: "RS",
        identidade_do_soberano: true,
        observacao: "Kosovo: o Brasil não reconhece a independência.",
        observacao_no_topo: true,
      }),
    );
    expect(screen.getByRole("heading", { level: 2, name: "Sérvia" })).toBeVisible();
    expect(bandeiras(container)).toEqual([expect.stringContaining("fi-rs")]);
    expect(container.querySelector(".fi-xk")).toBeNull();
  });

  it("Malvinas mostram o nome e a bandeira da Argentina", () => {
    const { container } = abrir(
      criarPais({
        codigo: "FK",
        nome: "Argentina",
        bandeira: "AR",
        tipo: "dependencia",
        soberano: "AR",
        identidade_do_soberano: true,
        observacao: "As Malvinas são administradas pelo Reino Unido.",
        observacao_no_topo: true,
      }),
    );
    expect(screen.getByRole("heading", { level: 2, name: "Argentina" })).toBeVisible();
    expect(bandeiras(container)).toEqual([expect.stringContaining("fi-ar")]);
    expect(container.querySelector(".fi-fk")).toBeNull();
  });

  it("o botão 'Ver mundo' fecha o painel", async () => {
    const { onFechar } = abrir(PAIS_EXEMPLO);
    await userEvent.setup().click(screen.getByRole("button", { name: "Ver mundo" }));
    expect(onFechar).toHaveBeenCalledTimes(1);
  });
});

describe("Painel: foco", () => {
  function Tela({ aberto }: { aberto: boolean }) {
    return (
      <>
        <button type="button">Quem abriu</button>
        {aberto && (
          <Painel
            estado={{ situacao: "pronto", pais: PAIS_EXEMPLO }}
            onFechar={vi.fn()}
            onTentarDeNovo={vi.fn()}
          />
        )}
      </>
    );
  }

  it("leva o foco para o painel ao abrir e devolve a quem estava com ele ao fechar", () => {
    const { rerender } = render(<Tela aberto={false} />);
    const quemAbriu = screen.getByRole("button", { name: "Quem abriu" });
    quemAbriu.focus();

    rerender(<Tela aberto />);
    expect(painel()).toHaveFocus();

    rerender(<Tela aberto={false} />);
    expect(quemAbriu).toHaveFocus();
  });

  it("o painel recebe o foco por código, mas não entra na ordem do Tab", () => {
    abrir(PAIS_EXEMPLO);
    expect(painel()).toHaveAttribute("tabindex", "-1");
  });
});

describe("Painel: regiões", () => {
  it("lista as regiões com alerta e o nível de cada uma", () => {
    abrir(LIBANO);
    const regioes = within(painel()).getByRole("region", { name: "Alertas regionais" });
    expect(within(regioes).getByText(/Sul do Líbano/)).toBeVisible();
    expect(within(regioes).getByText(/Não viaje/)).toBeVisible();
  });

  it("sem regiões, não mostra a seção", () => {
    abrir(PAIS_EXEMPLO);
    expect(screen.queryByRole("region", { name: "Alertas regionais" })).not.toBeInTheDocument();
  });

  it("avisa quando o alerta que rege vale só para a região", () => {
    abrir(
      criarPais({
        codigo: "PS",
        nome: "Palestina",
        nivel: "sem_alerta",
        regioes: [{ nome: "Faixa de Gaza", nivel: "nao_viajar" }],
        regiao_unica_do_alerta: true,
      }),
    );
    expect(within(painel()).getByText(/vale só para a região/i)).toBeVisible();
  });

  it("com alerta só regional, o título é 'Alerta só para parte do país', não 'Sem alerta'", () => {
    abrir(
      criarPais({
        codigo: "SY",
        nome: "Síria",
        nivel: "sem_alerta",
        regioes: [{ nome: "Norte da Síria", nivel: "nao_viajar" }],
        regiao_unica_do_alerta: true,
      }),
    );
    expect(within(painel()).getByText("Alerta só para parte do país")).toBeVisible();
    expect(within(painel()).queryByText("Sem alerta do Itamaraty")).not.toBeInTheDocument();
    expect(within(painel()).queryByText(/não publicou alerta/i)).not.toBeInTheDocument();
  });

  it("sem alerta de verdade continua com o título 'Sem alerta do Itamaraty'", () => {
    abrir(criarPais({ codigo: "BO", nome: "Bolívia", nivel: "sem_alerta" }));
    expect(within(painel()).getByText("Sem alerta do Itamaraty")).toBeVisible();
    expect(within(painel()).queryByText("Alerta só para parte do país")).not.toBeInTheDocument();
  });

  it("país com nível do país e regiões (Líbano) mostra o nível do país no topo", () => {
    abrir(LIBANO);
    expect(within(painel()).getByText("Evite viagens não essenciais")).toBeVisible();
    expect(within(painel()).queryByText("Alerta só para parte do país")).not.toBeInTheDocument();
  });

  it("não mostra esse aviso quando o alerta vale para o país inteiro", () => {
    abrir(LIBANO);
    expect(screen.queryByText(/vale só para a região/i)).not.toBeInTheDocument();
  });
});

describe("Painel: alertas", () => {
  it("lista os alertas com data e link para o original, marcando o que define o nível", () => {
    abrir(LIBANO);
    const alertas = within(painel()).getByRole("region", { name: "Alertas do Itamaraty" });
    const itens = within(alertas).getAllByRole("listitem");
    expect(itens).toHaveLength(2);

    const primeiro = within(itens[0] as HTMLElement);
    expect(primeiro.getByRole("link", { name: "Alerta Consular. Oriente Médio." })).toHaveAttribute(
      "href",
      "https://www.gov.br/mre/pt-br/alertas/oriente-medio",
    );
    expect(primeiro.getByText("17/08/2026")).toBeVisible();
    expect(primeiro.getByText("Define o nível atual")).toBeVisible();

    const segundo = within(itens[1] as HTMLElement);
    expect(segundo.getByText("01/03/2026")).toBeVisible();
    expect(segundo.queryByText("Define o nível atual")).not.toBeInTheDocument();
  });

  it("o link do alerta abre em outra aba, com rel seguro", () => {
    abrir(LIBANO);
    const link = screen.getByRole("link", { name: "Alerta Consular. Oriente Médio." });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("mostra a data de modificação quando há", () => {
    abrir(
      criarPais({
        alertas: [{ ...ALERTA_EXEMPLO, modificado_em: "2026-09-02T15:00:00Z" }],
      }),
    );
    expect(screen.getByText(/modificado em 02\/09\/2026/i)).toBeVisible();
  });

  it("indica a situação normalizada", () => {
    abrir(criarPais({ alertas: [{ ...ALERTA_EXEMPLO, situacao_normalizada: true }] }));
    expect(screen.getByText(/situação normalizada/i)).toBeVisible();
  });

  it("indica o alerta que ainda não foi classificado", () => {
    abrir(
      criarPais({
        nivel: "nao_verificado",
        alertas: [{ ...ALERTA_EXEMPLO, pendente: true }],
      }),
    );
    expect(screen.getByText(/ainda não classificado/i)).toBeVisible();
  });

  it("sem alertas, diz que nenhum alerta de viagem cita o país", () => {
    abrir(PAIS_EXEMPLO);
    expect(screen.getByText(/nenhum alerta de viagem do itamaraty cita/i)).toBeVisible();
  });

  it("título com marcação aparece como texto, nunca como HTML", () => {
    const { container } = abrir(
      criarPais({
        alertas: [{ ...ALERTA_EXEMPLO, titulo: "<script>alert(1)</script><b>Alerta</b>" }],
      }),
    );
    expect(screen.getByText("<script>alert(1)</script><b>Alerta</b>")).toBeVisible();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
  });
});

describe("Painel: postos", () => {
  it("lista os postos com tipo e cidade", () => {
    abrir(
      criarPais({
        postos: [
          criarPosto({ id: 1, tipo: "Embaixada", cidade: "Copenhague" }),
          criarPosto({ id: 2, tipo: "Consulado", cidade: "Aarhus" }),
        ],
      }),
    );
    const secao = within(painel()).getByRole("region", { name: "Representação brasileira" });
    expect(within(secao).getAllByRole("group")).toHaveLength(2); // cada <details> é um grupo
    expect(within(secao).getByText("Copenhague")).toBeVisible();
    expect(within(secao).getByText("Aarhus")).toBeVisible();
  });

  it("mostra a fonte dos postos, com links e a licença", () => {
    abrir(PAIS_EXEMPLO);
    const linha = screen.getByText(/^Postos:/);
    expect(linha.textContent).toBe(
      "Postos: Itamaraty e Wikipédia (CC BY-SA), conferidos em 21/10/2026",
    );
    expect(within(linha).getByRole("link", { name: "Itamaraty" })).toHaveAttribute(
      "href",
      expect.stringContaining("gov.br/mre"),
    );
    expect(within(linha).getByRole("link", { name: "Wikipédia" })).toHaveAttribute(
      "href",
      expect.stringContaining("wikipedia.org"),
    );
  });

  it("a linha de fonte fica abaixo da lista de postos", () => {
    abrir(PAIS_EXEMPLO);
    const lista = screen.getAllByRole("group")[0] as HTMLElement;
    const linha = screen.getByText(/^Postos:/);
    expect(lista.compareDocumentPosition(linha) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("país sem posto mostra o posto responsável, expansível, com o país dele", async () => {
    abrir(
      criarPais({
        codigo: "PR",
        nome: "Porto Rico (Estados Unidos)",
        postos: [],
        posto_responsavel: criarPosto({
          id: 90,
          tipo: "Consulado-Geral",
          cidade: "Miami",
          pais: "Estados Unidos",
        }),
      }),
    );
    expect(screen.getByText(/sem posto no país/i)).toBeVisible();
    expect(screen.getByText(/Miami/)).toBeVisible();
    await userEvent.setup().click(screen.getByText("Consulado-Geral"));
    expect(screen.getByRole("link", { name: "Abrir no Google Maps" })).toBeVisible();
    expect(screen.getByText(/^Postos:/)).toBeVisible();
  });

  it("Líbia orienta procurar o Itamaraty e não mostra a linha de fonte", () => {
    abrir(
      criarPais({
        codigo: "LY",
        nome: "Líbia",
        postos: [],
        sem_posto_indicado: true,
        fonte_postos: null,
      }),
    );
    expect(screen.getByText(/sem posto indicado na lista oficial/i)).toBeVisible();
    expect(screen.getByText(/procure o itamaraty/i)).toBeVisible();
    expect(screen.getByRole("link", { name: "Portal Consular" })).toHaveAttribute(
      "href",
      expect.stringContaining("gov.br/mre"),
    );
    expect(screen.queryByText(/^Postos:/)).not.toBeInTheDocument();
  });

  it("Brasil tem painel próprio, sem postos nem linha de fonte", () => {
    const { container } = abrir(
      criarPais({
        codigo: "BR",
        nome: "Brasil",
        bandeira: "BR",
        eh_brasil: true,
        postos: [],
        fonte_postos: null,
      }),
    );
    expect(screen.getByRole("heading", { level: 2, name: "Brasil" })).toBeVisible();
    expect(bandeiras(container)).toEqual([expect.stringContaining("fi-br")]);
    expect(screen.getByText(/toque em outro país/i)).toBeVisible();
    expect(screen.queryByRole("region", { name: "Representação brasileira" })).toBeNull();
    expect(screen.queryByText(/^Postos:/)).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Alertas do Itamaraty" })).toBeNull();
  });
});

describe("Painel: observações", () => {
  it("dependência mostra a observação com o link para 'Sobre as fronteiras deste mapa'", () => {
    abrir(
      criarPais({
        codigo: "GL",
        nome: "Groenlândia (Dinamarca)",
        tipo: "dependencia",
        soberano: "DK",
        observacao: "Território da Dinamarca.",
      }),
    );
    expect(screen.getByText("Território da Dinamarca.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Sobre as fronteiras deste mapa" })).toBeVisible();
  });

  it("país comum não tem observação nem o link", () => {
    abrir(PAIS_EXEMPLO);
    expect(
      screen.queryByRole("button", { name: "Sobre as fronteiras deste mapa" }),
    ).not.toBeInTheDocument();
  });

  it("para Kosovo e Malvinas a observação vem no topo, antes do nível", () => {
    abrir(
      criarPais({
        codigo: "XK",
        nome: "Sérvia",
        bandeira: "RS",
        identidade_do_soberano: true,
        observacao: "Kosovo: o Brasil não reconhece a independência.",
        observacao_no_topo: true,
      }),
    );
    const observacao = screen.getByText("Kosovo: o Brasil não reconhece a independência.");
    const nivel = screen.getByText("Sem alerta do Itamaraty");
    expect(
      observacao.compareDocumentPosition(nivel) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sobre as fronteiras deste mapa" })).toBeVisible();
  });

  it("nas outras dependências a observação vem depois do nível", () => {
    abrir(
      criarPais({
        codigo: "GL",
        nome: "Groenlândia (Dinamarca)",
        tipo: "dependencia",
        observacao: "Território da Dinamarca.",
      }),
    );
    const observacao = screen.getByText("Território da Dinamarca.");
    const nivel = screen.getByText("Sem alerta do Itamaraty");
    expect(
      nivel.compareDocumentPosition(observacao) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});

describe("Painel: carregando e erro", () => {
  it("enquanto carrega, avisa", () => {
    render(
      <Painel estado={{ situacao: "carregando" }} onFechar={vi.fn()} onTentarDeNovo={vi.fn()} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/carregando/i);
  });

  it("no erro, mostra a mensagem e deixa tentar de novo", async () => {
    const tentar = vi.fn();
    render(
      <Painel
        estado={{ situacao: "erro", mensagem: "Território não encontrado" }}
        onFechar={vi.fn()}
        onTentarDeNovo={tentar}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Território não encontrado");
    await userEvent.setup().click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(tentar).toHaveBeenCalledTimes(1);
  });

  it("mesmo carregando ou com erro, dá para voltar ao mundo", async () => {
    const onFechar = vi.fn();
    render(
      <Painel estado={{ situacao: "carregando" }} onFechar={onFechar} onTentarDeNovo={vi.fn()} />,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "Ver mundo" }));
    expect(onFechar).toHaveBeenCalledTimes(1);
  });
});

describe("Painel: seção de visto", () => {
  it("aparece abaixo dos alertas", () => {
    abrir(LIBANO);
    const alertas = within(painel()).getByRole("region", { name: "Alertas do Itamaraty" });
    const visto = within(painel()).getByRole("region", { name: "Visto" });
    expect(alertas.compareDocumentPosition(visto) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("mostra a categoria do país e o aviso de fonte não oficial", () => {
    abrir(PAIS_EXEMPLO);
    const visto = within(painel()).getByRole("region", { name: "Visto" });
    expect(within(visto).getByText("Isento de visto")).toBeVisible();
    expect(within(visto).getByText(/consulado ou embaixada/)).toBeVisible();
  });

  it("Kosovo mantém a identidade da Sérvia no painel e intitula a seção 'Visto: Kosovo'", () => {
    const { container } = abrir(
      criarPais({
        codigo: "XK",
        nome: "Sérvia",
        bandeira: "RS",
        tipo: "dependencia",
        soberano: "RS",
        identidade_do_soberano: true,
        visto: criarVisto({ territorio_nome: "Kosovo", situacao: "visto_exigido" }),
      }),
    );
    expect(screen.getByRole("heading", { level: 2, name: "Sérvia" })).toBeVisible();
    expect(bandeiras(container)).toEqual([expect.stringContaining("fi-rs")]);
    expect(screen.getByRole("region", { name: "Visto: Kosovo" })).toBeVisible();
    expect(screen.queryByRole("region", { name: "Visto" })).not.toBeInTheDocument();
  });

  it("Malvinas mantêm a identidade da Argentina e nunca mostram a entrada com RG", () => {
    abrir(
      criarPais({
        codigo: "FK",
        nome: "Argentina",
        bandeira: "AR",
        tipo: "dependencia",
        soberano: "AR",
        identidade_do_soberano: true,
        visto: criarVisto({ territorio_nome: "Ilhas Malvinas", aceita_rg: false }),
      }),
    );
    expect(screen.getByRole("heading", { level: 2, name: "Argentina" })).toBeVisible();
    const visto = screen.getByRole("region", { name: "Visto: Ilhas Malvinas" });
    expect(within(visto).queryByText("Entrada com o RG")).not.toBeInTheDocument();
  });

  it("país sem informação mostra o estado 'Sem informação de visto', nunca a seção ausente", () => {
    abrir(criarPais({ visto: VISTO_SEM_INFORMACAO }));
    const visto = within(painel()).getByRole("region", { name: "Visto" });
    expect(within(visto).getByText("Sem informação de visto")).toBeVisible();
    expect(within(visto).queryByText("Isento de visto")).not.toBeInTheDocument();
  });

  describe("Brasil", () => {
    function abrirBrasil() {
      return abrir(
        criarPais({
          codigo: "BR",
          nome: "Brasil",
          bandeira: "BR",
          eh_brasil: true,
          postos: [],
          fonte_postos: null,
          visto: null,
        }),
      );
    }

    it("não tem a seção: nem título, nem fonte, nem aviso", () => {
      abrirBrasil();
      expect(screen.queryByRole("region", { name: /^Visto/ })).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: /visto/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Visa requirements/ })).not.toBeInTheDocument();
      expect(screen.queryByText(/CC BY-SA/)).not.toBeInTheDocument();
      expect(screen.queryByText(/consulado ou embaixada/)).not.toBeInTheDocument();
    });

    it("não diz 'não se aplica' nem 'sem informação de visto'", () => {
      abrirBrasil();
      expect(screen.queryByText(/não se aplica/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/sem informação de visto/i)).not.toBeInTheDocument();
    });

    it("a ausência da seção segue o visto nulo, e só ele", () => {
      abrir(criarPais({ visto: null }));
      expect(screen.queryByRole("region", { name: /^Visto/ })).not.toBeInTheDocument();
    });
  });

  describe("o resto do painel é igual com a seção em qualquer estado", () => {
    /** O painel inteiro, menos a seção de visto (e os ids que o React gera a cada render). */
    function semAsecaoDeVisto(): string {
      const copia = painel().cloneNode(true) as HTMLElement;
      for (const secao of copia.querySelectorAll("section[aria-labelledby]")) {
        if (secao.querySelector("h3")?.textContent?.startsWith("Visto")) secao.remove();
      }
      return copia.innerHTML.replace(/ (id|aria-labelledby)="[^"]*"/g, "");
    }

    const ESTADOS = {
      "isento com RG": VISTO_ISENTO_COM_RG,
      "visto exigido": VISTO_EXIGIDO,
      "outra situação": VISTO_OUTRA_SITUACAO,
      "sem informação": VISTO_SEM_INFORMACAO,
      "herdado do soberano": VISTO_HERDADO,
      desatualizado: VISTO_DESATUALIZADO,
    };

    it.each(Object.entries(ESTADOS))("%s", (_nome, visto) => {
      abrir(PAIS_EXEMPLO);
      const base = semAsecaoDeVisto();
      cleanup();
      abrir(criarPais({ visto }));
      expect(semAsecaoDeVisto()).toBe(base);
    });
  });
});

describe("Painel: postos abertos e fechados pelo estado da tela", () => {
  const DOIS = criarPais({
    postos: [
      criarPosto({ id: 1, tipo: "Embaixada", cidade: "Copenhague" }),
      criarPosto({ id: 2, tipo: "Consulado", cidade: "Aarhus", grupo: "56.1,10.2" }),
    ],
  });

  function abertos(): boolean[] {
    return Array.from(document.querySelectorAll("details")).map((d) => d.open);
  }

  it("abre só os postos que a tela manda abrir", () => {
    render(
      <Painel
        estado={{ situacao: "pronto", pais: DOIS }}
        onFechar={vi.fn()}
        onTentarDeNovo={vi.fn()}
        postosExpandidos={[2]}
        onAlternarPosto={vi.fn()}
      />,
    );
    expect(abertos()).toEqual([false, true]);
  });

  it("avisa a tela qual posto foi expandido e qual foi recolhido", async () => {
    const aoAlternar = vi.fn();
    render(
      <Painel
        estado={{ situacao: "pronto", pais: DOIS }}
        onFechar={vi.fn()}
        onTentarDeNovo={vi.fn()}
        postosExpandidos={[]}
        onAlternarPosto={aoAlternar}
      />,
    );
    await userEvent.setup().click(screen.getByText("Aarhus"));
    await waitFor(() =>
      expect(aoAlternar).toHaveBeenCalledWith(expect.objectContaining({ id: 2 }), true),
    );
  });

  it("o posto responsável também abre e avisa a tela (FR-018e)", async () => {
    const aoAlternar = vi.fn();
    const responsavel = criarPosto({
      id: 91,
      tipo: "Consulado-Geral",
      cidade: "Miami",
      pais: "Estados Unidos",
      grupo: "25.76,-80.19",
    });
    render(
      <Painel
        estado={{
          situacao: "pronto",
          pais: criarPais({ postos: [], posto_responsavel: responsavel }),
        }}
        onFechar={vi.fn()}
        onTentarDeNovo={vi.fn()}
        postosExpandidos={[]}
        onAlternarPosto={aoAlternar}
      />,
    );
    await userEvent.setup().click(screen.getByText("Consulado-Geral"));
    await waitFor(() =>
      expect(aoAlternar).toHaveBeenCalledWith(expect.objectContaining({ id: 91 }), true),
    );
  });
});
