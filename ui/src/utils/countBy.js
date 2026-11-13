// Turns a list of records into [{ name, value }] counts for one field.
// Example: countBy(experiments, "program") -> [{ name: "BASS", value: 2 }, ...]
export function countBy(items, key) {
  const counts = {};
  items.forEach((item) => {
    counts[item[key]] = (counts[item[key]] || 0) + 1;
  });
  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => String(a.name).localeCompare(String(b.name), undefined, { numeric: true }));
}
