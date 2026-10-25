import { useId, useMemo, useState, type KeyboardEvent } from "react";
import type { TerritorioNoMapa } from "../../servicos/api/cliente";
import { buscarTerritorios } from "./buscarTerritorios";

interface Props {
  territorios: readonly TerritorioNoMapa[];
  /** Quem chama abre o painel e leva o mapa até o território, como no toque. */
  onEscolher(codigo: string): void;
}

/**
 * Campo de busca com sugestões (padrão combobox com lista). As sugestões vêm de `buscarTerritorios`
 * e o texto digitado só vira texto na tela, nunca HTML. Sem resultado, mostra a mensagem e não
 * escolhe nada (FR-022).
 */
export function Busca({ territorios, onEscolher }: Props) {
  const idBase = useId();
  const [texto, setTexto] = useState("");
  const [ativa, setAtiva] = useState(-1);
  const [fechada, setFechada] = useState(false);

  const sugestoes = useMemo(() => buscarTerritorios(territorios, texto), [territorios, texto]);
  const digitou = texto.trim() !== "";
  const aberta = digitou && !fechada && sugestoes.length > 0;
  // A mensagem só aparece com o mapa carregado: antes disso não há onde procurar
  const semResultado = digitou && territorios.length > 0 && sugestoes.length === 0;
  const idDaOpcao = (indice: number) => `${idBase}-opcao-${indice}`;

  function escolher(codigo: string) {
    setTexto("");
    setAtiva(-1);
    setFechada(false);
    onEscolher(codigo);
  }

  function aoTeclar(evento: KeyboardEvent<HTMLInputElement>) {
    switch (evento.key) {
      case "ArrowDown":
        if (sugestoes.length === 0) return;
        evento.preventDefault();
        setFechada(false);
        setAtiva((a) => (a + 1) % sugestoes.length);
        break;
      case "ArrowUp":
        if (sugestoes.length === 0) return;
        evento.preventDefault();
        setFechada(false);
        setAtiva((a) => (a <= 0 ? sugestoes.length - 1 : a - 1));
        break;
      case "Enter": {
        const escolhida = sugestoes[ativa] ?? sugestoes[0];
        if (!aberta || escolhida === undefined) return;
        evento.preventDefault();
        escolher(escolhida.codigo);
        break;
      }
      case "Escape":
        if (!aberta) return;
        // fecha só a lista; o Esc não chega ao fechamento do painel
        evento.stopPropagation();
        setFechada(true);
        setAtiva(-1);
        break;
    }
  }

  return (
    <div className="relative w-full max-w-xs">
      <input
        type="search"
        role="combobox"
        aria-label="Buscar país"
        aria-expanded={aberta}
        aria-controls={`${idBase}-lista`}
        aria-autocomplete="list"
        aria-activedescendant={aberta && ativa >= 0 ? idDaOpcao(ativa) : undefined}
        autoComplete="off"
        placeholder="Buscar país"
        value={texto}
        onChange={(evento) => {
          setTexto(evento.target.value);
          setAtiva(-1);
          setFechada(false);
        }}
        onKeyDown={aoTeclar}
        className="min-h-11 w-full rounded-xl border border-linha bg-white px-3 text-sm shadow-sm"
      />
      {aberta && (
        <ul
          id={`${idBase}-lista`}
          role="listbox"
          aria-label="Sugestões de países"
          className="absolute inset-x-0 top-full z-20 mt-1 max-h-72 overflow-auto rounded-xl border border-linha bg-white py-1 text-sm shadow"
        >
          {sugestoes.map((s, indice) => (
            <li
              key={s.codigo}
              id={idDaOpcao(indice)}
              role="option"
              aria-selected={indice === ativa}
              // mouseDown (e não click) para escolher antes de o campo perder o foco
              onMouseDown={(evento) => evento.preventDefault()}
              onClick={() => escolher(s.codigo)}
              className={`flex min-h-11 cursor-pointer items-center px-3 ${
                indice === ativa ? "bg-espaco" : ""
              }`}
            >
              {s.rotulo}
            </li>
          ))}
        </ul>
      )}
      {semResultado && (
        <p role="status" className="mt-1 rounded-lg bg-white px-3 py-2 text-sm shadow">
          Nenhum país encontrado para “{texto.trim()}”.
        </p>
      )}
    </div>
  );
}
