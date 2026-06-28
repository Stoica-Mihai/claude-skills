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
  required: ['changeName', 'summary', 'shouldSplit', 'splitReason', 'openQuestions'],
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
- Whether the request actually splits into multiple independent changes that each deserve their own change (shouldSplit). If so, explain in splitReason.
- Any open questions a human should answer (do not block on them — list them).`,
  { label: 'explore', phase: 'Explore', schema: EXPLORE }), 'explore')

if (exploration.shouldSplit) {
  return { stopped: 'should-split', exploration }
}
const changeName = exploration.changeName

// ---- Phase 2a/2b: Create + generate artifacts via openspec-ff-change skill ----
phase('Artifacts')
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
Let it create the change and generate ALL artifacts (proposal, specs, design, tasks) needed for implementation.

Then run \`openspec validate ${changeName}\` as a standalone bash command. If it reports structural errors (missing SHALL/MUST, empty requirement bodies, missing Scenario blocks), edit the artifacts to fix them and re-run validate until it is clean.

Return the list of artifact file paths created, whether validate is clean, and any notes.`,
  { label: 'ff+validate', phase: 'Artifacts', schema: FF }), 'ff')

// ---- Phase 2c: Self-review loop (fan out one reviewer per artifact; fix; repeat until clean) ----
phase('Self-review')
const REVIEW = {
  type: 'object', additionalProperties: false,
  required: ['file', 'concerns'],
  properties: {
    file: { type: 'string' },
    concerns: { type: 'array', items: { type: 'string' } },
  },
}
let reviewPass = 0
while (reviewPass < 100) {
  reviewPass++
  const reviews = (await parallel(ff.artifactFiles.map(f => () =>
    agent(`Review the OpenSpec artifact at ${f} (change "${changeName}", root ${root}).
Read it and the sibling artifacts in the same change directory for cross-references. Report concerns only:
missing requirements/edge cases, contradictions with sibling artifacts, vague task breakdowns, technical risks in the design.
Return an empty concerns array if it is sound.`,
      { label: `review:${f.split('/').pop()}`, phase: 'Self-review', schema: REVIEW })
  ))).filter(Boolean)

  const withConcerns = reviews.filter(r => r.concerns.length)
  if (!withConcerns.length) { log(`self-review clean after ${reviewPass} pass(es)`); break }

  log(`self-review pass ${reviewPass}: ${withConcerns.length} artifact(s) with concerns`)
  await parallel(withConcerns.map(r => () =>
    agent(`Fix these concerns in the OpenSpec artifact ${r.file} (change "${changeName}", root ${root}):
${r.concerns.map((c, i) => `  ${i + 1}. ${c}`).join('\n')}
Edit only ${r.file}. After editing, run \`openspec validate ${changeName}\` and fix any structural errors you introduced.`,
      { label: `review-fix:${r.file.split('/').pop()}`, phase: 'Self-review' })
  ))
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
  required: ['completed', 'errors'],
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
  res.forEach(r => { allCompleted.push(...r.completed); allErrors.push(...r.errors) })
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
    required: ['pass', 'failures', 'gaps'],
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
  if (triage && !triage.pass && triage.failures.length) {
    await parallel(triage.failures.map(f => () =>
      agent(`A test is failing for change "${changeName}" at root ${root}: ${f}. Find the cause and fix it. Do not weaken the test to make it pass.`,
        { label: 'test:fix', phase: 'Test' })))
  }
  if (triage && triage.gaps.length) {
    await parallel(triage.gaps.map(g => () =>
      agent(`Add tests covering ${g.file} for change "${changeName}" at root ${root}. Gap: ${g.reason}. Target near-100% on this file's changed code. Edit only the test file(s) for ${g.file}.`,
        { label: `test:cover:${g.file}`, phase: 'Test' })))
  }
  testStatus = triage || { error: 'triage returned null' }
}

// ---- Phase 2f: Verify loop. Invoke openspec-verify-change skill; parse its report into findings; fan out fixes. ----
phase('Verify')
const VERIFY = {
  type: 'object', additionalProperties: false,
  required: ['clean', 'findings'],
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
let verifyPass = 0
let verifyClean = false
while (verifyPass < 100) {
  verifyPass++
  const v = must(await agent(
    `Working directory: ${root}. Invoke the Skill tool with skill name "openspec-verify-change" passing the change name "${changeName}" (so it never has to ask which change).
It returns a CRITICAL/WARNING/SUGGESTION report. Convert that report into structured findings grouped by the file each finding concerns (use the change artifact path when a finding is about an artifact rather than source). Set clean=true only if there are zero CRITICAL/WARNING/SUGGESTION items.`,
    { label: `verify:pass-${verifyPass}`, phase: 'Verify', schema: VERIFY }), 'verify')
  if (v.clean || !v.findings.length) { verifyClean = true; log(`verify clean after ${verifyPass} pass(es)`); break }
  log(`verify pass ${verifyPass}: ${v.findings.length} file(s) with findings`)
  await parallel(v.findings.map(f => () =>
    agent(`Fix these verification findings in ${f.file} (change "${changeName}", root ${root}):
${f.items.map((it, i) => `  ${i + 1}. ${it}`).join('\n')}
Fix the cause, not the symptom. Edit only ${f.file} (and its direct test if a finding requires it).`,
      { label: `verify-fix:${f.file.split('/').pop()}`, phase: 'Verify' })))
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
}
