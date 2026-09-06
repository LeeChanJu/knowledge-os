import learning from "../../data/learning.json";
export const manifest = learning.manifest;
export function docForNode(id: string) {
  return (
    manifest.pages.find((p) => p.nodeIds.includes(id))?.id ||
    manifest.pages.find((p) => p.referenceIds.includes(id))?.id ||
    "knowledge-os"
  );
}
export function githubLink(id: string) {
  const ref = (learning.github.references as Record<string, { path: string }>)[
    id
  ];
  return ref
    ? `${learning.github.repository}/blob/${learning.github.revision}/${ref.path.split("/").map(encodeURIComponent).join("/")}`
    : "#";
}
