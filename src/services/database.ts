import supabase from "../config/supabase";
import { EnrichedVulnerability } from "../types/vulnerability";

export async function saveVulnerabilities(
    vulnerabilities: EnrichedVulnerability[]
) {
    const rows = vulnerabilities.map((v) => ({
        id: v.id,

        title: v.title,

        vendor: v.vendor,

        product: v.product,

        cvss_score: v.cvss,

        epss_score: v.epss,

        is_cisa_kev: v.isKEV,

        priority_score: v.priorityScore,

        published_at: v.published,
    }));

    const { data, error } = await supabase
        .from("vulnerability_cache")
        .upsert(rows)
        .select();

    if (error) {
        console.error("Supabase Error:");
        console.error(JSON.stringify(error, null, 2));
        throw error;
    }

    console.log(`Saved ${data?.length ?? 0} vulnerabilities.`);

    console.log(`Saved ${rows.length} vulnerabilities.`);
}