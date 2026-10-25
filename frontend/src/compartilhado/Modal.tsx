import { IconX } from "@tabler/icons-react";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

const FOCAVEIS =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface Props {
  aberto: boolean;
  titulo: string;
  onFechar(): void;
  children: ReactNode;
}

/**
 * Diálogo acessível, sem roteador: papel `dialog`, foco preso dentro dele, Esc e botão Fechar
 * fecham, e o foco volta ao elemento que o abriu. O conteúdo é sempre texto/elementos do React,
 * nunca HTML cru (princípio VIII).
 */
export function Modal({ aberto, titulo, onFechar, children }: Props) {
  const idDoTitulo = useId();
  const caixa = useRef<HTMLDivElement>(null);

  // Ao abrir: guarda quem tinha o foco e leva o foco para dentro. Ao fechar: devolve.
  useEffect(() => {
    if (!aberto) return;
    const quemAbriu = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    caixa.current?.querySelector<HTMLElement>(FOCAVEIS)?.focus();
    return () => quemAbriu?.focus();
  }, [aberto]);

  // Esc fecha; Tab e Shift+Tab giram dentro do diálogo
  useEffect(() => {
    if (!aberto) return;
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === "Escape") {
        evento.preventDefault();
        onFechar();
        return;
      }
      if (evento.key !== "Tab" || caixa.current === null) return;
      const itens = Array.from(caixa.current.querySelectorAll<HTMLElement>(FOCAVEIS));
      const primeiro = itens[0];
      const ultimo = itens[itens.length - 1];
      if (primeiro === undefined || ultimo === undefined) {
        evento.preventDefault();
        return;
      }
      const ativo = document.activeElement;
      const dentro = ativo instanceof Node && caixa.current.contains(ativo);
      if (evento.shiftKey && (ativo === primeiro || !dentro)) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && (ativo === ultimo || !dentro)) {
        evento.preventDefault();
        primeiro.focus();
      }
    }
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [aberto, onFechar]);

  if (!aberto) return null;

  return createPortal(
    <div
      data-testid="fundo-do-modal"
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4"
      onClick={(evento) => {
        if (evento.target === evento.currentTarget) onFechar();
      }}
    >
      <div
        ref={caixa}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idDoTitulo}
        className="max-h-[85dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl"
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <h2 id={idDoTitulo} className="text-lg font-semibold">
            {titulo}
          </h2>
          <button
            type="button"
            aria-label="Fechar"
            onClick={onFechar}
            className="-m-2 flex size-11 shrink-0 items-center justify-center rounded-lg text-texto-2 hover:bg-linha"
          >
            <IconX aria-hidden size={22} />
          </button>
        </div>
        <div className="space-y-3 text-sm leading-relaxed">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
