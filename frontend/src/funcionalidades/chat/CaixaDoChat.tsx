import { useEffect, useRef, useState, type FormEvent } from "react";
import { URL_DO_PORTAL_CONSULAR } from "../aviso/Aviso";
import { Mensagem } from "./Mensagem";
import type { MensagemDoChat } from "./useChat";

const TAMANHO_MAXIMO = 300;

interface Props {
  mensagens: readonly MensagemDoChat[];
  respondendo: boolean;
  onEnviar(pergunta: string): void;
  onFechar(): void;
}

/**
 * A caixa do chat: diálogo não modal, porque o mapa, a legenda e o painel continuam usáveis com ela
 * aberta (FR-022). Ser `dialog` também faz o Esc ser dela, e não do fechamento do painel.
 */
export function CaixaDoChat({ mensagens, respondendo, onEnviar, onFechar }: Props) {
  const [texto, setTexto] = useState("");
  const campo = useRef<HTMLInputElement>(null);
  const lista = useRef<HTMLOListElement>(null);

  useEffect(() => {
    campo.current?.focus();
  }, []);

  // Conforme o navegador, o campo desabilitado solta o foco no body; quem foi para outro lugar fica lá
  useEffect(() => {
    if (!respondendo && document.activeElement === document.body) campo.current?.focus();
  }, [respondendo]);

  // A última mensagem aparece a partir do começo: a frase direta vem primeiro (FR-003)
  useEffect(() => {
    const caixa = lista.current;
    if (caixa?.lastElementChild instanceof HTMLElement) {
      caixa.scrollTop = caixa.lastElementChild.offsetTop;
    }
  }, [mensagens]);

  useEffect(() => {
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key !== "Escape" || evento.defaultPrevented) return;
      if (document.querySelector('[aria-modal="true"]') !== null) return;
      // O App não pode tratar este Esc: a caixa some antes de ele olhar se há um diálogo
      evento.preventDefault();
      onFechar();
    }
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [onFechar]);

  function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    if (texto.trim() === "") return;
    onEnviar(texto);
    setTexto("");
  }

  return (
    <div
      role="dialog"
      aria-label="Chat"
      className="chat-caixa flex flex-col overflow-hidden rounded-2xl border border-linha bg-white shadow-lg"
    >
      <p className="border-b border-aviso-borda bg-aviso-fundo px-3 py-2 text-xs leading-snug text-aviso-texto">
        As respostas são montadas automaticamente a partir dos dados do site e devem ser conferidas
        no{" "}
        <a
          href={URL_DO_PORTAL_CONSULAR}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold underline"
        >
          Portal Consular
        </a>
      </p>

      <div aria-live="polite" className="flex min-h-0 flex-1 flex-col">
        <ol ref={lista} className="relative min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
          {mensagens.map((mensagem) => (
            <Mensagem key={mensagem.id} mensagem={mensagem} />
          ))}
        </ol>
        {respondendo && <p className="px-3 pb-2 text-sm text-texto-2">Respondendo…</p>}
      </div>

      <form onSubmit={aoEnviar} className="space-y-1 border-t border-linha p-2">
        <div className="flex items-baseline justify-between px-1 text-xs text-texto-2">
          <label htmlFor="pergunta-do-chat">Sua pergunta</label>
          <span>
            {texto.length}/{TAMANHO_MAXIMO}
          </span>
        </div>
        <div className="flex gap-2">
          <input
            ref={campo}
            id="pergunta-do-chat"
            type="text"
            autoComplete="off"
            maxLength={TAMANHO_MAXIMO}
            value={texto}
            onChange={(evento) => setTexto(evento.target.value)}
            disabled={respondendo}
            className="min-h-11 w-full min-w-0 rounded-lg border border-texto-2 px-3 text-base disabled:bg-espaco"
          />
          <button
            type="submit"
            disabled={respondendo}
            className="min-h-11 shrink-0 rounded-lg bg-marinho px-4 text-sm font-semibold text-white disabled:opacity-60"
          >
            Enviar
          </button>
        </div>
      </form>
    </div>
  );
}
