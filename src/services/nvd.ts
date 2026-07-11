import axios from "axios";
import { RawVulnerability } from "../types/vulnerability";
import { extractVendorAndProduct } from "../lib/normalization/vendor";
import { env } from "../config/env";
import { RESULTS_PER_PAGE } from "../config/constants";


const BASE_URL =
  "https://services.nvd.nist.gov/rest/json/cves/2.0";

export async function fetchNVDVulnerabilities(): Promise<RawVulnerability[]> {
  try {
    const now = new Date();

    const yesterday = new Date(
    now.getTime() - 24 * 60 * 60 * 1000
    );

    const response = await axios.get(BASE_URL, {
    params: {
        lastModStartDate: yesterday.toISOString(),
        lastModEndDate: now.toISOString(),
        resultsPerPage: RESULTS_PER_PAGE,
    },
    headers: env.NVD_API_KEY
        ? {
            apiKey: env.NVD_API_KEY,
        }
        : {},
    });

    const vulnerabilities = response.data.vulnerabilities;

    return vulnerabilities.map((item: any): RawVulnerability => {
      const cve = item.cve;

      const cvss =
        cve.metrics?.cvssMetricV31?.[0]?.cvssData?.baseScore ??
        cve.metrics?.cvssMetricV30?.[0]?.cvssData?.baseScore ??
        cve.metrics?.cvssMetricV2?.[0]?.cvssData?.baseScore ??
        null;
    
      const { vendor, product } = extractVendorAndProduct(
        cve.configurations
      );

      return {
        id: cve.id,

        title: cve.id,

        description:
          cve.descriptions?.find(
            (d: any) => d.lang === "en"
          )?.value ?? "",

        vendor,

        product,

        cvss,

        published: cve.published,

        modified: cve.lastModified,
      };
    });
  } catch (error: any) {
    console.error(
      "Failed to fetch NVD:",
      error.response?.data || error.message
    );

    return [];
  }
}