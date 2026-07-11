import supabase from "../config/supabase";
import { toDatabase } from "../lib/mappers/vulnerabilityMapper";
import { EnrichedVulnerability } from "../types/vulnerability";

export async function saveVulnerabilities(
    vulnerabilities: EnrichedVulnerability[]
) {
    const rows = vulnerabilities.map(toDatabase);

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