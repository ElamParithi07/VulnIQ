import axios from "axios";
import { EPSS_BATCH_SIZE } from "../config/constants";

const EPSS_API = "https://api.first.org/data/v1/epss";

export async function fetchEPSSScores(
    cveIds: string[]
): Promise<Map<string, number>> {
    try {
        if (cveIds.length === 0) {
            return new Map();
        }

        console.log(`Fetching EPSS scores for ${cveIds.length} CVEs...`);

        const epssMap = new Map<string, number>();

        for (let i = 0; i < cveIds.length; i += EPSS_BATCH_SIZE) {
            const batch = cveIds.slice(i, i + EPSS_BATCH_SIZE);
            console.log(`Fetching EPSS scores for CVEs ${i + 1} to ${i + batch.length}...`);
            const response = await axios.get(EPSS_API, {
                params: {
                    cve: batch.join(","),
                },
            });

            for (const item of response.data.data) {
                epssMap.set(
                    item.cve,
                    Number(item.epss)
                );
            }
        }

        console.log(`Fetched EPSS scores for ${epssMap.size} CVEs.`);

        return epssMap;
    } catch (error: any) {
        console.error(
            "Failed to fetch EPSS:",
            error.message
        );

        return new Map();
    }
}