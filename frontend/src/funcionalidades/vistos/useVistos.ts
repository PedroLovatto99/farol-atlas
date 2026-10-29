import { useCallback, useEffect, useRef } from "react";
import { useEstado } from "../../estado/contexto";
import type { EstadoDosVistos } from "../../estado/reducer";
import { ErroDeApi, type ClienteDaApi } from "../../servicos/api/cliente";
import type { ModoDoGlobo } from "../mapa/tipos";

const MENSAGEM_PADRAO = "Não foi possível carregar os vistos.";

function mensagemDe(erro: unknown): string {
  return erro instanceof ErroDeApi ? erro.message : MENSAGEM_PADRAO;
}

/**
 * Busca `GET /vistos` sob demanda: só quando a pessoa escolhe o modo "Vistos", e uma vez; a resposta
 * fica no estado da aplicação. Nem o carregamento do site nem o modo "Alertas" a pedem. Depois de
 * um erro, escolher o modo de novo não repete a chamada: quem repete é `tentarDeNovo`. Sai de
 * cena cancelando a busca.
 */
export function useVistos(
  cliente: ClienteDaApi,
  modo: ModoDoGlobo,
): { estado: EstadoDosVistos; tentarDeNovo: () => void } {
  const { estado, despachar } = useEstado();
  // A busca em andamento: só é cancelada quando outra começa ("Tentar de novo") ou quando o
  // componente sai de cena, e não quando o próprio estado passa de "nao_pedido" a "carregando".
  const emAndamento = useRef<AbortController | null>(null);

  const buscar = useCallback(() => {
    emAndamento.current?.abort();
    const controle = new AbortController();
    emAndamento.current = controle;
    despachar({ tipo: "vistos-carregando" });
    cliente
      .obterVistos(controle.signal)
      .then((dados) => {
        if (!controle.signal.aborted) despachar({ tipo: "vistos-carregados", dados });
      })
      .catch((erro: unknown) => {
        if (!controle.signal.aborted) {
          despachar({ tipo: "vistos-falhou", mensagem: mensagemDe(erro) });
        }
      });
  }, [cliente, despachar]);

  const primeiraBusca = modo === "vistos" && estado.vistos.situacao === "nao_pedido";
  useEffect(() => {
    if (primeiraBusca) buscar();
  }, [primeiraBusca, buscar]);

  useEffect(() => {
    const busca = emAndamento;
    return () => busca.current?.abort();
  }, []);

  return { estado: estado.vistos, tentarDeNovo: buscar };
}
