# MCP semantic and hybrid retrieval — 2026-09-05

## Measured gap

The Knowledge Service already supported keyword, semantic, and hybrid `RetrievalQuery`, but MCP
exposed only keyword `search_knowledge`. Even after a future embedding adapter populated evidence,
Codex or Claude could not consume semantic retrieval through the stated stable service boundary.

## Minimum extension

`retrieve_knowledge` maps MCP arguments directly to `POST /v1/retrieval/query`. It supports the
existing three modes and bounds result count at 100 and input vectors at 4,096 elements. The runtime
still enforces its exact configured dimension. Workspace and principals come only from MCP host
configuration.

No embedding model, provider SDK, vector store, retrieval framework, or automatic embedding write
was added. A replaceable caller must supply the query vector and exact model/version; Neo4j returns
only authorized active Chunks carrying that same model/version. `search_knowledge` remains as a
backward-compatible keyword convenience tool.

## Verification

- Tool schema and payload tests prove mode/vector/model/version preservation, bounded inputs, and
  fixed access injection.
- The complete suite passes 80 tests.
- In isolated workspace `it-mcp-semantic-v1`, one Evidence Chunk received a provenance-bearing
  1,536-dimensional `it-model` vector.
- A real MCP protocol client used an adapter-supplied query vector. Both semantic and hybrid calls
  returned exactly that authorized Chunk.
- Exact cleanup removed the embedded Chunk and every fixture ancestor plus the Workspace and
  temporary SQLite store, leaving zero matching workspaces.

This proves the complete adapter path, not personal semantic quality. The personal corpus still has
zero embeddings, and provider selection remains gated by reproducibility and held-out retrieval
improvement.
