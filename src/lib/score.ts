export function calculatePriorityScore(
  cvss: number | null,
  epss: number,
  isKEV: boolean
): number {
  const cvssWeight = (cvss ?? 0) * 0.4;

  const epssWeight = epss * 10 * 0.3;

  const kevWeight = isKEV ? 3 : 0;

  return Number(
    (cvssWeight + epssWeight + kevWeight).toFixed(2)
  );
}