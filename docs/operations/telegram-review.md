# Telegram approvals

Telegram is a replaceable human-review adapter over the same Governance and Action contracts as
`knowledge-os-review`. It supports assertion, Decision, and Event Proposal approval/rejection,
and governed Action approval/rejection. It cannot execute an Action or write Cypher.
The CLI remains a local recovery path; adding Telegram does not revoke local administrator access.

## Set up

Create a dedicated bot with `@BotFather` using `/newbot`. Run from the checkout:

```sh
python -m knowledge_os.telegram_review setup \
  --principals 'human:owner,google-drive:me,notion:connection:YOUR_CONNECTION_ID' \
  --actor human:owner
```

Only supply source principals that the owner already holds. The local operator explicitly binds
those principals to the Telegram account; the chat cannot choose its identity or principals.
Enter the token at the hidden prompt. It is stored in
`~/.config/knowledge-os/telegram-review.json` with mode 600, outside Git. Do not paste it into chats.
Open the one-use link printed locally in your own Telegram account, then press Start. Possession
of that random pairing link binds your numeric user ID and private chat ID. Do not share the link.
A public username is not authentication. Existing webhooks are rejected, not automatically deleted.

Run from the checkout with its Neo4j `.env` and Git-owned configuration:

```sh
python -m knowledge_os.telegram_review run
```

Use `/pending` in the bot to check the inbox. While running, the adapter checks at approximately
25-second intervals and sends new pending reviews. Click **검토하기**, read the attached complete
payload and evidence, then **내용 확인 · 승인** or **반려**. Approval is a real governance mutation.
Action approval only records permission; the existing separately authorized executor still runs
external operations. The separate [Notion pipeline](notion-pipeline.md) connects scheduled source ingestion and extraction to this review inbox. The Telegram worker itself remains an approval adapter.

## Guarantees and limits

- Numeric owner user ID, private chat, message ID, random callback ID, and a 24-hour expiry are
  checked before accepting a decision. Initial inbox cards cannot approve without the review step.
- Full authorized payload/evidence is fetched at review and again before the decision. A digest
  mismatch forces fresh review. The existing service repeats transaction-level ACL, evidence,
  lifecycle, ontology and supersession checks; no governance rule is relaxed.
- The digest is an adapter preflight, not a new transactional expected-evidence-version contract.
  Canonical payloads are content-addressed; a concurrent source version change continues to follow
  the existing service's historical-evidence policy. Latest-only evidence approval is not claimed.
- The audit reason includes the Telegram user/chat/message IDs and review digest. State is an
  atomic owner-only JSON file containing identifiers, digests, expiry, delivery IDs and update
  offset, not source content. A lock prevents two local workers using the same state file.
- A duplicate/replayed callback cannot repeat a successful decision. If the process dies after
  graph commit but before saving state, it reads the terminal graph state before another attempt.
  Telegram delivery is at-least-once; a crash around sending can leave a duplicate card, whose
  stale button cannot approve. Source content already sent to Telegram remains there even if
  source permissions later change; subsequent decisions still recheck access.
- API failures do not print bot-token URLs. Network errors are retried. The process and Mac must
  remain running; sleep/offline delays handling. Telegram retains unreceived updates for at most
  24 hours. The adapter accepts at most 100 pending items of each kind per scan (existing service
  limit); resolve newer items to expose older items in a larger backlog.
- This is a local owner trust boundary, not multi-user SSO. Other local CLI/API/admin access is
  unchanged. Do not expose the unauthenticated Knowledge Service publicly.
- No launchd service is installed in a Documents/iCloud checkout. Existing deployment guidance
  documents TCC startup failures there; a supervised deployment requires a deliberate local
  application-data configuration/runtime arrangement.

Telegram protocol: https://core.telegram.org/bots/api
