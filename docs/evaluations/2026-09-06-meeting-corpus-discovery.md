# Personal meeting corpus discovery — 2026-09-06

## Purpose

The meeting-transcript adapter is already implemented and tested, but production readiness must not
be inferred from fixtures. This read-only discovery checked whether a real personal transcript
corpus was already available for an authorized ingestion run.

## Evidence inspected

- Local roots: `/Users/chanju/Documents`, `/Users/chanju/Downloads`, and
  `/Users/chanju/Desktop`
- Candidate patterns: `.vtt`, `.srt`, transcript-named text files, and meeting/회의록-named text or
  Markdown files
- Existing authorized Google Drive graph corpus: titles of all 12 current Documents under the
  configured Drive Source

The local search returned zero candidates. The Drive corpus contains architecture, ontology,
decision, SAP roadmap, agent-framework, and risk documents; none is a meeting transcript. The two
Notion Documents present at that discovery were a shared test root and its MCP round-trip child, not
meeting evidence.

After the governed Action acceptance expanded the internal connection's insert/update capability,
a new read-only Notion `/search` inventory checked whether its accessible content scope had also
changed. Searches for `미팅`, `회의`, and `meeting` returned zero candidates. A complete paginated
page inventory returned exactly three pages: the shared test root, the hosted-MCP test child, and the
governed-Action test child. Therefore no meeting page is currently shared with this API connection;
write capability did not silently broaden the source corpus.

## Decision

Do not manufacture a transcript, relabel a design document as a meeting, or claim the personal
meeting gate complete from fixtures. The next valid step is to receive or locate at least one
trusted real `.vtt` or `.srt` transcript whose source location and access scope the owner intends to
ingest, or explicitly share a trusted Notion meeting page beneath an intended ingestion root. It can
then use the existing manifest-v2 path without an architectural change.
