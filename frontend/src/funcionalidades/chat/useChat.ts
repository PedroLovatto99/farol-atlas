import { useCallback, useRef, useState } from "react";
import { ErroDeApi, type ClienteDaApi, type TrechoDoChat } from "../../servicos/api/cliente";

const MENSAGEM_DE_FALHA = "Não foi possível responder agora. Tente de novo em instantes.";

export interface MensagemDoChat {
  id: number;
  autor: "pessoa" | "chat";
  paragrafos: readonly (readonly TrechoDoChat[])[];
}

function emParagrafo(texto: string): MensagemDoChat["paragrafos"] {
  return [[{ texto, url: null }]];
}

/**
 * A conversa fica só aqui: some ao recarregar a página e nunca passa pelo estado do mapa (FR-019,
 * FR-020). Cada pergunta vai sozinha para a API, sem as anteriores.
 */
export function useChat(cliente: ClienteDaApi) {
  const [mensagens, setMensagens] = useState<readonly MensagemDoChat[]>([]);
  const [respondendo, setRespondendo] = useState(false);
  // `respondendo` só muda no próximo render: dois envios seguidos passariam por ele
  const ocupado = useRef(false);
  const proximoId = useRef(0);

  const enviar = useCallback(
    (texto: string) => {
      const pergunta = texto.trim();
      if (pergunta === "" || ocupado.current) return;
      function acrescentar(
        autor: MensagemDoChat["autor"],
        paragrafos: MensagemDoChat["paragrafos"],
      ) {
        const id = proximoId.current++;
        setMensagens((atuais) => [...atuais, { id, autor, paragrafos }]);
      }

      ocupado.current = true;
      setRespondendo(true);
      acrescentar("pessoa", emParagrafo(pergunta));
      cliente
        .perguntarAoChat(pergunta)
        .then((resposta) => acrescentar("chat", resposta.paragrafos))
        .catch((erro: unknown) => {
          const limite = erro instanceof ErroDeApi && erro.status === 429;
          acrescentar("chat", emParagrafo(limite ? erro.message : MENSAGEM_DE_FALHA));
        })
        .finally(() => {
          ocupado.current = false;
          setRespondendo(false);
        });
    },
    [cliente],
  );

  return { mensagens, respondendo, enviar };
}
