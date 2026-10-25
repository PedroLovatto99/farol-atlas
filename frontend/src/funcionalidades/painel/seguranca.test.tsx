import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Pais } from "../../servicos/api/cliente";
import { ALERTA_EXEMPLO, criarPais, criarPosto } from "../../testes/dados-exemplo";
import { Painel } from "./Painel";

afterEach(cleanup);

/**
 * Princípio VIII: textos vindos de fora (alertas do gov.br, endereços coletados, respostas do
 * classificador) são dados. Aparecem como texto e nunca viram elementos da página.
 */
const SCRIPT = "<script>window.invadido = true</script>";
const IMAGEM = '<img src="x" onerror="window.invadido = true">';
const NEGRITO = "<b>negrito</b> & <i>itálico</i>";
const MARCACAO = `${SCRIPT}${IMAGEM}${NEGRITO}`;

/** Elementos que só existiriam se algum texto externo tivesse sido inserido como HTML. */
const ELEMENTOS_DE_INJECAO = "script, img, b, i, iframe, svg[onload], [onerror], [onclick]";

function abrir(pais: Pais) {
  return render(
    <Painel estado={{ situacao: "pronto", pais }} onFechar={vi.fn()} onTentarDeNovo={vi.fn()} />,
  );
}

function semInjecao(container: HTMLElement) {
  expect(container.querySelector(ELEMENTOS_DE_INJECAO)).toBeNull();
  expect(Reflect.get(window, "invadido")).toBeUndefined();
}

describe("Painel: texto externo nunca vira HTML", () => {
  it("título do alerta com marcação aparece como texto", () => {
    const { container } = abrir(criarPais({ alertas: [{ ...ALERTA_EXEMPLO, titulo: MARCACAO }] }));
    expect(screen.getByRole("link", { name: MARCACAO })).toBeVisible();
    semInjecao(container);
  });

  it("título com marcação continua texto quando o endereço do alerta não é web", () => {
    const { container } = abrir(
      criarPais({
        alertas: [{ ...ALERTA_EXEMPLO, titulo: MARCACAO, url: "javascript:alert(1)" }],
      }),
    );
    expect(screen.getByText(MARCACAO)).toBeVisible();
    expect(screen.queryByRole("link", { name: MARCACAO })).toBeNull(); // sem link para javascript:
    semInjecao(container);
  });

  it("observação, nome do país e nome da região com marcação aparecem como texto", () => {
    const { container } = abrir(
      criarPais({
        nome: `Ilha ${NEGRITO}`,
        observacao: MARCACAO,
        regioes: [{ nome: `Norte ${NEGRITO}`, nivel: "nao_viajar" }],
      }),
    );
    expect(screen.getByRole("heading", { level: 2, name: `Ilha ${NEGRITO}` })).toBeVisible();
    expect(screen.getByText(MARCACAO)).toBeVisible();
    expect(screen.getByText(`Norte ${NEGRITO}:`)).toBeVisible();
    semInjecao(container);
  });

  it("endereço, telefone e cidade de um posto com marcação aparecem como texto", async () => {
    const { container } = abrir(
      criarPais({
        postos: [
          criarPosto({
            cidade: `Lima ${NEGRITO}`,
            endereco: MARCACAO,
            telefone_plantao: `+51 ${SCRIPT}`,
            contato_coletado_em: "2026-10-20T12:00:00Z",
            contato_fonte_url: "https://www.gov.br/mre/pt-br/embaixada-lima",
          }),
        ],
      }),
    );
    await userEvent.click(screen.getByText(`Lima ${NEGRITO}`));
    expect(screen.getByText(MARCACAO, { exact: false })).toBeVisible();
    expect(screen.getByText(`+51 ${SCRIPT}`)).toBeVisible();
    semInjecao(container);
  });

  it("fonte do contato que não é web fica sem link", async () => {
    abrir(
      criarPais({
        postos: [
          criarPosto({
            endereco: "Rua A, 1",
            contato_coletado_em: "2026-10-20T12:00:00Z",
            contato_fonte_url: "javascript:alert(1)",
          }),
        ],
      }),
    );
    await userEvent.click(screen.getByText(/Embaixada|Consulado/));
    const posto = screen.getByText("Rua A, 1").closest("details");
    expect(posto).not.toBeNull();
    expect(within(posto as HTMLElement).queryByRole("link", { name: "Fonte" })).toBeNull();
    expect(within(posto as HTMLElement).getByText(/Coletado em/)).toBeVisible();
  });

  it("nenhum link de texto externo fica sem rel noopener noreferrer", () => {
    abrir(criarPais({ alertas: [{ ...ALERTA_EXEMPLO, titulo: MARCACAO }] }));
    const link = screen.getByRole("link", { name: MARCACAO });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.getAttribute("rel")).toContain("noreferrer");
  });
});
