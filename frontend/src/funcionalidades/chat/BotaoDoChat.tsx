import { IconMessageCircle, IconX } from "@tabler/icons-react";
import { useCallback, useRef, useState } from "react";
import type { ClienteDaApi } from "../../servicos/api/cliente";
import { CaixaDoChat } from "./CaixaDoChat";
import { useChat } from "./useChat";

/** Botão flutuante que abre e fecha a caixa; a conversa continua aqui enquanto a caixa está fechada. */
export function BotaoDoChat({ cliente }: { cliente: ClienteDaApi }) {
  const [aberto, setAberto] = useState(false);
  const { mensagens, respondendo, enviar } = useChat(cliente);
  const botao = useRef<HTMLButtonElement>(null);

  const fechar = useCallback(() => {
    setAberto(false);
    botao.current?.focus();
  }, []);

  return (
    <div
      className="chat-flutuante absolute z-30 flex flex-col items-end gap-2"
      data-aberto={aberto}
    >
      {aberto && (
        <CaixaDoChat
          mensagens={mensagens}
          respondendo={respondendo}
          onEnviar={enviar}
          onFechar={fechar}
        />
      )}
      <button
        ref={botao}
        type="button"
        aria-label={aberto ? "Fechar chat" : "Abrir chat"}
        aria-expanded={aberto}
        onClick={aberto ? fechar : () => setAberto(true)}
        className="flex size-12 items-center justify-center rounded-full border-2 border-white bg-marinho text-white shadow-lg"
      >
        {aberto ? <IconX aria-hidden="true" /> : <IconMessageCircle aria-hidden="true" />}
      </button>
    </div>
  );
}
