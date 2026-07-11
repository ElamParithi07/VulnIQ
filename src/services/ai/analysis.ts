import { ai } from "./client";
import { DatabaseVulnerability } from "../../types/vulnerability";
import { Intelligence } from "../../types/intelligence";

export async function analyzeVulnerability(
  vulnerability: DatabaseVulnerability
): Promise<Intelligence> {
  const prompt = `
You are a senior Cyber Threat Intelligence Analyst.

Analyze the following vulnerability.

Return ONLY valid JSON.

{
  "title": "...",
  "summary": "...",
  "businessImpact": "...",
  "priorityReason": "...",
  "remediation": "..."
}

Rules:

- No markdown.
- No code fences.
- No explanations.
- Do not mention the CVE ID.
- title <= 10 words.
- summary <= 2 sentences.
- businessImpact <= 2 sentences.
- priorityReason <= 1 sentence.
- remediation should be short and actionable.

Vulnerability:

Vendor: ${vulnerability.vendor}

Product: ${vulnerability.product}

CVSS: ${vulnerability.cvss_score}

EPSS: ${vulnerability.epss_score}

Actively Exploited: ${vulnerability.is_cisa_kev}

Description:

${vulnerability.description}
`;

  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash",

    contents: prompt,

    config: {
      responseMimeType: "application/json",
    },
  });

  return JSON.parse(response.text ?? "{}");
}