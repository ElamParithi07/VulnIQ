import { fetchNVDVulnerabilities } from "../services/nvd";
import { fetchKEVCatalog } from "../services/kev";
import { fetchEPSSScores } from "../services/epss";
import { enrichVulnerabilities } from "../lib/enrich";
import { saveVulnerabilities } from "../services/database";

async function main() {
    console.log("Fetching latest CVEs...\n");

    const vulnerabilities =
        await fetchNVDVulnerabilities();

    const cveIds = vulnerabilities.map(v => v.id);

    const epssMap = await fetchEPSSScores(cveIds);

    console.log(
        `Fetched EPSS scores for ${epssMap.size} CVEs.\n`
    );

    console.log("Fetching KEV catalog...\n");
    const kevSet = await fetchKEVCatalog();

    console.log(`KEV Catalog contains ${kevSet.size} vulnerabilities.\n`);


    console.log(
        `Fetched ${vulnerabilities.length} vulnerabilities.\n`
    );

    const enriched = enrichVulnerabilities(
        vulnerabilities,
        kevSet,
        epssMap
    );
    await saveVulnerabilities(enriched);

    // const sorted = enriched.sort(
    //     (a, b) => b.priorityScore - a.priorityScore
    // );

    // console.log("Top 10 Prioritized Vulnerabilities\n");

    // sorted.slice(0, 10).forEach((v, index) => {
    //     console.log(`========== ${index + 1} ==========`);

    //     console.log("ID:", v.id);

    //     console.log("Priority:", v.priorityScore);

    //     console.log("CVSS:", v.cvss);

    //     console.log("EPSS:", v.epss);

    //     console.log("KEV:", v.isKEV);

    //     console.log("Vendor:", v.vendor);

    //     console.log("Product:", v.product);

    //     console.log();
    // });
}

main();