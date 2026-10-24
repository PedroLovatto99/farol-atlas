// Gera os tipos TypeScript da API a partir do OpenAPI (constituição, princípio III).
//
//   npm run gerar-tipos                       usa o contrato em specs/.../contracts/openapi.yaml
//   npm run gerar-tipos -- caminho/openapi.json   usa outro arquivo (ex.: o exportado pelo backend)
//
// Para usar o OpenAPI real do backend:
//   (cd ../backend && uv run poe exportar-openapi ../frontend/openapi.json)
//   npm run gerar-tipos -- openapi.json
import { execFileSync } from "node:child_process";

const contrato = "../specs/001-mapa-alertas-viagem/contracts/openapi.yaml";
const entrada = process.argv[2] ?? contrato;
const saida = "src/servicos/api/esquema.d.ts";

// Roda o CLI com o próprio Node, sem shell (funciona igual no Windows e no Linux)
execFileSync(
  process.execPath,
  ["node_modules/openapi-typescript/bin/cli.js", entrada, "-o", saida],
  {
    stdio: "inherit",
  },
);
console.log(`Tipos gerados em ${saida} a partir de ${entrada}`);
