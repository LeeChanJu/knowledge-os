<!-- stage:intent -->
## Is a decision already an external change?

```diagram
“We decided to do this” → a decision record
“Apply it to the source” → a separate change request
A request does not execute itself
```

Deciding what to do differs from changing an outside system. A change request must identify its target and intended operation. Submitting it through connection tools does not grant approval authority.

<!-- stage:policy -->
## What changes are allowed?

```diagram
Requested operation and target
↓ Check the registered scope and policy
Do not execute outside that scope
```

There is a bounded Notion path, not a universal writer for every system. Read permission does not automatically grant write permission. This example is educational; this screen submits no actual changes.

<!-- stage:approve -->
## May the requesting AI approve itself?

```diagram
AI’s change request
↓ Separate human review and approval
Only the approved scope becomes eligible
```

An authorized human makes a separate decision. The agent adapter does not approve or execute. Preserve the distinction between what was requested and what was actually authorized.

<!-- stage:execute -->
## Who changes the original?

```diagram
Approved request
↓ Separately authorized executor
Allowed Notion location → inspect outcome
```

An executor with separate authority and policy performs the outside write. Attempting execution differs from confirming success at the source. Duplicate prevention and ambiguous outcomes have explicit verification limits and open findings.

<!-- stage:record -->
## What should be checked after execution?

```diagram
Record the outcome
↓ Read the source back and connect evidence
Distinguish success, failure and ambiguity
```

Connect execution records with observed source state for later inspection. Undoing a change may itself require a separately approved action; do not assume automatic recovery of every failure. This documentation site is read-only and executes nothing.

<!-- checks -->
## Explain it in your own words
```check
May an AI that can read material also edit its source?
---
Read access is not write access. Policy, separate approval and an authorized executor are required.
```
```check
Does approval guarantee success and automatic recovery of every outside operation?
---
No. Approval differs from execution outcome; ambiguity and recovery have limitations and separate procedures.
```
