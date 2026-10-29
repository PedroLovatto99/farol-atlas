import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import type { Visto } from "../../servicos/api/cliente";
import {
  criarVisto,
  VISTO_DESATUALIZADO,
  VISTO_EXIGIDO,
  VISTO_HERDADO,
  VISTO_ISENTO_COM_RG,
  VISTO_OUTRA_SITUACAO,
  VISTO_SEM_INFORMACAO,
} from "../../testes/dados-exemplo";
import { SecaoVisto } from "./SecaoVisto";

afterEach(cleanup);

function abrir(visto: Visto) {
  return render(<SecaoVisto visto={visto} />);
}

function secao(nome: string | RegExp = "Visto") {
  return screen.getByRole("region", { name: nome });
}

const OBSERVACAO_TRADUZIDA = {
  texto_original: "Passport valid for 6 months required.",
  traducao: "É exigido passaporte válido por 6 meses.",
};

describe("SecaoVisto: categoria e permanência", () => {
  it("'Isento de visto' aparece em texto, com '90 dias'", () => {
    abrir(criarVisto());
    expect(within(secao()).getByRole("heading", { level: 3, name: "Visto" })).toBeVisible();
    expect(within(secao()).getByText("Isento de visto")).toBeVisible();
    expect(within(secao()).getByText("90 dias")).toBeVisible();
  });

  it.each([
    ["visto_na_chegada", "Visto na chegada"],
    ["autorizacao_eletronica", "Autorização ou visto eletrônico"],
    ["visto_exigido", "Visto exigido"],
    ["outra_situacao", "Outra situação"],
  ] as const)("a categoria %s também aparece em texto: %s", (situacao, rotulo) => {
    abrir(criarVisto({ situacao }));
    expect(within(secao()).getByText(rotulo)).toBeVisible();
  });

  it("sem permanência na fonte, a linha não existe (nada de 'ilimitado')", () => {
    abrir(VISTO_EXIGIDO);
    expect(screen.queryByText(/permanência/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ilimitad/i)).not.toBeInTheDocument();
  });

  it("permanência 'original' aparece em inglês, como a fonte escreveu, avisando que não foi traduzida", () => {
    abrir(criarVisto({ permanencia: { tipo: "original", texto: "Up to 90 days, extendable" } }));
    const texto = screen.getByText("Up to 90 days, extendable");
    expect(texto).toHaveAttribute("lang", "en");
    expect(within(secao()).getByText(/não traduzido/)).toBeVisible();
  });

  it("permanência padronizada não traz o aviso de não traduzido", () => {
    abrir(criarVisto({ permanencia: { tipo: "padronizada", texto: "3 meses" } }));
    expect(within(secao()).getByText("3 meses")).toBeVisible();
    expect(screen.queryByText(/não traduzido/)).not.toBeInTheDocument();
  });

  it("prazos que variam conforme o motivo usam a frase fixa, sem escolher um prazo", () => {
    abrir(
      criarVisto({
        varia_conforme_motivo: true,
        permanencia: { tipo: "varia_conforme_motivo", texto: null },
      }),
    );
    expect(within(secao()).getByText("Varia conforme o motivo (ver observações)")).toBeVisible();
    expect(screen.queryByText("90 dias")).not.toBeInTheDocument();
  });

  it("prazos divergentes na fonte usam a frase fixa", () => {
    abrir(criarVisto({ permanencia: { tipo: "prazos_divergentes", texto: null } }));
    expect(
      within(secao()).getByText("Prazos divergentes na fonte (ver observações)"),
    ).toBeVisible();
  });

  it("a nota 'Varia conforme o motivo da viagem' aparece quando a regra varia", () => {
    abrir(
      criarVisto({
        varia_conforme_motivo: true,
        rotulo_original: "Visa not required / Visa required",
      }),
    );
    expect(within(secao()).getByText("Varia conforme o motivo da viagem")).toBeVisible();
  });

  it("sem variação por motivo, a nota não aparece", () => {
    abrir(criarVisto());
    expect(screen.queryByText("Varia conforme o motivo da viagem")).not.toBeInTheDocument();
  });
});

describe("SecaoVisto: RG", () => {
  it("quando basta o RG, diz isso de forma explícita, além da categoria", () => {
    abrir(VISTO_ISENTO_COM_RG);
    expect(within(secao()).getByText("Isento de visto")).toBeVisible();
    expect(within(secao()).getByText("Entrada com o RG")).toBeVisible();
  });

  it("sem RG, não diz nada sobre RG", () => {
    abrir(criarVisto());
    expect(screen.queryByText(/RG/)).not.toBeInTheDocument();
  });

  it("Ilhas Malvinas nunca mostram a entrada com RG", () => {
    abrir(criarVisto({ territorio_nome: "Ilhas Malvinas", aceita_rg: false }));
    expect(screen.queryByText("Entrada com o RG")).not.toBeInTheDocument();
  });
});

describe("SecaoVisto: rótulo da fonte", () => {
  it("'Outra situação' mostra o rótulo original da fonte", () => {
    abrir(VISTO_OUTRA_SITUACAO);
    expect(within(secao()).getByText("Outra situação")).toBeVisible();
    expect(within(secao()).getByText("Special permit required")).toBeVisible();
  });

  it("rótulo combinado mostra o original ao lado da categoria mais exigente", () => {
    abrir(
      criarVisto({
        situacao: "autorizacao_eletronica",
        rotulo_original: "eVisa / Visa on arrival",
      }),
    );
    expect(within(secao()).getByText("Autorização ou visto eletrônico")).toBeVisible();
    expect(within(secao()).getByText("eVisa / Visa on arrival")).toBeVisible();
  });

  it("o rótulo original fica marcado como inglês", () => {
    abrir(VISTO_OUTRA_SITUACAO);
    expect(screen.getByText("Special permit required")).toHaveAttribute("lang", "en");
  });
});

describe("SecaoVisto: observações", () => {
  it("mostra a tradução, identificada como automática, e deixa abrir o original em inglês", async () => {
    abrir(criarVisto({ observacoes: [OBSERVACAO_TRADUZIDA] }));
    expect(within(secao()).getByText("É exigido passaporte válido por 6 meses.")).toBeVisible();
    expect(within(secao()).getByText(/tradução automática/)).toBeVisible();

    const original = within(secao()).getByText("Passport valid for 6 months required.");
    expect(original).not.toBeVisible(); // dentro de <details> fechado
    await userEvent.setup().click(within(secao()).getByText("Ver o texto original"));
    expect(original).toBeVisible();
    expect(original).toHaveAttribute("lang", "en");
  });

  it("sem tradução, mostra o original em inglês avisando que não foi traduzido", () => {
    abrir(
      criarVisto({
        observacoes: [{ texto_original: "Visa valid for 30 days.", traducao: null }],
      }),
    );
    const original = within(secao()).getByText("Visa valid for 30 days.");
    expect(original).toBeVisible();
    expect(original).toHaveAttribute("lang", "en");
    expect(within(secao()).getByText(/não traduzido/)).toBeVisible();
    expect(screen.queryByText(/tradução automática/)).not.toBeInTheDocument();
    expect(screen.queryByText("Ver o texto original")).not.toBeInTheDocument();
  });

  it("preserva as quebras de linha da tradução e do original", async () => {
    abrir(
      criarVisto({
        observacoes: [
          {
            texto_original: "Tourism: 30 days.\nBusiness: 90 days.",
            traducao: "Turismo: 30 dias.\nNegócios: 90 dias.",
          },
          { texto_original: "Line 1\nLine 2", traducao: null },
        ],
      }),
    );
    const traducao = within(secao()).getByText(/Turismo: 30 dias\./);
    expect(traducao.textContent).toBe("Turismo: 30 dias.\nNegócios: 90 dias.");
    expect(traducao).toHaveStyle({ whiteSpace: "pre-line" });

    await userEvent
      .setup()
      .click(within(secao()).getAllByText("Ver o texto original")[0] as HTMLElement);
    const original = within(secao()).getByText(/Tourism: 30 days\./);
    expect(original.textContent).toBe("Tourism: 30 days.\nBusiness: 90 days.");
    expect(original).toHaveStyle({ whiteSpace: "pre-line" });

    expect(within(secao()).getByText(/Line 1/)).toHaveStyle({ whiteSpace: "pre-line" });
  });

  it("sem observações, não mostra a lista", () => {
    abrir(criarVisto());
    expect(within(secao()).queryByRole("list")).not.toBeInTheDocument();
    expect(screen.queryByText(/observações/i)).not.toBeInTheDocument();
  });

  it("lista cada observação como um item", () => {
    abrir(
      criarVisto({
        observacoes: [
          OBSERVACAO_TRADUZIDA,
          { texto_original: "Second note.", traducao: "Segunda nota." },
        ],
      }),
    );
    expect(within(secao()).getAllByRole("listitem")).toHaveLength(2);
  });
});

describe("SecaoVisto: sem informação", () => {
  it("diz 'Sem informação de visto', sem categoria, sem permanência e sem data", () => {
    abrir(VISTO_SEM_INFORMACAO);
    expect(within(secao()).getByText("Sem informação de visto")).toBeVisible();
    for (const rotulo of [
      "Isento de visto",
      "Visto na chegada",
      "Autorização ou visto eletrônico",
      "Visto exigido",
      "Outra situação",
    ]) {
      expect(screen.queryByText(rotulo)).not.toBeInTheDocument();
    }
    expect(screen.queryByText(/permanência/i)).not.toBeInTheDocument();
    expect(secao().querySelector("time")).toBeNull();
    expect(screen.queryByText("Entrada com o RG")).not.toBeInTheDocument();
  });

  it("explica que não há dado e ainda manda conferir com o consulado ou a embaixada", () => {
    abrir(VISTO_SEM_INFORMACAO);
    expect(within(secao()).getByText(/não há informação de visto/i)).toBeVisible();
    expect(within(secao()).getByText(/consulado ou embaixada/)).toBeVisible();
  });

  it("nunca vira uma seção vazia: o título e o estado estão sempre presentes", () => {
    abrir(VISTO_SEM_INFORMACAO);
    expect(within(secao()).getByRole("heading", { level: 3, name: "Visto" })).toBeVisible();
    expect(secao().textContent?.trim().length).toBeGreaterThan("Visto".length);
  });
});

describe("SecaoVisto: herança do soberano", () => {
  it("diz que vale a entrada do soberano, com o nome dele", () => {
    abrir(VISTO_HERDADO);
    expect(within(secao()).getByText(/Vale a entrada do soberano: Reino Unido\./)).toBeVisible();
  });

  it("entrada própria não traz a nota", () => {
    abrir(criarVisto());
    expect(screen.queryByText(/Vale a entrada do soberano/)).not.toBeInTheDocument();
  });
});

describe("SecaoVisto: título de Kosovo e Malvinas", () => {
  it.each(["Kosovo", "Ilhas Malvinas"])(
    "com territorio_nome '%s' o título é 'Visto: %s'",
    (nome) => {
      abrir(criarVisto({ territorio_nome: nome }));
      expect(
        within(secao(`Visto: ${nome}`)).getByRole("heading", { level: 3, name: `Visto: ${nome}` }),
      ).toBeVisible();
    },
  );

  it("sem territorio_nome o título é só 'Visto'", () => {
    abrir(criarVisto());
    expect(screen.getByRole("heading", { level: 3, name: "Visto" })).toBeVisible();
    expect(screen.queryByText(/^Visto:/)).not.toBeInTheDocument();
  });
});

describe("SecaoVisto: fonte, data e aviso", () => {
  it("mostra o link do artigo com 'CC BY-SA' e a data do dado", () => {
    abrir(criarVisto({ dado_de: "2026-10-23T12:00:00Z" }));
    const link = within(secao()).getByRole("link", {
      name: "Wikipédia: Visa requirements for Brazilian citizens",
    });
    expect(link).toHaveAttribute(
      "href",
      "https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(link).toHaveAttribute("rel", expect.stringContaining("noreferrer"));
    expect(within(secao()).getByText(/CC BY-SA/)).toBeVisible();
    expect(within(secao()).getByText("23/10/2026")).toBeVisible();
  });

  it("a data é a do dado deste país, não a de outro", () => {
    abrir(criarVisto({ dado_de: "2026-09-01T12:00:00Z" }));
    expect(within(secao()).getByText("01/09/2026")).toBeVisible();
  });

  it("mostra o aviso de fonte não oficial com 'consulado ou embaixada'", () => {
    abrir(criarVisto());
    expect(within(secao()).getByText(/não oficial/i)).toBeVisible();
    expect(within(secao()).getByText(/consulado ou embaixada/)).toBeVisible();
  });

  it("endereço da fonte que não é web fica sem link", () => {
    abrir(
      criarVisto({
        fonte: { nome: "Fonte estranha", url: "javascript:alert(1)", licenca: "CC BY-SA" },
      }),
    );
    expect(within(secao()).getByText(/Fonte estranha/)).toBeVisible();
    expect(within(secao()).queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("SecaoVisto: dados antigos", () => {
  it("avisa que os dados podem estar desatualizados quando passam de 14 dias", () => {
    abrir(VISTO_DESATUALIZADO);
    expect(within(secao()).getByText(/podem estar desatualizados/i)).toBeVisible();
  });

  it("dado recente não traz o aviso", () => {
    abrir(criarVisto());
    expect(screen.queryByText(/desatualizados/i)).not.toBeInTheDocument();
  });

  it("o aviso de dados antigos convive com a mudança retida: continua mostrando o dado exibido", () => {
    abrir(criarVisto({ ...VISTO_DESATUALIZADO, situacao: "visto_exigido" }));
    expect(within(secao()).getByText("Visto exigido")).toBeVisible();
    expect(within(secao()).getByText(/podem estar desatualizados/i)).toBeVisible();
  });
});

describe("SecaoVisto: teclado", () => {
  // Enter e Espaço no <summary> abrem o <details> por comportamento nativo do navegador, que o jsdom
  // não emula; aqui se confere o que ele permite: o sumário recebe o foco do Tab, o link da fonte
  // vem depois dele, e o original só aparece depois de aberto.
  it("o sumário do original e o link da fonte entram na ordem do Tab, nesta ordem", async () => {
    const usuario = userEvent.setup();
    abrir(criarVisto({ observacoes: [OBSERVACAO_TRADUZIDA] }));
    const sumario = within(secao()).getByText("Ver o texto original");
    const original = within(secao()).getByText("Passport valid for 6 months required.");

    await usuario.tab();
    expect(sumario).toHaveFocus();
    expect(original).not.toBeVisible();
    await usuario.click(sumario);
    expect(original).toBeVisible();

    await usuario.tab();
    expect(
      within(secao()).getByRole("link", { name: /Visa requirements for Brazilian citizens/ }),
    ).toHaveFocus();
  });

  it("sem observações nem link, não há nada para o Tab parar na seção", async () => {
    abrir(
      criarVisto({
        fonte: { nome: "Fonte", url: "data:text/html,x", licenca: null },
      }),
    );
    await userEvent.setup().tab();
    expect(secao().contains(document.activeElement)).toBe(false);
  });
});

describe("SecaoVisto: 360 px de largura", () => {
  // O jsdom não calcula layout; o que dá para garantir é que nada na seção tem largura fixa, que o
  // texto longo quebra e que o alvo de toque do original tem a altura mínima de 44 px (min-h-11).
  const COMPRIDO = "https://exemplo.org/" + "muito-longo-".repeat(20);

  it("nenhum elemento da seção tem largura fixa em pixels", () => {
    abrir(criarVisto({ observacoes: [OBSERVACAO_TRADUZIDA] }));
    expect(secao().outerHTML).not.toMatch(/w-\[\d+px\]|width:\s*\d+px/);
  });

  it("textos longos da fonte quebram em vez de estourar a largura", () => {
    abrir(
      criarVisto({
        situacao: "outra_situacao",
        rotulo_original: COMPRIDO,
        permanencia: { tipo: "original", texto: COMPRIDO },
        observacoes: [{ texto_original: COMPRIDO, traducao: COMPRIDO }],
      }),
    );
    const longos = within(secao()).getAllByText(COMPRIDO);
    expect(longos.length).toBeGreaterThanOrEqual(4);
    for (const elemento of longos) expect(elemento.className).toContain("break-words");
  });

  it("o botão de abrir o original tem altura de toque de 44 px", () => {
    abrir(criarVisto({ observacoes: [OBSERVACAO_TRADUZIDA] }));
    const sumario = within(secao()).getByText("Ver o texto original").closest("summary");
    expect(sumario).toHaveClass("min-h-11");
  });
});
