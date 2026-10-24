/** `matchMedia` controlável para os testes (o jsdom não implementa). */
import { vi } from "vitest";

type Ouvinte = (evento: MediaQueryListEvent) => void;

export interface MediaSimulada {
  /** Muda o resultado da consulta e avisa quem está ouvindo. */
  definir(consulta: string, valor: boolean): void;
  restaurar(): void;
}

export function simularMatchMedia(inicial: Readonly<Record<string, boolean>> = {}): MediaSimulada {
  const valores = new Map<string, boolean>(Object.entries(inicial));
  const ouvintes = new Map<string, Set<Ouvinte>>();
  const original = window.matchMedia;

  window.matchMedia = vi.fn((consulta: string): MediaQueryList => {
    const lista: Partial<MediaQueryList> = {
      media: consulta,
      get matches() {
        return valores.get(consulta) ?? false;
      },
      addEventListener: (_tipo: string, ouvinte: unknown) => {
        const conjunto = ouvintes.get(consulta) ?? new Set<Ouvinte>();
        conjunto.add(ouvinte as Ouvinte);
        ouvintes.set(consulta, conjunto);
      },
      removeEventListener: (_tipo: string, ouvinte: unknown) => {
        ouvintes.get(consulta)?.delete(ouvinte as Ouvinte);
      },
    };
    return lista as MediaQueryList;
  });

  return {
    definir(consulta, valor) {
      valores.set(consulta, valor);
      for (const ouvinte of ouvintes.get(consulta) ?? []) {
        ouvinte({ matches: valor, media: consulta } as MediaQueryListEvent);
      }
    },
    restaurar() {
      window.matchMedia = original;
    },
  };
}
