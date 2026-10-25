/** Versioned static transport, subject selection, filtering, and complete exports. */
export const SCHEMA_VERSION = 1;
export async function decodeResponse(response, url) {
  if (!response.ok)
    throw Error(`Cannot load ${new URL(url).pathname} (${response.status})`);
  let value;
  if (!new URL(url).pathname.endsWith(".json.gz"))
    value = await response.json();
  else {
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes[0] !== 0x1f || bytes[1] !== 0x8b)
      value = JSON.parse(new TextDecoder().decode(bytes));
    else {
      if (typeof DecompressionStream === "undefined")
        throw Error("Please use a current browser to load the study data.");
      value = await new Response(
        new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip")),
      ).json();
    }
  }
  if (!Array.isArray(value) && value.schema_version !== SCHEMA_VERSION)
    throw Error(
      "The dashboard data version is unsupported. Refresh the page to load the current release.",
    );
  return value;
}
export function createClient(fetcher = fetch) {
  const cache = new Map();
  const get = (url) => {
    const key = String(url);
    if (!cache.has(key))
      cache.set(
        key,
        fetcher(key, { cache: "no-cache" })
          .then((r) => decodeResponse(r, key))
          .catch((e) => {
            cache.delete(key);
            throw e;
          }),
      );
    return cache.get(key);
  };
  return { get };
}
export async function loadRows(get, urlFor, table, selected, allSubjects) {
  const all = selected.length === allSubjects.length && selected.length > 0,
    subjects = new Set(selected);
  const chunks = table.chunks.filter(
    (c) =>
      table.subject_index === null ||
      all ||
      c.subjects.some((s) => subjects.has(s)),
  );
  const records = (
    await Promise.all(chunks.map((c) => get(urlFor(c.url))))
  ).flat();
  return records
    .filter(
      (r) =>
        table.subject_index === null ||
        all ||
        subjects.has(String(r[table.subject_index + 1])),
    )
    .sort((a, b) => a[0] - b[0]);
}
export function filterRows(rows, metadata, query, peers) {
  const q = query.toLowerCase().trim();
  if (!q) return rows;
  const match = (r) =>
    r.slice(1).some((v) =>
      String(v ?? "")
        .toLowerCase()
        .includes(q),
    );
  const subjects = new Set();
  for (const { rows: records, meta } of peers)
    if (meta.subject_index !== null)
      for (const row of records)
        if (match(row)) subjects.add(row[meta.subject_index + 1]);
  return rows.filter(
    (r) =>
      match(r) ||
      (metadata.subject_index !== null &&
        subjects.has(r[metadata.subject_index + 1])),
  );
}
export function csvContent(rows, columns) {
  const quote = (value) => {
    let text = String(value ?? "");
    if (typeof value === "string" && /^[=+@\t\r-]/.test(text))
      text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  return (
    [columns.map((c) => c.name), ...rows.map((r) => r.slice(1))]
      .map((r) => r.map(quote).join(","))
      .join("\r\n") + "\r\n"
  );
}
