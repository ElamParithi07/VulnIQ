export function normalizeTechnology(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ");
}