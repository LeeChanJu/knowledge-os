import { test } from "node:test";
import assert from "node:assert/strict";
import {
  STATES,
  expand,
  filtered,
  search,
  visibleEdges,
  fromHash,
  nodeHash,
} from "../src/graph-state.mjs";
const nodes = [
  {
    id: "a",
    name: "Source",
    domain: "source",
    status: "IMPLEMENTED",
    description: "registry",
  },
  {
    id: "b",
    name: "Chunk",
    domain: "evidence",
    status: "KNOWN ISSUE",
    description: "evidence",
  },
  {
    id: "c",
    name: "test_f6",
    domain: "references",
    status: "IMPLEMENTED",
    description: "regression",
    resource: { path: "tests/chunk.py" },
  },
];
const edges = [
  { id: "ab", source: "a", target: "b", overview: true },
  { id: "bc", source: "b", target: "c", overview: false },
];
test("one-hop expansion includes incoming and outgoing, never recurses", () => {
  assert.deepEqual([...expand(new Set(["a"]), "a", edges)], ["a", "b"]);
  assert.deepEqual([...expand(new Set(), "b", edges)], ["b", "a", "c"]);
});
test("filters consistently restrict revealed nodes and hidden search results", () => {
  assert.deepEqual(
    filtered(nodes, new Set(["a", "b"]), "evidence", STATES).map((n) => n.id),
    ["b"],
  );
  assert.deepEqual(filtered(nodes, new Set(["a", "b"]), "", []), []);
  assert.equal(search(nodes, "tests/chunk", "", STATES)[0].id, "c");
  assert.equal(search(nodes, "tests/chunk", "evidence", STATES).length, 0);
});
test("edges preserve direction and require visible endpoints and explicit expansion", () => {
  assert.deepEqual(
    visibleEdges(edges, nodes, new Set()).map((e) => e.id),
    ["ab"],
  );
  assert.deepEqual(
    visibleEdges(edges, nodes, new Set(["b"])).map((e) => e.id),
    ["ab", "bc"],
  );
  assert.equal(visibleEdges(edges, [nodes[0]], new Set(["a"])).length, 0);
});
test("hash routes round-trip paths and reject malformed encoding", () => {
  assert.equal(
    fromHash(nodeHash("ref:src/a.py::Thing.method")),
    "ref:src/a.py::Thing.method",
  );
  assert.equal(fromHash("#/node/%zz"), null);
  assert.equal(fromHash("#/overview"), null);
});

test('curated graph preserves evidence lineage and separate governance promotion', async()=>{
  const {readFileSync}=await import('node:fs');
  const model=JSON.parse(readFileSync(new URL('../data/architecture.json',import.meta.url)));
  for(const [source,target,label] of [['source','document','HAS_DOCUMENT'],['document','version','HAS_VERSION'],['version','chunk','HAS_CHUNK'],['chunk','assertion','EVIDENCE_FOR'],['proposal','approval','reviewed through'],['approval','assertion','permits promotion']]) {
    assert.ok(model.edges.some(e=>e.source===source&&e.target===target&&e.label===label),`${source} → ${target}: ${label}`);
  }
});
