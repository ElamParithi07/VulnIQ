import { getTopVulnerabilitiesForUser } from "../services/matching";

async function main() {
  const results =
    await getTopVulnerabilitiesForUser([
      "linux",
      "apache",
      "postgresql",
    ]);

  console.log(
    `Found ${results.length} vulnerabilities\n`
  );

  results.forEach((v, index) => {
    console.log(
      `${index + 1}. ${v.id}`
    );

    console.log(
      `${v.vendor} - ${v.product}`
    );

    console.log(
      `Priority: ${v.priorityScore}`
    );

    console.log("-------------------");
  });
}

main();