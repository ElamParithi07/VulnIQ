import { getAllVulnerabilities } from "../database/vulnerability";
import { matchVulnerabilities } from "../../lib/matching";

export async function getTopVulnerabilitiesForUser(
  techTags: string[]
) {

  const vulnerabilities =
    await getAllVulnerabilities();

  return matchVulnerabilities(
    vulnerabilities,
    techTags
  );

}