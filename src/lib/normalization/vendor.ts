import { normalizeTechnology } from "./technology";
export function extractVendorAndProduct(configurations: any) {
  if (!configurations) {
    return {
      vendor: "Unknown",
      product: "Unknown",
    };
  }

  for (const config of configurations) {
    for (const node of config.nodes || []) {
      for (const match of node.cpeMatch || []) {
        if (!match.criteria) continue;

        const parts = match.criteria.split(":");

        if (parts.length >= 5) {
          return {
            vendor: normalizeTechnology(parts[3]),
            product: normalizeTechnology(parts[3])
          };
        }
      }
    }
  }

  return {
    vendor: "Unknown",
    product: "Unknown",
  };
}