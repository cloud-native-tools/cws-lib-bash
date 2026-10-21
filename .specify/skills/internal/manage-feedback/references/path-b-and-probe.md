# Path B — 打包上送 & Probe Injection

Owns § Path B (steps 1–6) and § Probe Injection of the feedback skill. Extracted from
`.specify/templates/commands/feedback.md`; content preserved, form re-expressed. The routing
judgment that selects Path B (or defers probe injection to an explicit request) lives
in the skill's SKILL.md (Routing flow).

## Path B — 打包上送 (Package For The Framework Upstream)

Everything the feedback points at the framework upstream. This is the sending side,
and it never sends anything itself — delivery stays manual.

**Reached automatically only from a client project.** In the framework project the
router does not select this path, because there is no upstream to deliver to — a zip
packaged here is addressed to this same repository. It stays reachable there by an
explicit `package` request (for example to hand a bundle to another maintainer, or to
reset the counter via `mark-submitted`), and the run says plainly that it was taken on
request rather than by judgment.

1. **Status view**: `--action status` (count / threshold / should_prompt)。若因阈值
   提示进入本命令:Path A 的 § Introspection 可先跑一遍再打包——建议而非强制,跳过不影响
   任何后续步骤。
2. **Summary view**: `--action list --limit 0` with filters as requested —
   `--slice <commands|skills|host-custom|...>`, `--kind <internal|external>`,
   `--disposition <processed|ignored|open>`, plus the pre-existing
   `--unit-id/--since/--contains`. Parse the `{"count": N, "matches": [...]}` envelope
   documented in the SKILL.md Routing flow's inventory step, never a bare array.
3. **Disposition**: `--action dispose --id <entry-id> --to processed|ignored` (local
   metadata only; optional `--reason`/`--ref` record provenance, e.g. from an
   introspection report).
4. **Package** (on the user's go-ahead, internal entries only): `--action package` →
   print zip path + manual-send guidance. The agent NEVER sends the zip. 若待打包条目
   带有 `introspection_ref`(已被自省覆盖),默认提议改用
   `--action package --include-introspection` 把覆盖它们的自省报告一并入包;用户可拒绝,
   拒绝不阻断打包。外部条目(`kind: external`)由引擎自动排除并只回报
   `excluded_external` 计数——它们属 Path A,永不随包上行。
5. **Post-package cleanup (hat-aware closing step of the package run)**: whether the
   packaged batch may leave the active store depends on which hat this repo wears —
   decided by the SKILL.md Routing flow's step-2 criterion, not restated here.
   - **Client project (the default)**: once the zip exists, the packaged batch no
     longer needs to live in the active store — the zip is on its way to a recipient
     that can act on it, so the zip is the record. Preview with
     `--action cleanup --package <zip|latest> --dry-run`, then run without `--dry-run`
     in the same session as packaging. Cleanup removes only entries actually inside
     that zip; `cleanup-log.md` records every removal. The zip itself STAYS under
     `.specify/memory/feedback/packages/` as the delivery artifact.
   - **Framework project**: run cleanup **only when the user's request for this same
     run also asked for `mark-submitted`** — that pairing is what states the batch is
     genuinely settled. Without a recipient (see the paragraph above), emptying the
     active store would leave the entries' only actionable form inside a zip nobody
     can deliver, and the store would no longer be able to answer `--action list`.
     When the pairing is absent, **keep the entries in the store** and list them in
     the report as **待定 (pending)**: packaged, undelivered, still actionable,
     deliberately not cleaned up.
6. **After delivery (`mark-submitted`)**: once the batch is dealt with (sent, or
   deliberately ignored) and `mark-submitted` has reset the counter, the zip has
   served its purpose — remove it from the outbox:
   `rm .specify/memory/feedback/packages/feedback-<ts>.zip`. The store, the outbox,
   and the counter all return to zero; `cleanup-log.md` plus the (already-delivered)
   zip's MANIFEST remain the audit trail.

If upstream cannot be detected, the engine offers a one-time
`--action upstream --set <repo-url>` (engine detail — do not paste the bare flag into
the user-facing line).

## Probe Injection (explicit request only)

Outside the automatic router by design: injecting a probe needs a target unit id that
cannot be inferred from repo state, so this capability runs only when the user names
it. For **client-project** custom Skills/Agents/Commands (assets the framework's own
probes never cover). Terminology — **客户项目 (Client Project)** / **框架项目
(Framework Project)** — is defined canonically in
`.specify/shared/definitions/dogfooding-definitions.md` §2 (one repo, two hats; the
flow chain framework sources → publish → install → each client project's
`.specify/`); this skill says "client project" wherever older drafts said "host
project":

1. Elicit the target unit (`custom:<owner>/<name>`), lifecycle point (default
   `wrap-up`), and a short collection-intent note (`--notes-file`).
2. Run `--action probe-inject --unit custom:<owner>/<name> --notes-file <file>` —
   writes `.specify/memory/feedback/probes/ext-<slug>.md`.
3. Verify the injection: the object appears in `--action probes` and after
   `--action map`.

External-probe feedback is **client-project-local** (the client project's own
use→feedback→iterate loop): it feeds that project's own optimization, is separately
filterable via `--kind external` (its improvement loop consumes the findings with
`--action list --kind external`), is routed by Path A, and is **never** included in
upstream packages.
