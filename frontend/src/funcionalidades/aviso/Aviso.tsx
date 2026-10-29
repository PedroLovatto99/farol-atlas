export const URL_DO_PORTAL_CONSULAR = "https://www.gov.br/mre/pt-br/assuntos/portal-consular";

interface Props {
  /** Houve ao menos uma coleta completa (FR-002). */
  dadosObtidos: boolean;
  /** Fim da última coleta completa (FR-005). */
  atualizadoEm: string | null;
  /** A última coleta completa tem mais de 3 dias (FR-041), calculado no backend. */
  desatualizado: boolean;
  /** Ainda esperando a resposta do servidor: só o aviso de site não oficial aparece. */
  carregando?: boolean;
  /** Modo "Vistos" com a última coleta válida de vistos de mais de 14 dias (FR-029a), do backend. */
  vistosDesatualizados?: boolean;
}

const FORMATO_DA_DATA = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "long",
  timeZone: "America/Sao_Paulo",
});

/** Data da última atualização, aviso de site não oficial e avisos de dados antigos ou ausentes. */
export function Aviso({
  dadosObtidos,
  atualizadoEm,
  desatualizado,
  carregando = false,
  vistosDesatualizados = false,
}: Props) {
  return (
    <section
      aria-label="Avisos"
      className="rounded-lg border border-aviso-borda bg-aviso-fundo px-3 py-1.5 text-xs leading-snug text-aviso-texto sm:text-sm"
    >
      <p>
        Este site não é um serviço oficial. Confirme sempre no{" "}
        <a
          href={URL_DO_PORTAL_CONSULAR}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold underline"
        >
          Portal Consular do Itamaraty
        </a>
        .
      </p>
      {dadosObtidos && atualizadoEm !== null && (
        <p>Atualizado em {FORMATO_DA_DATA.format(new Date(atualizadoEm))}.</p>
      )}
      {desatualizado && (
        <p role="status" className="font-semibold">
          Dados desatualizados: a última atualização completa tem mais de 3 dias.
        </p>
      )}
      {vistosDesatualizados && (
        <p role="status" className="font-semibold">
          Dados de visto desatualizados: a última coleta válida tem mais de 14 dias.
        </p>
      )}
      {!dadosObtidos && !carregando && (
        <p role="status" className="font-semibold">
          Ainda não obtivemos os dados do Itamaraty. Todos os países aparecem como não verificado.
        </p>
      )}
    </section>
  );
}
