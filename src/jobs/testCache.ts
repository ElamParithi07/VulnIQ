import { analyzeIfNeeded } from "../services/intelligence/analyze";

async function main() {
  const result = await analyzeIfNeeded(
    "CVE-2018-7192"
  );

  console.log(result);
}

main().catch(console.error);