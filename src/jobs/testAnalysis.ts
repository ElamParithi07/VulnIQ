import { getAllVulnerabilities } from "../services/database/vulnerability";
import { analyzeVulnerability } from "../services/ai/analysis";

async function main() {
  const vulnerabilities = await getAllVulnerabilities();

  const result = await analyzeVulnerability(vulnerabilities[0]);

  console.log(result);
}

main().catch(console.error);