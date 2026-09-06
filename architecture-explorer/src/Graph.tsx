import { t } from "./i18n";
import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import type { ArchitectureNode, Edge } from "./model";

export interface GraphControls {
  fit: () => void;
  zoom: (factor: number) => void;
}
export default function Graph({
  resetTick,
  nodes,
  edges,
  selected,
  theme,
  onSelect,
  onReady,
  colors,
}: {
  resetTick: number;
  nodes: ArchitectureNode[];
  edges: Edge[];
  selected: string | null;
  theme: string;
  onSelect: (id: string) => void;
  onReady: (controls: GraphControls) => void;
  colors: Record<string, string>;
}) {
  const container = useRef<HTMLDivElement>(null),
    cy = useRef<cytoscape.Core | null>(null);
  const layoutKey = useRef("");
  const select = useRef(onSelect);
  select.current = onSelect;
  useEffect(() => {
    const instance = cytoscape({
      container: container.current,
      elements: [],
      minZoom: 0.2,
      maxZoom: 2.8,
      layout: { name: "preset" },
    });
    cy.current = instance;
    layoutKey.current = "";
    instance.on("tap", "node", (e) => select.current(e.target.id()));
    onReady({
      fit: () => {
        const focus = instance.$("node.focused");
        instance.fit(
          focus.nonempty()
            ? focus.closedNeighborhood().nodes()
            : instance.nodes(),
          45,
        );
      },
      zoom: (factor) =>
        instance.zoom({
          level: instance.zoom() * factor,
          renderedPosition: {
            x: instance.width() / 2,
            y: instance.height() / 2,
          },
        }),
    });
    const observer = new ResizeObserver(() => {
      instance.resize();
    });
    observer.observe(container.current!);
    return () => {
      observer.disconnect();
      instance.destroy();
      cy.current = null;
    };
  }, [onReady]);
  useEffect(() => {
    const instance = cy.current;
    if (!instance) return;
    const dark = theme === "dark";
    instance.style([
      {
        selector: "node",
        style: {
          "background-color": dark ? "#18222b" : "#ffffff",
          "border-width": 1.5,
          "border-color": "data(color)",
          shape: "round-rectangle",
          width: 178,
          height: 64,
          label: "data(name)",
          color: dark ? "#e5edf2" : "#172d3e",
          "font-size": 14,
          "font-family": "system-ui",
          "text-wrap": "wrap",
          "text-overflow-wrap": "whitespace",
          "text-max-width": "154px",
          "text-valign": "center",
          "text-halign": "center",
          "overlay-opacity": 0,
        },
      },
      {
        selector: 'node[category = "primitive"]',
        style: { shape: "round-rectangle", "border-width": 2.5 },
      },
      {
        selector: 'node[category = "contract"]',
        style: { shape: "hexagon", width: 180, height: 76 },
      },
      {
        selector: 'node[category = "finding"]',
        style: {
          shape: "round-rectangle",
          "border-color": "#d99f75",
          "background-color": dark ? "#322822" : "#fff0df",
        },
      },
      {
        selector: 'node[status = "DEFERRED"]',
        style: { "border-style": "dashed", "background-opacity": 0.6 },
      },
      {
        selector: 'node[status = "KNOWN ISSUE"]',
        style: { "border-style": "double", "border-width": 3 },
      },
      {
        selector: "edge",
        style: {
          width: 1.1,
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.8,
          "line-color": dark ? "#405564" : "#bac9d2",
          "target-arrow-color": dark ? "#617888" : "#8ba0ad",
          label: "data(label)",
          "font-size": 10,
          "font-family": "system-ui",
          color: dark ? "#8fa6b7" : "#526b7d",
          "text-rotation": "autorotate",
          "text-background-color": dark ? "#101920" : "#edf3f6",
          "text-background-opacity": 0.95,
          "text-background-padding": "3px",
          "text-margin-y": -2,
          "overlay-opacity": 0,
        },
      },
      { selector: ".dimmed", style: { opacity: 0.25 } },
      {
        selector: "node.focused",
        style: {
          "border-width": 4,
          "border-color": "#7bd8c9",
          "background-color": dark ? "#22433f" : "#d6f3eb",
        },
      },
      {
        selector: "edge.incoming",
        style: {
          width: 2.5,
          "line-color": "#d9ad72",
          "target-arrow-color": "#d9ad72",
          color: dark ? "#f0cda0" : "#825017",
          "z-index": 9,
        },
      },
      {
        selector: "edge.outgoing",
        style: {
          width: 2.5,
          "line-color": "#6ecbbb",
          "target-arrow-color": "#6ecbbb",
          color: dark ? "#9be4d7" : "#14685a",
          "z-index": 9,
        },
      },
    ]);
    const desired = new Set([
      ...nodes.map((n) => n.id),
      ...edges.map((e) => e.id),
    ]);
    const key = [
      resetTick,
      selected || "",
      ...nodes.map((n) => n.id),
      ...edges.map((e) => e.id),
    ].join("|");
    instance.batch(() => {
      instance
        .elements()
        .filter((el) => !desired.has(el.id()))
        .remove();
      nodes.forEach((n, index) => {
        const data = {
          id: n.id,
          name: n.resource?.symbol
            ? n.name
                .replace(/^test_/, "")
                .replaceAll("_", " ")
                .replace("GraphStore.", "GraphStore\n")
            : n.name,
          category: n.category,
          status: n.status,
          color: colors[n.domain] || "#a4aebe",
        };
        if (instance.getElementById(n.id).empty())
          instance.add({
            group: "nodes",
            data,
            position: n.position
              ? { ...n.position }
              : {
                  x: (index % 5) * 240,
                  y: 1050 + Math.floor(index / 5) * 100,
                },
          });
        else instance.getElementById(n.id).data(data);
      });
      for (const e of edges)
        if (instance.getElementById(e.id).empty())
          instance.add({ group: "edges", data: { ...e } });
      instance.elements().removeClass("dimmed focused incoming outgoing");
      const focus = selected
        ? instance.getElementById(selected)
        : instance.collection();
      if (focus.nonempty()) {
        instance.elements().addClass("dimmed");
        focus.closedNeighborhood().removeClass("dimmed");
        focus.addClass("focused");
        focus.incomers("edge").addClass("incoming");
        focus.outgoers("edge").addClass("outgoing");
      }
    });
    if (layoutKey.current !== key) {
      layoutKey.current = key;
      const focus = selected
        ? instance.getElementById(selected)
        : instance.collection();
      if (focus.nonempty()) {
        // Preserve all revealed nodes, but frame the selected neighborhood at a readable scale.
        // A deterministic preset prevents asynchronous layout results from undoing Reset.
        const local = focus.closedNeighborhood();
        const incoming = focus
          .incomers("node")
          .sort((a, b) => a.id().localeCompare(b.id()));
        const outgoing = focus
          .outgoers("node")
          .difference(incoming)
          .sort((a, b) => a.id().localeCompare(b.id()));
        focus.position({ x: 0, y: 0 });
        const column = (
          items: cytoscape.CollectionReturnValue,
          direction: number,
        ) =>
          items.forEach((item, i) => {
            item.position({
              x: direction * (310 + Math.floor(i / 6) * 245),
              y: ((i % 6) - (Math.min(6, items.length) - 1) / 2) * 122,
            });
          });
        column(incoming, -1);
        column(outgoing, 1);
        instance
          .nodes()
          .difference(local)
          .forEach((item, i) => {
            item.position({
              x: 1800 + (i % 5) * 240,
              y: Math.floor(i / 5) * 140,
            });
          });
        instance.fit(local.nodes(), 65);
        if (instance.zoom() > 1.15) {
          instance.zoom(1.15);
          instance.center(local.nodes());
        }
      } else {
        instance.nodes().forEach((el, i) => {
          el.position({
            ...(nodes.find((n) => n.id === el.id())?.position || {
              x: (i % 5) * 240,
              y: Math.floor(i / 5) * 140,
            }),
          });
        });
        instance.fit(instance.nodes(), 40);
      }
    }
  }, [resetTick, nodes, edges, selected, theme, colors]);
  return (
    <div
      ref={container}
      className="graph-canvas"
      role="application"
      aria-label={t(
        "Architecture graph. Drag to pan, scroll to zoom. Use the node list for keyboard selection.",
      )}
    />
  );
}
