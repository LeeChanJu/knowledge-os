import learning from "../../data/learning.json";
import type { Architecture } from "../model";
import type { Language } from "../i18n";
export function localizedArchitecture(
  data: Architecture,
  lang: Language,
): Architecture {
  const content = learning as any;
  const words = content.locales[lang] as Record<string, string>;
  const translate = (s: string) => words[s] || s;
  const descriptions = content.architecture[lang];
  const claims = content.claims[lang];
  return {
    ...data,
    domains: data.domains.map((d) => ({ ...d, name: translate(d.name) })),
    notes: data.notes.map(translate),
    verification: data.verification.map((c) => ({ ...c, ...claims[c.id] })),
    edges: data.edges.map((e) => ({ ...e, label: translate(e.label) })),
    nodes: data.nodes.map((n) => {
      if (descriptions[n.id]) return { ...n, ...descriptions[n.id] };
      if (n.verification) {
        const c = claims[n.verification];
        return {
          ...n,
          name: n.id + " · " + c.title,
          description: c.scope,
          responsibilities: n.responsibilities.map(translate),
          inputs: [],
          outputs: [],
          owns: n.owns.map(translate),
          invariants: n.invariants.map((v) =>
            v ===
            data.verification.find((x) => x.id === n.verification)
              ?.resolutionRequired
              ? c.resolutionRequired
              : translate(v),
          ),
          gaps: [c.limitations],
          deferrals: [],
        };
      }
      return { ...n, gaps: n.gaps.map(translate) };
    }),
  };
}
