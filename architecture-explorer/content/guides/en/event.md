A record of something that happened.

## The problem at this stage

A record of something that happened. It is one part of the larger document journey. Mixing business events with synchronization events would obscure meaning.

## Follow one study note

Yesterday the note said “under review”; today it says “review stopped”. Overwriting yesterday’s state would make yesterday’s answer impossible to explain.

## Distinguish the concept from its implementation

Follow the exact repository references below. Their presence does not constitute a fresh execution result.

Semantic Events go through Proposal/Approval and retain evidence. Operational events have a separate class and provenance.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Event** implementation, not a claim that the concept or learning stage is a separate service.

- Operational Events have exactly one Source/Document provenance parent. Source deletion observations retain source timestamps separately from local recording time.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Event** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Approved Event proposal or a source operation.

Outputs: Semantic Event reads or operational source history.

Owned data: Occurrence and recording times, participants/evidence or source parent linkage.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Observation and parsing | Preserve readable source evidence | Do not silently change the source |
| Interpretation and review | Decide what content to accept | Requires proposal and approval boundaries |

<!-- CHECKS -->

### Does finishing extraction of readable text and passages approve semantic relations?

No. Evidence preservation differs from semantic judgment. Compare a candidate against evidence and rules, then review it separately.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
