import {
  createContext,
  useContext,
  useMemo,
  useReducer,
  type ActionDispatch,
  type ReactNode,
} from "react";
import { ESTADO_INICIAL, reducer, type Acao, type Estado } from "./reducer";

interface ValorDoContexto {
  estado: Estado;
  despachar: ActionDispatch<[acao: Acao]>;
}

const Contexto = createContext<ValorDoContexto | null>(null);

export function ProvedorDeEstado({
  children,
  inicial = ESTADO_INICIAL,
}: {
  children: ReactNode;
  inicial?: Estado;
}) {
  const [estado, despachar] = useReducer(reducer, inicial);
  const valor = useMemo(() => ({ estado, despachar }), [estado, despachar]);
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useEstado(): ValorDoContexto {
  const valor = useContext(Contexto);
  if (valor === null) {
    throw new Error("useEstado precisa estar dentro de <ProvedorDeEstado>");
  }
  return valor;
}
