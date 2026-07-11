import axios from "axios";

const KEV_URL =
  "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json";

export async function fetchKEVCatalog(): Promise<Set<string>> {
  try {
    const response = await axios.get(KEV_URL);

    const vulnerabilities = response.data.vulnerabilities;

    const kevSet = new Set<string>();

    for (const vuln of vulnerabilities) {
      kevSet.add(vuln.cveID);
    }

    return kevSet;
  } catch (error: any) {
    console.error("Failed to fetch KEV:", error.message);

    return new Set();
  }
}