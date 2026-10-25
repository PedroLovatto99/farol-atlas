import { useCallback, useEffect, useState } from "react";
import { ErroDeApi, type ClienteDaApi, type Pais } from "../../servicos/api/cliente";

export type EstadoDoPais =
  | { situacao: "ocioso" }
  | { situacao: "carregando" }
  | { situacao: "erro"; mensagem: string }
  | { situacao: "pronto"; pais: Pais };

type Resultado = Exclude<EstadoDoPais, { situacao: "ocioso" } | { situacao: "carregando" }>;

const MENSAGEM_PADRAO = "Não foi possível carregar os dados do país.";

function mensagemDe(erro: unknown): string {
  return erro instanceof ErroDeApi ? erro.message : MENSAGEM_PADRAO;
}

/**
 * Busca `/paises/{codigo}` quando alguém seleciona um território: uma chamada por seleção, com
 * cancelamento da anterior ao trocar de país. Sem seleção, não chama nada. `tentarDeNovo` repete
 * a busca depois de um erro.
 */
export function usePais(
  cliente: ClienteDaApi,
  codigo: string | null,
): { estado: EstadoDoPais; tentarDeNovo: () => void } {
  const [tentativa, setTentativa] = useState(0);
  const [resultado, setResultado] = useState<{
    codigo: string;
    tentativa: number;
    estado: Resultado;
  } | null>(null);

  useEffect(() => {
    if (codigo === null) return;
    const controle = new AbortController();
    const pedido = codigo;
    // Resposta de uma chamada já cancelada (o país mudou) nunca entra
    function guardar(estado: Resultado) {
      if (!controle.signal.aborted) setResultado({ codigo: pedido, tentativa, estado });
    }
    cliente
      .obterPais(codigo, controle.signal)
      .then((pais) => guardar({ situacao: "pronto", pais }))
      .catch((erro: unknown) => guardar({ situacao: "erro", mensagem: mensagemDe(erro) }));
    return () => controle.abort();
  }, [cliente, codigo, tentativa]);

  const tentarDeNovo = useCallback(() => setTentativa((n) => n + 1), []);

  let estado: EstadoDoPais;
  if (codigo === null) {
    estado = { situacao: "ocioso" };
  } else if (resultado?.codigo === codigo && resultado.tentativa === tentativa) {
    estado = resultado.estado;
  } else {
    estado = { situacao: "carregando" };
  }
  return { estado, tentarDeNovo };
}
