export type Status = "VERIFIED" | "IMPLEMENTED" | "KNOWN ISSUE" | "DEFERRED";
export interface Reference {
  id: string;
  path: string;
  symbol?: string;
  anchor?: string;
  kind: string;
  signature?: string;
  fingerprint?: string;
  fields?: string[];
  decorators?: string[];
  objects?: string[];
  value?: unknown;
}
export interface ArchitectureNode {
  id: string;
  name: string;
  category: string;
  domain: string;
  overview: boolean;
  description: string;
  responsibilities: string[];
  inputs: string[];
  outputs: string[];
  owns: string[];
  invariants: string[];
  gaps: string[];
  deferrals: string[];
  contracts: string[];
  references: string[];
  status: Status;
  knownIssues: string[];
  verification?: string;
  resource?: Reference;
  position?: { x: number; y: number };
}
export interface Edge {
  id: string;
  source: string;
  target: string;
  label: string;
  references: string[];
  overview: boolean;
}
export interface Claim {
  id: string;
  title: string;
  scope: string;
  status: Status;
  recordedOutcome: string;
  environment: string;
  revision: string;
  revisionScope?: "repository" | "original-source-history";
  limitations: string;
  resolutionRequired: string;
  dependencies: Record<string, string>;
  tests: { path: string; symbol?: string }[];
  sources: { path: string; anchor?: string }[];
  affects: string[];
}
export interface Architecture {
  schemaVersion: string;
  evidenceDigest: string;
  baselineRevision: string;
  nodes: ArchitectureNode[];
  edges: Edge[];
  domains: { id: string; name: string; color: string }[];
  notes: string[];
  verification: Claim[];
}
