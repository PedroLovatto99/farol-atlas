import { ehUrlWeb } from "../../compartilhado/urlSegura";
import type { TrechoDoChat } from "../../servicos/api/cliente";
import type { MensagemDoChat } from "./useChat";

const ESTILO_DO_AUTOR: Record<MensagemDoChat["autor"], string> = {
  pessoa: "ml-8 bg-marinho text-white",
  chat: "mr-4 bg-espaco text-texto",
};

function Trecho({ trecho }: { trecho: TrechoDoChat }) {
  // O texto vem como texto do React (nunca HTML) e a url é dado externo: só vira link se for web
  if (trecho.url === null || !ehUrlWeb(trecho.url)) return <span>{trecho.texto}</span>;
  return (
    <a
      href={trecho.url}
      target="_blank"
      rel="noopener noreferrer"
      className="font-semibold text-marinho underline"
    >
      {trecho.texto}
    </a>
  );
}

export function Mensagem({ mensagem }: { mensagem: MensagemDoChat }) {
  return (
    <li
      className={`space-y-2 rounded-lg px-3 py-2 text-sm wrap-anywhere ${ESTILO_DO_AUTOR[mensagem.autor]}`}
    >
      <span className="sr-only">{mensagem.autor === "pessoa" ? "Você:" : "Chat:"}</span>
      {mensagem.paragrafos.map((trechos, indice) => (
        <p key={indice}>
          {trechos.map((trecho, posicao) => (
            <Trecho key={posicao} trecho={trecho} />
          ))}
        </p>
      ))}
    </li>
  );
}
