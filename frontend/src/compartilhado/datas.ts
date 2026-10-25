/** Datas no formato brasileiro (dd/mm/aaaa), sempre no fuso de Brasília. */

const FORMATO_DA_DATA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: "America/Sao_Paulo",
});

const SO_DATA = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * "2026-08-17T15:00:00Z" vira "17/08/2026". Uma data sem hora ("2026-10-21") não passa por fuso,
 * para o dia não andar. Se o texto não for uma data, volta como veio.
 */
export function formatarData(valor: string): string {
  const soData = SO_DATA.exec(valor);
  if (soData !== null) {
    const [, ano, mes, dia] = soData;
    return `${dia}/${mes}/${ano}`;
  }
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? valor : FORMATO_DA_DATA.format(data);
}
