import { analyzeVulnerability } from "../ai/analysis";
import {
    findCachedAnalysis,
    saveAnalysis,
} from "../database/ai";
import { getAllVulnerabilities, getVulnerabilityById } from "../database/vulnerability";
import { Intelligence } from "../../types/intelligence";

export async function analyzeIfNeeded(
    id: string
): Promise<Intelligence> {

    const cached = await findCachedAnalysis(id);

    if (cached) {
        console.log("Returning cached intelligence.");

        return cached;
    }

    const vulnerability =
        await getVulnerabilityById(id);

    if (!vulnerability) {
        throw new Error(`Vulnerability ${id} not found.`);
    }

    const intelligence =
        await analyzeVulnerability(vulnerability);

    await saveAnalysis(
        id,
        intelligence
    );
    console.log("Saved intelligence.");

    return intelligence;
}