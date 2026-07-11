import { ai } from "./client";

export async function generateSummary(
  description: string
): Promise<string> {
  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash",

    contents: `
You are a senior Cyber Threat Intelligence analyst.

Summarize the following vulnerability.

Rules:

- Maximum 2 sentences.
- Explain the operational risk.
- Explain the business impact.
- Avoid CVE IDs.
- Use professional language.

Description:

${description}
`,
  });

  return response.text ?? "";
}