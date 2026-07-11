import supabase from "../config/supabase";
import { EnrichedVulnerability } from "../types/vulnerability";
import { TOP_VULNERABILITIES } from "../config/constants";

export async function getTopVulnerabilitiesForUser(
  techTags: string[],
  limit = TOP_VULNERABILITIES
): Promise<EnrichedVulnerability[]> {
  if (techTags.length === 0) {
    return [];
  }

  const vendorFilters = techTags.join(",");

  const { data, error } = await supabase
    .from("vulnerability_cache")
    .select("*")
    .or(
      `vendor.in.(${vendorFilters}),product.in.(${vendorFilters})`
    )
    .order("priority_score", {
      ascending: false,
    })
    .limit(limit);

  if (error) {
    throw error;
  }

  return (data ?? []).map((row: any) => ({
    id: row.id,
    title: row.title,
    description: "",
    vendor: row.vendor,
    product: row.product,
    cvss: row.cvss_score,
    epss: row.epss_score ?? 0,
    isKEV: row.is_cisa_kev,
    priorityScore: row.priority_score,
    published: row.published_at,
    modified: row.created_at,
  }));
}