import { generateSummary } from "../services/ai/summary";

async function main() {

    const summary = await generateSummary(`
A vulnerability in Apache HTTP Server allows remote attackers
to execute arbitrary code due to improper input validation.
`);

    console.log(summary);

}

main();