import {GuideLibrary} from '../atlas/GuideLibrary';
import {migrateHash} from '../atlas/integration';
import Atlas, {AtlasHome,AtlasReturn} from '../atlas/Atlas';
import {LearnHome, Journey, CapabilityNav, ContextTrail, ReferenceCatalog} from './LearnIA';
import {catalog, classification, capability, contextQuery, docHref, contextualHref} from './ia';
import {flowText} from './LearnFlow';
import {Flagship, isFlagship, flagshipText} from "./Flagship";
import { lazy, Suspense, useEffect, useMemo, useState, useRef } from "react";
import learning from "../../data/learning.json";
import type { Architecture, ArchitectureNode } from "../model";
import { language, route, t, type Language } from "../i18n";
import { docForNode, githubLink, manifest } from "./helpers";
import { localizedArchitecture } from "./localized";
import "./docs.css";
declare const __BUILD_INFO__: {
  checkoutRevision: string;
  dirty: boolean;
  state: string;
};
const Guide = lazy(() => import('../atlas/Guide'));
const Explorer = lazy(() => import("../App"));
type Page = {
  id: string;
  title: string;
  sections: { id: string; title: string; body: string }[];
  steps: { id: string; nodeId: string; title: string; body: string }[];
};
const categories: Record<string, string> = {
  "getting-started": "Getting started",
  concepts: "Core concepts",
  walkthroughs: "Walkthroughs",
  capabilities: "Capabilities",
  operations: "Operations",
  architecture: "Architecture decisions",
};
const initialRoute = () => location.hash || route(language());
function currentPath(hash: string) {
  return hash.replace(/^#\/(?:en|ko-KR)\/?/, "").split("?")[0];
}
export default function Site({ data }: { data: Architecture }) {
  const previousPath=useRef(location.hash.split("?")[0]);
  const [hash, setHash] = useState(initialRoute),
    [lang, setLang] = useState<Language>(language),
    [theme, setTheme] = useState(
      () => localStorage.getItem("architecture-theme") || "dark",
    );
  const [query, setQuery] = useState(""),
    [depth, setDepth] = useState("understand"),
    [term, setTerm] = useState<string | null>(null);
  useEffect(() => {
    if (!location.hash) location.replace(route(language()));
    const change = () => {
      setHash(location.hash);
      setLang(language());
      setQuery("");
      setDepth("understand");
      setTerm(null);
      const nextPath=location.hash.split("?")[0];
      if(nextPath!==previousPath.current)window.scrollTo(0,0);
      previousPath.current=nextPath;
    };
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  useEffect(() => {
    if (!term) return;
    const prior = document.activeElement as HTMLElement;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTerm(null);
      if (e.key === "Tab") {
        const items = Array.from(
          document.querySelectorAll<HTMLElement>(
            ".term-popover button,.term-popover a",
          ),
        );
        const first = items[0],
          last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      prior?.focus();
    };
  }, [term]);
  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem("architecture-language", lang);
  }, [lang]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("architecture-theme", theme);
    window.dispatchEvent(new Event("architecture-theme"));
  }, [theme]);
  const architecture = useMemo(
    () => localizedArchitecture(data, lang),
    [data, lang],
  );
  const byId = useMemo(
    () => new Map(architecture.nodes.map((n) => [n.id, n])),
    [architecture],
  );
  const docs = (
    learning.documents as unknown as Record<Language, Record<string, Page>>
  )[lang];
  const rawPath=currentPath(hash), archived=rawPath.startsWith("archive/"), archivedId=rawPath.startsWith("archive/document/")?rawPath.slice(17):null;
  const path = archivedId?"reference/concepts/"+archivedId:rawPath.replace(/^archive\//,""),
    legacy = hash.startsWith("#/node/") || hash === "#/overview";
  let mode =
    legacy || path === "explore" || path.startsWith("explore/")
      ? "explore"
      : path.startsWith("reference")
        ? "reference"
        : "learn";
  let slug = "";
  try {
    slug = decodeURIComponent(path.replace(/^learn\//, ""));
  } catch {
    /*invalid route below*/
  }
  const routeEntry=catalog.entries.find(e=>e.path===path||('archivePath' in e&&e.archivePath===path));
  if(routeEntry) slug=routeEntry.id;
  if(archivedId)slug=archivedId;
  if(path.startsWith("reference/guide/"))slug=slug.replace(/^reference\/guide\//, "");
  const classified=classification(slug);
  if(classified&&slug!=='start-here'&&!capability(slug))mode='reference';
  const atlasAxis=path==='runtime'?'runtime':path==='engineering'?'engineering':null;
  const atlasHome=!path;
  const learnSurface=(!path||path==='learn'||path==='learn/start-here'||!!capability(slug))&&!path.startsWith('reference');
  useEffect(()=>{
    const target=migrateHash(hash,lang);if(target&&target!==hash)location.replace(target);
  },[hash,lang]);
  const page = docs[slug],
    entry = manifest.pages.find((p) => p.id === slug);
  const home = !path;
  useEffect(() => {
    document.title = `${atlasAxis?(atlasAxis==='runtime'?(lang==='en'?'How it works':'시스템 동작'):(lang==='en'?'How it is built':'개발·검증')):capability(slug)?.title[lang] || page?.title || t(mode[0].toUpperCase() + mode.slice(1))} · Knowledge OS`;
  }, [page?.title, mode, lang, atlasAxis]);
  const href = (s: string) => {
    if(s.startsWith('learn/')&&classification(s.slice(6)))return docHref(lang,s.slice(6));
    const query=contextQuery();
    return route(lang,s)+((s.startsWith('reference')||s.startsWith('explore'))&&query?'?'+query:'');
  };
  const changeLanguage = (next: Language) => {
    const suffix = legacy
      ? "explore" + (hash.startsWith("#/node/") ? hash.slice(1) : "")
      : (archived?rawPath:path) + (hash.includes("?") ? "?" + hash.split("?")[1] : "");
    location.hash = route(next, suffix);
  };
  const referenceLinks = (ids: string[]) =>
    ids.map((id) => {
      const n = byId.get(id);
      return (
        n && (
          <div className="evidence-item" key={id}>
          <a
            className="evidence-card"
            href={href("reference/item/" + encodeURIComponent(id))}
          >
            <span>{t(n.resource?.kind || n.status)}</span>
            <strong>{n.name}</strong>
            <code>{n.resource?.path}</code>
            <small>{n.resource?.symbol}</small>
          </a>
          <a className="file-action" href={githubLink(id)} target="_blank" rel="noreferrer">{t("Evidence revision on GitHub")} ↗</a>
          </div>
        )
      );
    });
  const status = (n: ArchitectureNode) => (
    <span className={"badge " + n.status.toLowerCase().replaceAll(" ", "-")}>
      {n.status}
    </span>
  );
  const conceptTerms = [
    "ontology",
    "assertion",
    "evidence",
    "provenance",
    "embedding",
    "proposal",
    "supersession",
  ];
  const paragraphs = (body: string) => {
    const found = conceptTerms.filter(
      (id) =>
        id !== page?.id &&
        body
          .toLowerCase()
          .includes(
            (lang === "en"
              ? docs[id].title
              : docs[id].title.split(" (")[0]
            ).toLowerCase(),
          ),
    );
    return (
      <>
        <p>{body}</p>
        {found.length > 0 && (
          <div className="term-row">
            {found.slice(0, 3).map((id) => (
              <button
                key={id}
                onClick={() => setTerm(id)}
                aria-label={t("Explain this") + ": " + docs[id].title}
              >
                {docs[id].title} ⓘ
              </button>
            ))}
          </div>
        )}
      </>
    );
  };
  return (
    <div className="site">
      <header className="site-header">
        <a className="site-brand" href={href("")}>
          <span className="book-mark">
            K<span>·</span>
          </span>
          Knowledge OS <small>{t("FIELD GUIDE")}</small>
        </a>
        <nav aria-label={t("Main navigation")}>
          {["runtime", "engineering", "explore", "reference"].map((m) => (
            <a
              key={m}
              className={(atlasAxis||mode) === m ? "current" : ""}
              aria-current={(atlasAxis||mode) === m ? "page" : undefined}
              href={href(m === "learn" ? "learn/start-here" : m)}
            >
              {m==='runtime'?(lang==='en'?'How it works':'시스템 동작'):m==='engineering'?(lang==='en'?"How it’s built":'개발·검증'):t(m[0].toUpperCase() + m.slice(1))}
            </a>
          ))}
        </nav>
        <div className="site-preferences">
          <div className="language-switch" aria-label={t("Language")}>
            {(["ko-KR", "en"] as Language[]).map((l) => (
              <button
                key={l}
                aria-pressed={lang === l}
                onClick={() => changeLanguage(l)}
              >
                {l === "en" ? "English" : "한국어"}
              </button>
            ))}
          </div>
          <button
            className="theme-button"
            aria-label={t("Change theme")}
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? "☀" : "☾"}{" "}
            {t(theme === "dark" ? "Light" : "Dark")}
          </button>
        </div>
      </header>
      <AtlasReturn lang={lang}/>{archived&&<p className="archive-notice">{lang==='en'?'Archived original · current learning starts in the System Atlas.':'보관된 이전 문서 · 현재 학습은 시스템 지도에서 시작합니다.'} <a href={`#/${lang}`}>{lang==='en'?'System Atlas →':'시스템 지도 →'}</a></p>}
      {path.startsWith('reference/guide/') ? <Suspense fallback={<p>{t("Loading architecture…")}</p>}><Guide id={slug} lang={lang} architecture={architecture}/></Suspense> : atlasHome ? <AtlasHome lang={lang}/> : atlasAxis ? <Atlas lang={lang} axis={atlasAxis}/> : mode === "explore" ? (
        <div className="embedded-explorer"><ContextTrail lang={lang}/>
          <Suspense fallback={<p>{t("Loading architecture…")}</p>}>
            <Explorer key={lang} data={architecture} />
          </Suspense>
        </div>
      ) : learnSurface ? (
        <div className="documentation-layout flow-layout ia-layout"><aside className="docs-sidebar"><CapabilityNav lang={lang} active={capability(slug)?.id||'start-here'}/><a className="ia-reference-link" href={href('reference')}>{lang==='en'?'Concepts and technical reference':'개념·기술 참조'} ↗</a></aside>{capability(slug)?<Journey id={slug} lang={lang}/>:<LearnHome lang={lang}/>}</div>
      ) : (
        <div className={`documentation-layout ${isFlagship(slug)?"flow-layout":""}`}>
          <aside className="docs-sidebar">
            <nav className="reference-nav" aria-label={lang==='en'?'Reference navigation':'참조 탐색'}><a href={href('reference')}>{lang==='en'?'Concepts and explanations':'개념과 설명'}</a><a href={href('reference/objects')}>{lang==='en'?'Contracts, code, tests and migrations':'계약·코드·테스트·마이그레이션'}</a><a href={href('learn/start-here')}>{lang==='en'?'Back to capability journeys':'행동 흐름으로 돌아가기'}</a></nav>
            <label htmlFor="docs-search">{t('Search documentation')}</label><input id="docs-search" value={query} onChange={e=>setQuery(e.target.value)} placeholder={t('Search documentation')}/>
            {query&&<nav aria-label={t('Search results')}>{manifest.pages.filter(p=>(docs[p.id].title+' '+docs[p.id].sections.map(s=>s.body).join(' ')+' '+(isFlagship(p.id)?flowText(lang,p.id)+' '+flagshipText(lang,p.id):'')).toLowerCase().includes(query.toLowerCase())).map(p=><a key={p.id} href={docHref(lang,p.id)}>{docs[p.id].title}</a>)}{!manifest.pages.some(p=>(docs[p.id].title+' '+docs[p.id].sections.map(s=>s.body).join(' ')+' '+(isFlagship(p.id)?flowText(lang,p.id)+' '+flagshipText(lang,p.id):'')).toLowerCase().includes(query.toLowerCase()))&&<p>{t('No documents match.')}</p>}</nav>}
          </aside>
          {mode === "reference" && !page ? (
            <main className="docs-article reference-article"><ContextTrail lang={lang}/>{path==='reference'&&<><h1>{t('Reference')}</h1><GuideLibrary lang={lang}/></>}
              <ReferenceView
                path={path}
                architecture={architecture}
                lang={lang}
              />
            </main>
          ) : !page || !entry ? (
            <main className="docs-article">
              <h1>{t("Page not found")}</h1>
              <p>{t("This route is not in this snapshot.")}</p>
              <a href={href("learn/start-here")}>{t("Start learning")}</a>
            </main>
          ) : isFlagship(page.id) ? (
            <Flagship id={page.id} lang={lang} title={page.title} />
          ) : (
            <>
              <main className="docs-article" key={page.id}><ContextTrail lang={lang}/><p className="classified-role">{classified?.role} · {lang==='en'?'A contextual branch, not the next required lesson':'필요할 때 여는 가지 문서'}</p>
                <div className="eyebrow">
                  {classified?.role} / {t("FIELD NOTES")}
                </div>
                <h1>{page.title}</h1>
                <p className="article-lead">{page.sections[0].body}</p>
                <div
                  className="depth-tabs"
                  role="tablist"
                  aria-label={t("Reading depth")}
                >
                  {["understand", "how-it-works", "implementation"].map(
                    (id, i) => (
                      <button
                        key={id}
                        role="tab"
                        aria-selected={depth === id}
                        onClick={() => {
                          setDepth(id);
                          requestAnimationFrame(() => document
                            .getElementById(
                              id === "understand"
                                ? "plain-language"
                                : id === "how-it-works"
                                  ? "in-knowledge-os"
                                  : "implementation",
                            )
                            ?.scrollIntoView({
                              behavior: "smooth",
                              block: "start",
                            }));
                        }}
                      >
                        {i + 1}.{" "}
                        {t(["Understand", "How it works", "Implementation"][i])}
                      </button>
                    ),
                  )}
                </div>
                {page.sections.slice(1, 5).map((s) => (
                  <section
                    key={s.id}
                    id={s.id}
                    className={s.id === "example" ? "example-block" : ""}
                  >
                    <h2>{s.title}</h2>
                    {paragraphs(s.body)}
                    {s.id === "in-knowledge-os" && page.steps.length > 0 && (
                      <ol className="teaching-flow">
                        {page.steps.map((step, i) => (
                          <li key={step.id}>
                            <span className="step-index">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <div>
                              <a
                                href={href(
                                  "explore/node/" +
                                    encodeURIComponent(step.nodeId),
                                )}
                              >
                                {step.title} ↗
                              </a>
                              <p>{step.body}</p>
                              {status(byId.get(step.nodeId)!)}
                            </div>
                          </li>
                        ))}
                      </ol>
                    )}
                    {s.id === "in-knowledge-os" && !page.steps.length && (
                      <div className="mini-lineage">
                        {[
                          "source",
                          "document",
                          "version",
                          "chunk",
                          "assertion",
                        ].map((id, i) => (
                          <a href={href("explore/node/" + id)} key={id}>
                            {byId.get(id)?.name}
                            {i < 4 && <span> →</span>}
                          </a>
                        ))}
                      </div>
                    )}
                  </section>
                ))}
                <section id="related">
                  <h2>{page.sections[5].title}</h2>
                  <div className="related-concepts">
                    {entry.relatedPageIds.map((id) => (
                      <a key={id} href={href("learn/" + id)}>
                        {docs[id].title} ↗
                      </a>
                    ))}
                  </div>
                </section>
                <details
                  open={depth === "implementation"}
                  onToggle={(e) => {
                    if (e.currentTarget.open) setDepth("implementation");
                    else if (depth === "implementation") setDepth("understand");
                  }}
                >
                  <summary>{t("Implementation")}</summary>
                  <section id="technical">
                    <h2>{page.sections[6].title}</h2>
                    {paragraphs(page.sections[6].body)}
                  </section>
                  <section id="implementation">
                    <h2>{page.sections[7].title}</h2>
                    <p>{page.sections[7].body}</p>
                    <div className="implementation-nodes">
                      {entry.nodeIds.map((id) => (
                        <div key={id}>
                          {status(byId.get(id)!)}{" "}
                          <a href={href("explore/node/" + id)}>
                            {t("View in Architecture")}: {byId.get(id)?.name} ↗
                          </a>
                        </div>
                      ))}
                    </div>
                    <div className="evidence-grid">
                      {referenceLinks(entry.referenceIds)}
                    </div>
                  </section>
                </details>
                <section className="verification-callout">
                  <h2>{t("Verification status")}</h2>
                  <p>
                    {t(
                      "Code and references show implementation, not fresh verification. F1/F2 retain their recorded scope; F3–F8 and release acceptance remain open.",
                    )}
                  </p>
                  {entry.claimIds.map((id) => (
                    <a
                      key={id}
                      href={href("reference/item/" + encodeURIComponent(id))}
                    >
                      {byId.get(id)?.name} ↗
                    </a>
                  ))}
                </section>
                <div className="article-navigation">{classified?.journeys.map(id=><a key={id} href={href('learn/'+id)}>{capability(id)?.title[lang]} ↑</a>)}</div>
              </main>
              <aside className="article-toc">
                <span className="eyebrow">{t("On this page")}</span>
                {page.sections.slice(1).map((s) => (
                  <button
                    key={s.id}
                    onClick={() => {
                      if (["technical", "implementation"].includes(s.id))
                        setDepth("implementation");
                      setTimeout(
                        () =>
                          document
                            .getElementById(s.id)
                            ?.scrollIntoView({
                              behavior: "smooth",
                              block: "start",
                            }),
                        0,
                      );
                    }}
                  >
                    {s.title}
                  </button>
                ))}
                <a
                  className="toc-explore"
                  href={href("explore/node/" + entry.nodeIds[0])}
                >
                  {t("View in Architecture")} ↗
                </a>
              </aside>
            </>
          )}
        </div>
      )}
      {mode !== "explore" && (
        <footer className="docs-footer">
          {t("Checked snapshot")} · schema {learning.schemaVersion} ·{" "}
          {t("Evidence")} {data.baselineRevision.slice(0, 12)} · {t("Checkout")}{" "}
          {__BUILD_INFO__.checkoutRevision.slice(0, 12)}
          {__BUILD_INFO__.dirty ? " +" : ""} ·{" "}
          <a href={href("learn/verification")}>{t("Verification status")}</a>
        </footer>
      )}
      {term && (
        <div className="term-backdrop" onClick={() => setTerm(null)}>
          <section
            className="term-popover"
            role="dialog"
            aria-modal="true"
            aria-labelledby="term-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Escape") setTerm(null);
              }}
              onClick={() => setTerm(null)}
            >
              {t("Close")} ×
            </button>
            <h2 id="term-title">{docs[term].title}</h2>
            <p>{docs[term].sections[0].body}</p>
            <a href={href("learn/" + term)}>{t("Read the explanation")} →</a>
          </section>
        </div>
      )}
    </div>
  );
}
function ReferenceView({
  path,
  architecture,
  lang,
}: {
  path: string;
  architecture: Architecture;
  lang: Language;
}) {
  const [query, setQuery] = useState(""),
    [kind, setKind] = useState("");
  let id = "";
  try {
    id = decodeURIComponent(path.replace(/^reference\/item\//, ""));
  } catch {}
  const n = architecture.nodes.find((n) => n.id === id),
    isItem = path.startsWith("reference/item/");
  const items = architecture.nodes.filter(
    (n) => n.resource || n.verification || n.id.startsWith("contract-"),
  );
  const kinds = [
    "contract",
    "configuration",
    "class",
    "function",
    "python",
    "document",
    "test",
    "migration",
    "issue",
  ];
  const classify = (n: ArchitectureNode) =>
    n.verification
      ? "issue"
      : n.id.startsWith("contract-")
        ? "contract"
        : n.resource?.kind || n.category;
  if (isItem && !n)
    return (
      <>
        <h1>{t("Page not found")}</h1>
        <a href={contextualHref(lang, "reference")}>{t("Reference")}</a>
      </>
    );
  if (n) {
    const claim = architecture.verification.find(
      (c) => c.id === n.verification,
    );
    return (
      <>
        <a href={contextualHref(lang, "reference")}>← {t("Reference")}</a>
        <h1>{n.name}</h1>
        <p className="article-lead">{n.description}</p>
        <span
          className={"badge " + n.status.toLowerCase().replaceAll(" ", "-")}
        >
          {n.status}
        </span>
        <div className="reference-actions">
          <a href={contextualHref(lang, "explore/node/" + encodeURIComponent(n.id))}>
            {t("View in Architecture")} ↗
          </a>
          <a href={contextualHref(lang, "learn/" + docForNode(n.id))}>
            {t("Read the explanation")} ↗
          </a>
        </div>
        {n.resource && (
          <>
            <code className="source-path">
              {n.resource.path}
              {n.resource.symbol ? "::" + n.resource.symbol : ""}
            </code>
            <p>
              <a href={githubLink(n.id)} target="_blank" rel="noreferrer">
                {t("Evidence revision on GitHub")} ↗
              </a>
            </p>
            <p>
              <a
                href={
                  learning.github.repository + "/blob/main/" + n.resource.path
                }
                target="_blank"
                rel="noreferrer"
              >
                {t("Current repository on GitHub")} ↗
              </a>
            </p>
            <p className="muted">
              {t(
                "The evidence link is pinned to a public source snapshot. The current repository link may show later changes. Symbols are shown exactly; line numbers are omitted to avoid stale anchors.",
              )}
            </p>
            {n.resource.signature && <pre>{n.resource.signature}</pre>}
            {n.resource.fields?.length ? (
              <>
                <h2>{t("Declared fields")}</h2>
                <pre>{n.resource.fields.join("\n")}</pre>
              </>
            ) : null}
            {n.resource.decorators?.length ? (
              <pre>{n.resource.decorators.join("\n")}</pre>
            ) : null}
            {n.resource.objects?.length ? (
              <pre>{n.resource.objects.join("\n")}</pre>
            ) : null}
            {n.resource.value ? (
              <pre>{JSON.stringify(n.resource.value, null, 2)}</pre>
            ) : null}
          </>
        )}
        {claim && (
          <>
            <h2>{t("Verification scope")}</h2>
            <p>{claim.scope}</p>
            <p>{claim.recordedOutcome}</p>
            <p>{claim.environment}</p>
            <p>{claim.limitations}</p>
            <h2>{t("Required resolution")}</h2>
            <p>{claim.resolutionRequired || "—"}</p>
            <code>{claim.revision}</code>
          </>
        )}
        <h2>{t("Repository evidence")}</h2>
        {n.references.map((id) => (
          <p key={id}>
            <a href={contextualHref(lang, "reference/item/" + encodeURIComponent(id))}>
              {architecture.nodes.find((n) => n.id === id)?.name} ↗
            </a>
          </p>
        ))}
        <p>
          {t(
            "A reference locates evidence. Its existence alone is not proof of successful execution.",
          )}
        </p>
      </>
    );
  }
  const matches = items.filter(
    (n) =>
      (!kind || classify(n) === kind) &&
      (n.name + " " + n.resource?.path + " " + n.description)
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <>
      <div className="eyebrow">{t("Repository evidence")}</div>
      {path==='reference'?<h2>{lang==='en'?'Implementation objects':'구현 객체'}</h2>:<h1>{t("Reference")}</h1>}
      <p className="article-lead">
        {t(
          "The exact contracts, files and verification records behind the explanations.",
        )}
      </p>
      <div className="reference-filters">
        <input
          aria-label={t("Search results")}
          placeholder={t("Find a component or reference")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          aria-label={t("Reference type")}
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          <option value="">{t("All reference types")}</option>
          {kinds.map((k) => (
            <option value={k} key={k}>
              {t(k)}
            </option>
          ))}
        </select>
      </div>
      <div className="evidence-grid">
        {matches.map((n) => (
          <a
            key={n.id}
            className="evidence-card"
            href={contextualHref(lang, "reference/item/" + encodeURIComponent(n.id))}
          >
            <small>{t(classify(n))}</small>
            <strong>{n.name}</strong>
            <code>{n.resource?.path}</code>
          </a>
        ))}
      </div>
      {!matches.length && <p>{t("No documents match.")}</p>}
    </>
  );
}
