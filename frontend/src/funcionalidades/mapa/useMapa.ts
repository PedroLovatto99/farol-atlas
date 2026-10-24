import { useCallback, useEffect, useState } from "react";
import { ErroDeApi, type ClienteDaApi, type Mapa } from "../../servicos/api/cliente";

export type EstadoDoMapa =
  | { situacao: "carregando" }
  | { situacao: "erro"; mensagem: string }
  | { situacao: "pronto"; mapa: Mapa };

const MENSAGEM_PADRAO = "Não foi possível carregar os dados do mapa.";

function mensagemDe(erro: unknown): string {
  return erro instanceof ErroDeApi ? erro.message : MENSAGEM_PADRAO;
}

/**
 * Busca `/mapa` uma vez (tudo o que o mapa precisa vem numa chamada só; nenhuma requisição por
 * país no carregamento). `tentarDeNovo` repete a busca depois de um erro.
 */
export function useMapa(cliente: ClienteDaApi): {
  estado: EstadoDoMapa;
  tentarDeNovo: () => void;
} {
  const [tentativa, setTentativa] = useState(0);
  const [resultado, setResultado] = useState<{
    tentativa: number;
    estado: Exclude<EstadoDoMapa, { situacao: "carregando" }>;
  } | null>(null);

  useEffect(() => {
    const controle = new AbortController();
    cliente
      .obterMapa(controle.signal)
      .then((mapa) => setResultado({ tentativa, estado: { situacao: "pronto", mapa } }))
      .catch((erro: unknown) => {
        if (controle.signal.aborted) return;
        setResultado({ tentativa, estado: { situacao: "erro", mensagem: mensagemDe(erro) } });
      });
    return () => controle.abort();
  }, [cliente, tentativa]);

  const tentarDeNovo = useCallback(() => setTentativa((n) => n + 1), []);
  const estado: EstadoDoMapa =
    resultado?.tentativa === tentativa ? resultado.estado : { situacao: "carregando" };
  return { estado, tentarDeNovo };
}
