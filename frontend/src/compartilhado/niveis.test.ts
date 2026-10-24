import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { NIVEIS, NIVEL_PADRAO, ORDEM_DA_LEGENDA, nivelMaisGrave, type NivelId } from "./niveis";

const tema = readFileSync(resolve(process.cwd(), "src/compartilhado/tema.css"), "utf-8");

const TODOS: NivelId[] = ["sem_alerta", "evitar", "nao_viajar", "nao_verificado"];

describe("níveis de alerta", () => {
  it("todo nível tem rótulo e texto explicativo", () => {
    for (const id of TODOS) {
      expect(NIVEIS[id].rotulo.length).toBeGreaterThan(0);
      expect(NIVEIS[id].texto.length).toBeGreaterThan(0);
    }
  });

  it("os rótulos são os da especificação", () => {
    expect(NIVEIS.sem_alerta.rotulo).toBe("Sem alerta do Itamaraty");
    expect(NIVEIS.evitar.rotulo).toBe("Evite viagens não essenciais");
    expect(NIVEIS.nao_viajar.rotulo).toBe("Não viaje");
    expect(NIVEIS.nao_verificado.rotulo).toBe("Não verificado");
  });

  it("o padrão, quando não há dado confirmado, é não verificado", () => {
    expect(NIVEL_PADRAO).toBe("nao_verificado");
  });

  it("ausência de alerta não é apresentada como recomendação de viagem", () => {
    expect(NIVEIS.sem_alerta.texto).toMatch(/não significa que o governo recomenda a viagem/i);
  });

  it("a gravidade cresce de sem alerta para não viaje, e não verificado fica abaixo de todos", () => {
    expect(NIVEIS.nao_verificado.gravidade).toBeLessThan(NIVEIS.sem_alerta.gravidade);
    expect(NIVEIS.sem_alerta.gravidade).toBeLessThan(NIVEIS.evitar.gravidade);
    expect(NIVEIS.evitar.gravidade).toBeLessThan(NIVEIS.nao_viajar.gravidade);
  });

  it("nivelMaisGrave escolhe o mais grave", () => {
    expect(nivelMaisGrave(["sem_alerta", "nao_viajar", "evitar"])).toBe("nao_viajar");
    expect(nivelMaisGrave([])).toBe("nao_verificado");
  });

  it("a legenda lista os quatro níveis, cada um uma vez", () => {
    expect([...ORDEM_DA_LEGENDA].sort()).toEqual([...TODOS].sort());
  });

  it("as cores do código são as mesmas dos tokens do tema (tema.css)", () => {
    const tokens: Record<NivelId, string> = {
      sem_alerta: "--color-nivel-sem-alerta",
      evitar: "--color-nivel-evitar",
      nao_viajar: "--color-nivel-nao-viajar",
      nao_verificado: "--color-nivel-nao-verificado",
    };
    for (const id of TODOS) {
      const encontrado = new RegExp(`${tokens[id]}:\\s*(#[0-9a-fA-F]{6})`).exec(tema);
      expect(encontrado, `token ${tokens[id]} em tema.css`).not.toBeNull();
      expect(encontrado?.[1]?.toLowerCase()).toBe(NIVEIS[id].cor.toLowerCase());
    }
  });
});
