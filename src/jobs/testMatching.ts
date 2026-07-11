import { getTopVulnerabilitiesForUser } from "../services/matching/matching";

async function main() {

  const results =
    await getTopVulnerabilitiesForUser([
      "linux",
      "apache",
      "postgresql"
    ]);

  console.log(results);

}

main();