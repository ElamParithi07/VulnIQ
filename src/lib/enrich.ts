import {
  Vulnerability,
  EnrichedVulnerability,
} from "../types/vulnerability";

import { calculatePriorityScore } from "./score";

export function enrichVulnerabilities(
  vulnerabilities: Vulnerability[],
  kevSet: Set<string>,
  epssMap: Map<string, number>
): EnrichedVulnerability[] {
  return vulnerabilities.map((v) => {
    const epss = epssMap.get(v.id) ?? 0;

    const isKEV = kevSet.has(v.id);

    const priorityScore = calculatePriorityScore(
      v.cvss,
      epss,
      isKEV
    );

    return {
      ...v,

      epss,

      isKEV,

      priorityScore,
    };
  });
}