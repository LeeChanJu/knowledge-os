export const STATES = ["VERIFIED", "IMPLEMENTED", "KNOWN ISSUE", "DEFERRED"];
export const overviewIds = (nodes) =>
  nodes.filter((n) => n.overview).map((n) => n.id);
export function expand(ids, id, edges) {
  const next = new Set([...ids, id]);
  for (const e of edges) {
    if (e.source === id) next.add(e.target);
    if (e.target === id) next.add(e.source);
  }
  return next;
}
export function filtered(nodes, revealed, domain, statuses) {
  return nodes.filter(
    (n) =>
      revealed.has(n.id) &&
      (!domain || n.domain === domain) &&
      statuses.includes(n.status),
  );
}
export function search(nodes, query, domain, statuses) {
  const words = query.trim().toLowerCase().split(/\s+/);
  return nodes.filter(
    (n) =>
      (!domain || n.domain === domain) &&
      statuses.includes(n.status) &&
      words.every((w) =>
        `${n.name} ${n.description} ${n.resource?.path || ""}`
          .toLowerCase()
          .includes(w),
      ),
  );
}
export function visibleEdges(edges, nodes, expanded) {
  const ids = new Set(nodes.map((n) => n.id));
  return edges.filter(
    (e) =>
      ids.has(e.source) &&
      ids.has(e.target) &&
      (e.overview || expanded.has(e.source) || expanded.has(e.target)),
  );
}
export function nodeHash(id) {
  return id ? "#/node/" + encodeURIComponent(id) : "#/overview";
}
export function fromHash(hash) {
  if (!hash.startsWith("#/node/")) return null;
  try {
    return decodeURIComponent(hash.slice(7));
  } catch {
    return null;
  }
}
