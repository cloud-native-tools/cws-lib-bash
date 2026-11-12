# Nested (chain) runs — the four duties

Owner of reference: `SKILL.md` § Nested (chain) runs (pointer). The body states the branch;
this file carries the detail. Owner of the *rule* remains the skill-reference owner's
§ Nested (cited from `SKILL.md` § Inputs); this file is the operational shape.

A Trainee may itself be a meta-skill whose own target is the skill actually changed —
`coaching-skills improve-skills 优化 X` is caller → Trainee → **subject**. Supported per the
skill-reference owner's § Nested (owner cited under `SKILL.md` § Inputs), with four duties here:

- **The Trainee resolves the subject, not the coach.** The subject reference stays inside
  `<work>` byte-for-byte; resolving, normalizing or rewriting it in this run is a contract
  violation — it would pre-digest the work.
- **Expectation and verdict target the subject.** `OC-1` names the changed **subject** file
  set (or the Trainee's own run report), not the Trainee's files; record
  `chain: <caller> → <trainee> → <subject>` and each hop's resolved absolute path in
  `expectation.md` and `observation.md`.
- **The write lock follows the subject**, per `data-model.md` § Optimization claim: two
  runs coaching different meta-trainees at the same subject still serialize.
- **Depth is counted per perspective, in dispatch edges**: this run owns exactly one edge
  (coach → Trainee); the Trainee owns its own single edge (Trainee → subject) and MUST NOT
  open a second one. A Trainee whose flow would itself dispatch a further coaching/agent
  run stops and reports `depth-exceeded`; the coach never opens a second dispatch to
  compensate.
- **Claim before dispatch when the write rides inside it**: a nested run's subject is
  written during the dispatch, so the claim is taken before dispatching (see
  `data-model.md` § Optimization claim) — taking it after the plan would guard a write
  that already happened.
- **Guards**: subject == this skill → fail closed before the expectation (never write the
  running skill from inside its own run); Trainee cannot resolve the subject → record an
  `observation-gap` plus a deviation, never substitute the coach's own resolution.
