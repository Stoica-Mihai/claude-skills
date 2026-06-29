export const meta = {
  name: 'opsx-task-full',
  description: 'Full autonomous OpenSpec change pipeline: explore → ff (artifacts) → validate → self-review → implement (waves) → test → verify, as one deterministic workflow. Returns a summary; the human gate (Phase 3) and archive + commit (Phase 4) stay in the calling skill because a workflow cannot pause for a human.',
  phases: [
    { title: 'Explore' },
    { title: 'Artifacts' },
    { title: 'Self-review' },
    { title: 'Implement' },
    { title: 'Test' },
    { title: 'Verify' },
  ],
}

// args (JSON or string):
// {
//   description: "<the user's request, verbatim>",
//   root: "<absolute path of the openspec project>",
//   schema: "<optional openspec schema name>",
//   test: { enabled: bool, runCmd: "...", coverageCmd: "..." }
// }
const A = typeof args === 'string' ? JSON.parse(args) : args
if (!A || !A.description || !A.root) {
  throw new Error('args.description and args.root are required')
}
const root = A.root
const must = (v, what) => { if (v == null) throw new Error(`pipeline aborted: ${what} returned null`); return v }

// Detect the test suite inside the workflow when the caller did not supply A.test,
// so the main thread does nothing before the gate except fire this workflow.
let testCfg = A.test
if (!testCfg) {
  const TEST_DETECT = {
    type: 'object', additionalProperties: false,
    required: ['enabled', 'runCmd', 'coverageCmd'],
    properties: {
      enabled: { type: 'boolean' },
      runCmd: { type: 'string' },
      coverageCmd: { type: 'string' },
    },
  }
  testCfg = await agent(
    `At project root ${root}, determine whether a test suite already exists (test dirs/files, runner config in package.json/pyproject.toml/Cargo.toml/etc.).
Return enabled=true with the exact command to run the full suite (runCmd) and a coverage command if one is obvious (coverageCmd, else ""). If no suite exists, enabled=false with empty commands.`,
    { label: 'detect-tests', phase: 'Explore', schema: TEST_DETECT }) || { enabled: false, runCmd: '', coverageCmd: '' }
}

// ---- Phase 1: Explore via the openspec-explore skill (runs non-interactively: it investigates
//      and reports; it has no mandatory user prompt, so it does not block without a human). ----
phase('Explore')
const EXPLORE = {
  type: 'object', additionalProperties: false,
  // Only the always-present fields are required. splitReason/openQuestions are
  // legitimately empty in the common case, and models DROP empty-array/optional
  // fields (especially under "there's nothing open" steering) — requiring them
  // makes the validator reject valid output and the agent retries to the cap.
  required: ['changeName', 'summary', 'shouldSplit'],
  properties: {
    changeName: { type: 'string' },
    summary: { type: 'string' },
    shouldSplit: { type: 'boolean' },
    splitReason: { type: 'string' },
    openQuestions: { type: 'array', items: { type: 'string' } },
  },
}
const exploration = must(await agent(
  `Working directory: ${root}. Invoke the Skill tool with skill name "openspec-explore", passing this to think through:
  "${A.description}"
Let it investigate the codebase (it reads code and surfaces findings; it will not block waiting for you). Do NOT write application code.

From its investigation, distill and return:
- A short kebab-case change name.
- A 2-3 sentence summary of what the change entails and where it lands in the code.
- Whether the request actually splits into multiple independent changes that each deserve their own change (shouldSplit). Include splitReason only if shouldSplit is true.
- Any open questions a human should answer (do not block on them). If there are none, omit openQuestions or return an empty list — do not invent questions to fill it.`,
  { label: 'explore', phase: 'Explore', schema: EXPLORE }), 'explore')

if (exploration.shouldSplit) {
  return { stopped: 'should-split', exploration }
}
const changeName = exploration.changeName

// ---- Phase 2a/2b: Create + generate artifacts via openspec-ff-change skill ----
phase('Artifacts')

// Lock open decisions to ONE concrete answer BEFORE artifact generation. ff lets
// each artifact author make its own "reasonable" call, so an unresolved judgment
// call gets different answers in different files — the cross-artifact contradiction
// the self-review loop then chases. Deciding once up front kills it at the source.
let lockedDecisions = []
if (exploration.openQuestions && exploration.openQuestions.length) {
  const DECIDE = {
    type: 'object', additionalProperties: false, required: ['decisions'],
    properties: {
      decisions: {
        type: 'array',
        items: {
          type: 'object', additionalProperties: false, required: ['question', 'decision'],
          properties: { question: { type: 'string' }, decision: { type: 'string' } },
        },
      },
    },
  }
  const d = await agent(
    `For the OpenSpec change "${changeName}" (root ${root}) — "${A.description}" — commit a single concrete answer to each open question below, so every artifact can agree on it. Pick the most reasonable default given the codebase; be SPECIFIC (the exact token/name/value/approach), never "either/or". These answers are binding for artifact generation.
Open questions:
${exploration.openQuestions.map((q, i) => `  ${i + 1}. ${q}`).join('\n')}`,
    { label: 'lock-decisions', phase: 'Artifacts', schema: DECIDE })
  if (d && d.decisions) {
    lockedDecisions = d.decisions
    log(`locked ${lockedDecisions.length} decision(s) before artifact generation`)
  }
}

const FF = {
  type: 'object', additionalProperties: false,
  required: ['created', 'artifactFiles', 'valid', 'validationNotes'],
  properties: {
    created: { type: 'boolean' },
    artifactFiles: { type: 'array', items: { type: 'string' } },
    valid: { type: 'boolean' },
    validationNotes: { type: 'string' },
  },
}
const ff = must(await agent(
  `Working directory: ${root}.
Invoke the Skill tool with skill name "openspec-ff-change", passing this exact input so it never has to ask the user anything:
  change name "${changeName}" for: ${A.description}
${A.schema ? `Use the openspec schema "${A.schema}".` : ''}
${lockedDecisions.length ? `These decisions are FINAL — every artifact must use exactly these answers; do not re-decide them per artifact:\n${lockedDecisions.map((x, i) => `  ${i + 1}. ${x.question} -> ${x.decision}`).join('\n')}\n` : ''}For any OTHER decision the input leaves open, make it ONCE, state it explicitly in the earliest artifact that needs it, and ensure every later artifact reads and matches that choice — never let two artifacts give different answers to the same question.
Let it create the change and generate ALL artifacts (proposal, specs, design, tasks) needed for implementation.

Then run \`openspec validate ${changeName}\` as a standalone bash command. If it reports structural errors (missing SHALL/MUST, empty requirement bodies, missing Scenario blocks), edit the artifacts to fix them and re-run validate until it is clean.

Return the list of artifact file paths created, whether validate is clean, and any notes.`,
  { label: 'ff+validate', phase: 'Artifacts', schema: FF }), 'ff')

// ---- Phase 2c: Self-review loop. Read-only reviewers fan out (blocking-only); a
// SINGLE reconciliation agent then edits ALL artifacts together. Per-file fixers
// were the failure engine: the dominant concern class is cross-artifact
// contradictions, which a one-sided "edit only this file" fixer cannot resolve —
// it documents the conflict instead, the other file still disagrees, and it gets
// re-flagged every pass. One reconciler that can touch every file fixes that. ----
phase('Self-review')
// Concerns carry a severity; only BLOCKING ones gate the loop. Minor/stylistic
// notes are logged but never trigger another pass — prose artifacts always have
// *something* a fresh reviewer could nitpick, which otherwise oscillates forever.
const REVIEW = {
  type: 'object', additionalProperties: false,
  required: ['file'],  // concerns omitted when sound — don't force the empty array
  properties: {
    file: { type: 'string' },
    concerns: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['severity', 'note'],
        properties: {
          severity: { type: 'string', enum: ['blocking', 'minor'] },
          note: { type: 'string' },
        },
      },
    },
  },
}
// Markdown self-review should converge in 1-2 rounds. Low cap + non-progress break
// stop the ping-pong; residual blockers escalate to the human gate, not silence.
const MAX_REVIEW = 5
let reviewPass = 0, prevBlocking = Infinity
let residualConcerns = []
// Minor concerns don't gate the loop, but they are NOT discarded — severity is the
// reviewer's subjective call, so an under-rated real issue would ship silently.
// Carry the latest pass's minors to the human gate as a safety net.
let minorConcerns = []
while (reviewPass < MAX_REVIEW) {
  reviewPass++
  const reviews = (await parallel(ff.artifactFiles.map(f => () =>
    agent(`Review the OpenSpec artifact at ${f} (change "${changeName}", root ${root}).
Read it and the sibling artifacts for cross-references. Report ONLY genuinely BLOCKING defects (severity "blocking"):
a contradiction between artifacts (two files specifying different answers for the same thing), a missing or
malformed requirement/scenario, or a task breakdown that cannot be implemented as written.
Mark everything else "minor": polish, "could add more detail", nice-to-haves, stylistic preferences — AND anything
that cannot be resolved by editing the artifact text, e.g. "no automated test/verification harness exists" or other
tooling that does not yet exist (those are implementation notes, not artifact defects). Do NOT cite sibling
artifacts by line number, and do NOT flag shifted/stale line references as blocking. Artifacts need not be
exhaustive; do not invent blocking concerns. Return an empty concerns array if it is sound.`,
      { label: `review:${f.split('/').pop()}`, phase: 'Self-review', schema: REVIEW })
  ))).filter(Boolean)

  const blockers = reviews.flatMap(r => (r.concerns || []).filter(c => c.severity === 'blocking').map(c => ({ file: r.file, note: c.note })))
  // Overwrite (not accumulate) so this reflects the latest artifact state, not stale minors from earlier passes.
  minorConcerns = reviews.flatMap(r => (r.concerns || []).filter(c => c.severity === 'minor').map(c => ({ file: r.file.split('/').pop(), note: c.note })))

  if (!blockers.length) { residualConcerns = []; log(`self-review clean after ${reviewPass} pass(es)${minorConcerns.length ? ` — ${minorConcerns.length} minor note(s) surfaced to the gate` : ''}`); break }
  // Not strictly fewer blockers than last round → oscillating. Escalate, don't loop.
  if (blockers.length >= prevBlocking) { residualConcerns = blockers; log(`self-review not converging (${blockers.length} blocking, prev ${prevBlocking}) — escalating residual to the human gate`); break }
  prevBlocking = blockers.length
  residualConcerns = blockers

  log(`self-review pass ${reviewPass}: reconciling ${blockers.length} blocking concern(s) across the artifact set`)
  // ONE agent edits across ALL artifacts so two-sided contradictions get a single
  // coherent answer, instead of N isolated edits that re-break each other.
  await agent(`Reconcile these BLOCKING concerns across the OpenSpec change "${changeName}" artifacts (root ${root}).
Artifact files: ${ff.artifactFiles.join(', ')}.
Concerns:
${blockers.map((b, i) => `  ${i + 1}. [${b.file.split('/').pop()}] ${b.note}`).join('\n')}
You MAY edit ANY of these files. Resolve each contradiction by choosing ONE answer and making every artifact agree
with it — do NOT add "this overrides the other file" prose, and do NOT reference sibling artifacts by line number.
Make the minimal edits that resolve the concerns; do not expand scope. Then run \`openspec validate ${changeName}\`
and fix any structural errors you introduced.`,
    { label: 'reconcile', phase: 'Self-review' })
  if (reviewPass === MAX_REVIEW) { residualConcerns = blockers; log(`self-review hit pass cap (${MAX_REVIEW}); ${blockers.length} concern(s) escalated to the human gate`) }
}

// ---- Phase 2d: Implement. Agent plans the waves; the script fans out (NOT openspec-apply, which is serial). ----
phase('Implement')
const PLAN = {
  type: 'object', additionalProperties: false,
  required: ['waves'],
  properties: {
    waves: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['title', 'groups'],
        properties: {
          title: { type: 'string' },
          groups: {
            type: 'array',
            items: {
              type: 'object', additionalProperties: false,
              required: ['label', 'files', 'tasks'],
              properties: {
                label: { type: 'string' },
                files: { type: 'array', items: { type: 'string' } },
                tasks: {
                  type: 'array',
                  items: {
                    type: 'object', additionalProperties: false,
                    required: ['num', 'text'],
                    properties: { num: { type: 'string' }, text: { type: 'string' } },
                  },
                },
                context: { type: 'string' },
              },
            },
          },
        },
      },
    },
  },
}
const plan = must(await agent(
  `Read openspec/changes/${changeName}/tasks.md and the change's other artifacts (proposal.md, design.md, specs/) at root ${root}.
Build a dependency-ordered wave plan for parallel implementation:
- Group tasks by their primary edit target (one source file per group; all tasks touching one file go in the SAME group — never split a file across groups).
- Wave 0: scaffolding/primitives every later group needs. Wave 1: independent modules (depend only on wave 0). Wave 2+: aggregators that wire earlier modules together.
- For each group include: label, the files it owns, the full text of each task it owns (copied from tasks.md), and relevant cross-references from the artifacts as context.
Return the wave plan.`,
  { label: 'plan-waves', phase: 'Implement', schema: PLAN }), 'plan')

const COMPLETED = {
  type: 'object', additionalProperties: false,
  required: ['completed'],  // errors empty on a clean wave — keep optional
  properties: {
    completed: { type: 'array', items: { type: 'string' } },
    errors: { type: 'array', items: { type: 'string' } },
  },
}
const allCompleted = []
const allErrors = []
for (const wave of plan.waves) {
  log(`${wave.title}: ${wave.groups.length} group(s)`)
  const res = (await parallel(wave.groups.map(g => () =>
    agent(`Implement tasks for OpenSpec change "${changeName}" at root ${root}.
You own tasks: ${g.tasks.map(t => t.num).join(', ')}
${g.tasks.map(t => `  ${t.num}: ${t.text}`).join('\n')}
Files you may create/edit (and NO others): ${g.files.map(f => root + '/' + f).join(', ')}
Context: ${g.context || '(none)'}
Do NOT edit tasks.md (the orchestrator owns it). Comment only on a non-obvious WHY. Return the task numbers you completed.`,
      { label: `impl:${g.label}`, phase: 'Implement', schema: COMPLETED })
  ))).filter(Boolean)
  res.forEach(r => { allCompleted.push(...(r.completed || [])); allErrors.push(...(r.errors || [])) })
}

// Mark tasks.md from completed list (single writer = one agent).
if (allCompleted.length) {
  await agent(
    `In openspec/changes/${changeName}/tasks.md (root ${root}), mark these tasks done by changing "- [ ] N.M" to "- [x] N.M" for each: ${allCompleted.join(', ')}. Edit only tasks.md.`,
    { label: 'mark-tasks', phase: 'Implement' })
}

// ---- Phase 2e: Test ----
let testStatus = { skipped: true }
if (testCfg?.enabled) {
  phase('Test')
  const TRIAGE = {
    type: 'object', additionalProperties: false,
    required: ['pass'],  // failures/gaps empty on a clean suite — keep them optional
    properties: {
      pass: { type: 'boolean' },
      failures: { type: 'array', items: { type: 'string' } },
      gaps: {
        type: 'array',
        items: {
          type: 'object', additionalProperties: false,
          required: ['file', 'reason'],
          properties: { file: { type: 'string' }, reason: { type: 'string' } },
        },
      },
    },
  }
  const triage = await agent(
    `At root ${root}, run the test suite for change "${changeName}".
Run: ${testCfg.runCmd}
Coverage: ${testCfg.coverageCmd || '(none — skip coverage)'}
Return pass=true only if the whole suite passes. List failing tests, and changed files lacking adequate coverage.`,
    { label: 'test:triage', phase: 'Test', schema: TRIAGE })
  const triageFailures = triage?.failures || []
  const triageGaps = triage?.gaps || []
  if (triage && !triage.pass && triageFailures.length) {
    await parallel(triageFailures.map(f => () =>
      agent(`A test is failing for change "${changeName}" at root ${root}: ${f}. Find the cause and fix it. Do not weaken the test to make it pass.`,
        { label: 'test:fix', phase: 'Test' })))
  }
  if (triage && triageGaps.length) {
    await parallel(triageGaps.map(g => () =>
      agent(`Add tests covering ${g.file} for change "${changeName}" at root ${root}. Gap: ${g.reason}. Target near-100% on this file's changed code. Edit only the test file(s) for ${g.file}.`,
        { label: `test:cover:${g.file}`, phase: 'Test' })))
  }
  testStatus = triage || { error: 'triage returned null' }
}

// ---- Phase 2f: Verify loop. Invoke openspec-verify-change skill; parse its report into findings; fan out fixes. ----
phase('Verify')
const VERIFY = {
  type: 'object', additionalProperties: false,
  required: ['clean'],  // findings omitted/empty when clean — don't force it
  properties: {
    clean: { type: 'boolean' },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['file', 'items'],
        properties: {
          file: { type: 'string' },
          items: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}
const MAX_VERIFY = 5
let verifyPass = 0
let verifyClean = false
let prevFindings = Infinity
while (verifyPass < MAX_VERIFY) {
  verifyPass++
  const v = must(await agent(
    `Working directory: ${root}. Invoke the Skill tool with skill name "openspec-verify-change" passing the change name "${changeName}" (so it never has to ask which change).
It returns a CRITICAL/WARNING/SUGGESTION report. Convert that report into structured findings grouped by the file each finding concerns (use the change artifact path when a finding is about an artifact rather than source). Include ONLY CRITICAL and WARNING items in findings — omit SUGGESTIONs (they are optional, not defects). Set clean=true if there are no CRITICAL or WARNING items (a SUGGESTION-only report is clean).`,
    { label: `verify:pass-${verifyPass}`, phase: 'Verify', schema: VERIFY }), 'verify')
  const findings = v.findings || []
  if (v.clean || !findings.length) { verifyClean = true; log(`verify clean after ${verifyPass} pass(es)`); break }
  const findingCount = findings.reduce((n, f) => n + f.items.length, 0)
  if (findingCount >= prevFindings) { log(`verify not converging (${findingCount} findings, prev ${prevFindings}) — stopping at pass ${verifyPass}`); break }
  prevFindings = findingCount
  log(`verify pass ${verifyPass}: ${findingCount} finding(s) across ${findings.length} file(s)`)
  await parallel(findings.map(f => () =>
    agent(`Fix these verification findings in ${f.file} (change "${changeName}", root ${root}):
${f.items.map((it, i) => `  ${i + 1}. ${it}`).join('\n')}
Fix the cause, not the symptom. Edit only ${f.file} (and its direct test if a finding requires it).`,
      { label: `verify-fix:${f.file.split('/').pop()}`, phase: 'Verify' })))
  if (verifyPass === MAX_VERIFY) log(`verify hit pass cap (${MAX_VERIFY}) with ${findingCount} finding(s) still open`)
}

return {
  changeName,
  summary: exploration.summary,
  openQuestions: exploration.openQuestions,
  artifactFiles: ff.artifactFiles,
  completed: allCompleted,
  errors: allErrors,
  testStatus,
  verifyClean,
  verifyPasses: verifyPass,
  residualConcerns,
  minorConcerns,
}
