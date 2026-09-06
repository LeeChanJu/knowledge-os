import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { Architecture, ArchitectureNode, Status } from "./model";
const Graph = lazy(() => import("./Graph"));
import type { GraphControls } from "./Graph";
import {
  STATES,
  overviewIds,
  expand,
  filtered,
  search,
  visibleEdges,
  nodeHash,
  fromHash,
} from "./graph-state.mjs";

declare const __BUILD_INFO__: {
  checkoutRevision: string;
  dirty: boolean;
  state: string;
};
const statusClass = (status: string) =>
  status.toLowerCase().replaceAll(" ", "-");
function Badge({ status }: { status: Status }) {
  return (
    <span className={`badge ${statusClass(status)}`}>
      <span aria-hidden="true" /> {status}
    </span>
  );
}
function TextList({ title, items }: { title: string; items: string[] }) {
  return items.length ? (
    <section className="detail-section">
      <h3>{title}</h3>
      {items.map((s, i) => (
        <p key={i}>{s}</p>
      ))}
    </section>
  ) : null;
}

export default function App({ data }: { data: Architecture }) {
  const byId = useMemo(() => new Map(data.nodes.map((n) => [n.id, n])), [data]);
  const colors = useMemo(
    () => Object.fromEntries(data.domains.map((d) => [d.id, d.color])),
    [data],
  );
  const [selected, setSelected] = useState<string | null>(
    fromHash(location.hash),
  );
  const [revealed, setRevealed] = useState<Set<string>>(
    new Set(overviewIds(data.nodes)),
  );
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [domain, setDomain] = useState(""),
    [statuses, setStatuses] = useState<string[]>([...STATES]);
  const [resetTick, setResetTick] = useState(0);
  const [query, setQuery] = useState(""),
    [theme, setTheme] = useState(
      () => localStorage.getItem("architecture-theme") || "dark",
    );
  const controls = useRef<GraphControls | null>(null);
  const onReady = useCallback((value: GraphControls) => {
    controls.current = value;
  }, []);
  const [panelTab, setPanelTab] = useState<"overview" | "evidence">("overview");
  const applySelection = useCallback(
    (id: string | null) => {
      setSelected(id);
      setPanelTab("overview");
      if (id && byId.has(id)) {
        setRevealed((prev) => expand(prev, id, data.edges));
        setExpanded((prev) => new Set([...prev, id]));
      }
      if (!id) {
        setRevealed(new Set(overviewIds(data.nodes)));
        setExpanded(new Set());
      }
    },
    [byId, data],
  );
  useEffect(() => {
    applySelection(fromHash(location.hash));
    const handler = () => applySelection(fromHash(location.hash));
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, [applySelection]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("architecture-theme", theme);
  }, [theme]);
  const select = useCallback(
    (id: string) => {
      if (location.hash === nodeHash(id)) applySelection(id);
      else location.hash = nodeHash(id);
    },
    [applySelection],
  );
  const reset = () => {
    setResetTick((t) => t + 1);
    setDomain("");
    setStatuses([...STATES]);
    setQuery("");
    applySelection(null);
    location.hash = nodeHash(null);
  };
  const clearFilters = () => {
    setDomain("");
    setStatuses([...STATES]);
    setQuery("");
  };
  const visible = useMemo(
    () =>
      filtered(data.nodes, revealed, domain, statuses) as ArchitectureNode[],
    [revealed, domain, statuses],
  );
  const edges = useMemo(
    () => visibleEdges(data.edges, visible, expanded),
    [visible, expanded],
  );
  const results = useMemo(
    () =>
      query.trim()
        ? (search(data.nodes, query, domain, statuses) as ArchitectureNode[])
        : [],
    [query, domain, statuses],
  );
  const node = selected ? byId.get(selected) : undefined;
  const claim = node?.verification
    ? data.verification.find((c) => c.id === node.verification)
    : undefined;
  const neighbors = node
    ? data.edges.filter((e) => e.source === node.id || e.target === node.id)
    : [];
  const references = node?.references
    .map((id) => byId.get(id))
    .filter(Boolean) as ArchitectureNode[] | undefined;
  const statusCount = (status: string) =>
    data.verification.filter((c) => c.status === status).length;
  const selectLink = (n: ArchitectureNode) => (
    <button className="reference-link" key={n.id} onClick={() => select(n.id)}>
      <span>{n.name}</span>
      <small>{n.resource?.path || n.category}</small>
      <span className="link-arrow" aria-hidden="true">
        ↗
      </span>
    </button>
  );
  return (
    <div className="app">
      <header className="topbar">
        <a href="#/overview" className="brand" onClick={reset}>
          <span className="brand-mark" aria-hidden="true">
            K<span>·</span>
          </span>
          <span>
            Knowledge OS<small>ARCHITECTURE EXPLORER</small>
          </span>
        </a>
        <div className="topbar-center">
          <span className="live-dot" /> Read-only documentation{" "}
          <span className="separator">/</span> Local-first system of context
        </div>
        <button
          className="theme-button"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
        >
          {theme === "dark" ? "☀" : "☾"}
          <span>{theme === "dark" ? "Light" : "Dark"}</span>
        </button>
      </header>
      <div className="workspace">
        <aside className="sidebar" aria-label="Explore and filter">
          <div className="eyebrow">EXPLORE THE SYSTEM</div>
          <label className="search-label" htmlFor="search">
            Find a component or reference
          </label>
          <div className="search-box">
            <span aria-hidden="true">⌕</span>
            <input
              id="search"
              placeholder="Search architecture…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {query && (
              <button aria-label="Clear search" onClick={() => setQuery("")}>
                ×
              </button>
            )}
          </div>
          {query.trim() && (
            <div className="search-results" aria-label="Search results">
              <p className="muted">{results.length} matching results</p>
              {results.slice(0, 25).map((n) => (
                <button
                  key={n.id}
                  onClick={() => {
                    select(n.id);
                    setQuery("");
                  }}
                >
                  {n.name}
                  <small>
                    {n.category} · {n.status}
                  </small>
                </button>
              ))}
              {!results.length && <p>No matches within these filters.</p>}
            </div>
          )}
          <label className="filter-label" htmlFor="domain">
            Architectural domain
          </label>
          <select
            id="domain"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          >
            <option value="">All domains</option>
            {data.domains.map((d) => (
              <option value={d.id} key={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <fieldset>
            <legend>Implementation state</legend>
            {STATES.map((status) => (
              <label key={status} className="status-filter">
                <input
                  type="checkbox"
                  checked={statuses.includes(status)}
                  onChange={() =>
                    setStatuses((prev) =>
                      prev.includes(status)
                        ? prev.filter((s) => s !== status)
                        : [...prev, status],
                    )
                  }
                />
                <Badge status={status as Status} />
              </label>
            ))}
          </fieldset>
          <button className="text-button" onClick={clearFilters}>
            Clear filters
          </button>
          <div className="sidebar-divider" />
          <div className="list-heading">
            <span className="eyebrow">ON THE MAP</span>
            <span>{visible.length}</span>
          </div>
          <nav className="node-list" aria-label="Visible nodes">
            {visible.map((n) => (
              <button
                key={n.id}
                className={selected === n.id ? "active" : ""}
                onClick={() => select(n.id)}
                title={`${n.name} · ${n.status}`}
              >
                <span
                  className="domain-dot"
                  style={{ background: colors[n.domain] }}
                />
                <span>{n.name}</span>
                <span className="node-list-arrow" aria-hidden="true">
                  ↗
                </span>
              </button>
            ))}
            {!visible.length && (
              <p className="muted">
                No visible nodes. Clear filters or search an unexpanded
                component.
              </p>
            )}
          </nav>
          <div className="sidebar-footer">
            DOCUMENTATION, NOT RUNTIME
            <br />
            <span>No service or database connection</span>
          </div>
        </aside>
        <main className="map-pane">
          <div className="map-heading">
            <div className="breadcrumb">
              <button onClick={reset}>Architecture</button>
              <span>/</span>
              <span>{node?.name || "Overview"}</span>
            </div>
            <div className="map-title">
              <div>
                <h1>
                  {node ? "Follow the connections." : "A map of the system."}
                </h1>
                <p>
                  {node
                    ? "One neighborhood at a time. Every claim leads back to repository evidence."
                    : "From source records to governed context. Select a node to see what happens around it."}
                </p>
              </div>
              <span className="version-label">v0.1 · milestone 1</span>
            </div>
          </div>
          <div className="graph-shell">
            <Suspense
              fallback={<div className="empty-map">Loading architecture…</div>}
            >
              <Graph
                resetTick={resetTick}
                nodes={visible}
                edges={edges}
                selected={selected}
                theme={theme}
                onSelect={select}
                onReady={onReady}
                colors={colors}
              />
            </Suspense>
            {!visible.length && (
              <div className="empty-map">
                <h2>No nodes match these filters</h2>
                <p>The map retains your expansion state.</p>
                <button className="primary" onClick={clearFilters}>
                  Show all states and domains
                </button>
              </div>
            )}
            <div className="map-meta" aria-live="polite">
              <span>{visible.length} nodes</span>
              <span>{edges.length} relationships</span>
              <span>
                {expanded.size ? "Expanded view" : "Architecture overview"}
              </span>
            </div>
            <div className="map-controls">
              <button
                aria-label="Zoom out"
                onClick={() => controls.current?.zoom(0.8)}
              >
                −
              </button>
              <button
                aria-label="Zoom in"
                onClick={() => controls.current?.zoom(1.25)}
              >
                +
              </button>
              <span />
              <button onClick={() => controls.current?.fit()}>Fit</button>
              <button onClick={reset}>Reset overview</button>
            </div>
          </div>
          <div className="graph-legend">
            <span>
              <i className="legend-line incoming" />
              Incoming
            </span>
            <span>
              <i className="legend-line outgoing" />
              Outgoing
            </span>
            <span>
              <i className="legend-box" />
              Component / concept
            </span>
            <span>
              <i className="legend-box dashed" />
              Deferred
            </span>
            <span className="graph-hint">Drag to pan · Scroll to zoom</span>
          </div>
          <footer className="freshness">
            <div>
              <span className="live-dot" />
              {__BUILD_INFO__.state}
              <span className="muted"> · schema {data.schemaVersion}</span>
            </div>
            <div title={data.baselineRevision}>
              Evidence <code>{data.baselineRevision.slice(0, 7)}</code>
            </div>
            <div title={__BUILD_INFO__.checkoutRevision}>
              Checkout{" "}
              <code>{__BUILD_INFO__.checkoutRevision.slice(0, 7)}</code>
              {__BUILD_INFO__.dirty ? " + tracked changes" : ""}
            </div>
            <span className="freshness-note">
              Checked at build/start; not a live monitor
            </span>
          </footer>
        </main>
        <aside
          className="detail-panel"
          aria-label="Component details"
          key={selected || "overview"}
        >
          {!selected ? (
            <>
              <div className="eyebrow">YOUR GUIDE TO THE GRAPH</div>
              <h2>Context, with a paper trail.</h2>
              <p className="intro">
                Understand what the system owns, how its boundaries fit
                together, and where the evidence stops.
              </p>
              <div className="guide-path">
                <span>01</span>
                <div>
                  <h3>Start with the architecture</h3>
                  <p>
                    The initial map shows {overviewIds(data.nodes).length} major
                    concepts, not every implementation detail.
                  </p>
                </div>
                <span>02</span>
                <div>
                  <h3>Expand a neighborhood</h3>
                  <p>
                    Click a node to reveal direct connections, then follow a
                    contract, symbol or test.
                  </p>
                </div>
                <span>03</span>
                <div>
                  <h3>Inspect the evidence</h3>
                  <p>
                    Verification is a scoped claim with recorded provenance.
                    Existing code alone is not proof.
                  </p>
                </div>
              </div>
              <div className="audit-card">
                <div className="eyebrow">CURRENT REMEDIATION</div>
                <h3>Acceptance is still open.</h3>
                <p>
                  {statusCount("VERIFIED")} recorded verified findings ·{" "}
                  {statusCount("KNOWN ISSUE") - 1} unresolved findings · 1
                  release gate
                </p>
                <div className="finding-grid">
                  {data.verification.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => select(c.id)}
                      className={statusClass(c.status)}
                    >
                      {c.id === "release-gate" ? "Release gate" : c.id}
                      <span>{c.status === "VERIFIED" ? "✓" : "↗"}</span>
                    </button>
                  ))}
                </div>
                <p className="small muted">
                  F1/F2 import the explicit repository remediation decision. No
                  production tests were run by this Explorer.
                </p>
              </div>
              <section className="detail-section">
                <h3>Follow a starting point</h3>
                {["systems", "ingestion", "governance", "graph-retrieval"].map(
                  (id) => selectLink(byId.get(id)!),
                )}
              </section>
              <section className="detail-section">
                <h3>Eight documentation domains</h3>
                <div className="domain-legend">
                  {data.domains.map((d) => (
                    <div key={d.id}>
                      <span
                        className="domain-dot"
                        style={{ background: d.color }}
                      />
                      {d.name}
                    </div>
                  ))}
                </div>
              </section>
            </>
          ) : !node ? (
            <>
              <h2>Unknown documentation node</h2>
              <p>This link does not exist in this snapshot.</p>
              <button onClick={reset}>Return to overview</button>
            </>
          ) : (
            <>
              <div className="detail-kicker">
                <span className="eyebrow">
                  {node.category} /{" "}
                  {data.domains.find((d) => d.id === node.domain)?.name}
                </span>
                <button aria-label="Close component details" onClick={reset}>
                  ×
                </button>
              </div>
              <h2>{node.name}</h2>
              <Badge status={node.status} />
              <p className="intro">{node.description}</p>
              {!visible.some((n) => n.id === node.id) && (
                <div className="notice">
                  This selection is hidden by the active filters.{" "}
                  <button onClick={clearFilters}>Clear filters</button>
                </div>
              )}
              <div
                className="panel-tabs"
                role="tablist"
                aria-label="Detail sections"
              >
                <button
                  role="tab"
                  aria-selected={panelTab === "overview"}
                  onClick={() => setPanelTab("overview")}
                >
                  Overview
                </button>
                <button
                  role="tab"
                  aria-selected={panelTab === "evidence"}
                  onClick={() => setPanelTab("evidence")}
                >
                  Evidence <span>{node.references.length}</span>
                </button>
              </div>
              {panelTab === "overview" ? (
                <>
                  <TextList
                    title="Why it exists / responsibility"
                    items={node.responsibilities}
                  />
                  <TextList title="Inputs" items={node.inputs} />
                  <TextList title="Outputs" items={node.outputs} />
                  <TextList title="What it owns" items={node.owns} />
                  <TextList title="Invariants" items={node.invariants} />
                  {node.resource && (
                    <section className="detail-section">
                      <h3>Exact repository reference</h3>
                      <code className="source-path">
                        {node.resource.path}
                        {node.resource.symbol
                          ? "::" + node.resource.symbol
                          : node.resource.anchor
                            ? "#" + node.resource.anchor
                            : ""}
                      </code>
                      {node.resource.signature && (
                        <pre>{node.resource.signature}</pre>
                      )}
                      {node.resource.fields?.length ? (
                        <>
                          <h3>Declared fields</h3>
                          <pre>{node.resource.fields.join("\n")}</pre>
                        </>
                      ) : null}
                      {node.resource.decorators?.length ? (
                        <>
                          <h3>Decorators / surface</h3>
                          <pre>{node.resource.decorators.join("\n")}</pre>
                        </>
                      ) : null}
                      {node.resource.objects?.length ? (
                        <TextList
                          title="Schema objects"
                          items={node.resource.objects}
                        />
                      ) : null}
                      {node.resource.value ? (
                        <pre>
                          {JSON.stringify(node.resource.value, null, 2)}
                        </pre>
                      ) : null}
                      <p className="small muted">
                        Compact generated reference. Source bodies are not
                        copied into the Explorer.
                      </p>
                      {node.resource.fingerprint && (
                        <code className="fingerprint">
                          SHA-256 {node.resource.fingerprint}
                        </code>
                      )}
                    </section>
                  )}
                  {claim && (
                    <section className="detail-section claim">
                      <h3>Verification scope</h3>
                      <p>{claim.recordedOutcome}</p>
                      {claim.environment && <p>{claim.environment}</p>}
                      {claim.revision && (
                        <p className="small">
                          Correction revision{" "}
                          <code>{claim.revision.slice(0, 12)}</code>
                        </p>
                      )}
                      {claim.revisionScope === "original-source-history" && <p className="small muted">Revision from original source history; the public snapshot may not retain this Git object. Verification is tied to the recorded remediation decision and content fingerprints.</p>}
                    {claim.resolutionRequired && (
                        <>
                          <h3>Required resolution</h3>
                          <p>{claim.resolutionRequired}</p>
                        </>
                      )}
                      <p className="small muted">{claim.limitations}</p>
                      <p className="small">
                        {claim.tests.length} executable references ·{" "}
                        {Object.keys(claim.dependencies).length} pinned
                        dependencies
                      </p>
                    </section>
                  )}
                  {!claim && (
                    <section className="detail-section">
                      <h3>Verification status</h3>
                      <p>
                        {node.status === "KNOWN ISSUE"
                          ? "An open finding affects this scope. Inspect the finding for its exact invariant and required proof."
                          : node.status === "DEFERRED"
                            ? "This capability is intentionally deferred, not an implemented runtime service."
                            : "Implementation or repository evidence is present. This node does not claim independently verified behavior."}
                      </p>
                    </section>
                  )}
                  {!!node.knownIssues.length && (
                    <section className="detail-section">
                      <h3>Known findings</h3>
                      {node.knownIssues.map((id) => selectLink(byId.get(id)!))}
                    </section>
                  )}
                  <TextList
                    title="Unknowns / documentation gaps"
                    items={node.gaps}
                  />
                  <TextList
                    title="Intentional deferrals"
                    items={node.deferrals}
                  />
                  {!!node.contracts.length && (
                    <section className="detail-section">
                      <h3>Stable contracts</h3>
                      {node.contracts.map((c) =>
                        selectLink(byId.get("contract-" + c)!),
                      )}
                    </section>
                  )}
                  <section className="detail-section">
                    <h3>Before, after & related components</h3>
                    {neighbors
                      .filter(
                        (e) =>
                          byId.get(e.source === node.id ? e.target : e.source)
                            ?.category !== "reference",
                      )
                      .slice(0, 30)
                      .map((e) => {
                        const other = byId.get(
                          e.source === node.id ? e.target : e.source,
                        )!;
                        return (
                          <button
                            className="relationship"
                            key={e.id}
                            onClick={() => select(other.id)}
                          >
                            <small
                              className={
                                e.source === node.id ? "outgoing" : "incoming"
                              }
                            >
                              {e.source === node.id ? "OUT →" : "← IN"}{" "}
                              {e.label}
                            </small>
                            <span>{other.name}</span>
                          </button>
                        );
                      })}
                  </section>
                </>
              ) : (
                <>
                  <section className="detail-section">
                    <h3>Repository evidence</h3>
                    <p className="small muted">
                      References identify exact objects. A test reference does
                      not mean it passed. Select a finding to inspect recorded
                      verification.
                    </p>
                    {references?.length ? (
                      references.map(selectLink)
                    ) : (
                      <p>
                        Reach supporting components using the incoming
                        relationships in Overview.
                      </p>
                    )}
                  </section>
                  {claim && (
                    <section className="detail-section">
                      <h3>Pinned verification dependencies</h3>
                      {Object.entries(claim.dependencies).map(
                        ([path, digest]) => (
                          <div key={path} className="dependency">
                            <code>{path}</code>
                            <small>{digest}</small>
                          </div>
                        ),
                      )}
                    </section>
                  )}
                </>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
