import { DatabaseVulnerability } from "../types/vulnerability";
import { normalizeTechnology } from "./normalization/technology";

export function matchVulnerabilities(
  vulnerabilities: DatabaseVulnerability[],
  techTags: string[],
  limit = 10
): DatabaseVulnerability[] {

  const normalizedTags = techTags.map(normalizeTechnology);

  const matches = vulnerabilities.filter((vulnerability) => {

    const vendor = normalizeTechnology(vulnerability.vendor);

    const product = normalizeTechnology(vulnerability.product);

    return normalizedTags.some((tag) =>
      vendor.includes(tag) || product.includes(tag)
    );

  });

  return matches.slice(0, limit);
}