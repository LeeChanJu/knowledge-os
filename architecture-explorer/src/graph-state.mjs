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
  const match =
    typeof location !== "undefined" &&
    location.hash.match(/^#\/(en|ko-KR)(?:\/|$)/);
  const prefix = match ? "#/" + match[1] + "/explore" : "#";
  const q = typeof location !== "undefined" ? new URLSearchParams(location.hash.split("?")[1]) : new URLSearchParams();
  const context = new URLSearchParams();
  if (["remember","find","relationships","sources","correct","act"].includes(q.get("journey"))) for (const key of ["journey","step","concept"]) if(q.get(key)) context.set(key,q.get(key));
  if(q.get("atlas"))context.set("atlas",q.get("atlas"));
  const suffix = context.size ? "?" + context.toString() : "";
  return (id
    ? prefix + "/node/" + encodeURIComponent(id)
    : match
      ? prefix
      : "#/overview") + suffix;
}
export function fromHash(hash) {
  const match = hash.split("?")[0].match(/^#\/(?:(?:en|ko-KR)\/explore\/)?node\/(.+)$/);
  if (!match) return null;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}
