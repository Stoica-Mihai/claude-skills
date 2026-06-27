export const meta = {
  name: 'opsx-implement-and-test',
  description: 'Run an OpenSpec change implementation in dependency waves, then run/extend its test suite. Driven by a wave plan passed in via args.',
  phases: [
    { title: 'Implement' },
    { title: 'Test' },
  ],
}

// args shape:
// {
//   changeName: "add-foo",
//   waves: [                       // ordered; waves run sequentially, groups within a wave run in parallel
//     { title: "Wave 0 — Scaffold",
//       groups: [
//         { label: "cargo+errors",
//           files: ["Cargo.toml", "src/error.rs"],
//           tasks: [{ num: "1.1", text: "..." }, ...],
//           context: "relevant proposal/design/spec excerpts inline" }
//       ] }
//   ],
//   test: { enabled: true, runCmd: "npm test", coverageCmd: "npm test -- --coverage" }
// }

// args may arrive JSON-stringified depending on how the workflow is invoked.
const A = typeof args === 'string' ? JSON.parse(args) : args
if (!A || !Array.isArray(A.waves)) {
  throw new Error('args.waves missing — pass the wave plan built by the skill')
}

const COMPLETED = {
  type: 'object',
  additionalProperties: false,
  required: ['completed', 'errors'],
  properties: {
    completed: { type: 'array', items: { type: 'string' } },
    errors: { type: 'array', items: { type: 'string' } },
  },
}

const implementPrompt = (g) => `Implement tasks for OpenSpec change "${A.changeName}".

You own ONLY these tasks: ${g.tasks.map(t => t.num).join(', ')}
Task text (do NOT re-read tasks.md):
${g.tasks.map(t => `  ${t.num}: ${t.text}`).join('\n')}

Files you may create/edit (and NO others): ${g.files.join(', ')}
Context:
${g.context || '(none)'}

Rules:
- Do NOT edit tasks.md — the orchestrator owns it.
- Comment policy: only a comment that captures a non-obvious WHY. No restating what the code does.
- Return the task numbers you completed.`

const allCompleted = []
const allErrors = []

for (const wave of A.waves) {
  log(`${wave.title}: ${wave.groups.length} group(s)`)
  const results = await parallel(
    wave.groups.map(g => () =>
      agent(implementPrompt(g), {
        label: `impl:${g.label}`,
        phase: 'Implement',
        schema: COMPLETED,
      })
    )
  )
  results.filter(Boolean).forEach(r => {
    allCompleted.push(...r.completed)
    allErrors.push(...r.errors)
  })
  if (allErrors.length) log(`errors after ${wave.title}: ${allErrors.length}`)
}

let testStatus = { skipped: true }

if (A.test?.enabled) {
  const TRIAGE = {
    type: 'object',
    additionalProperties: false,
    required: ['pass', 'failures', 'gaps'],
    properties: {
      pass: { type: 'boolean' },
      failures: { type: 'array', items: { type: 'string' } },
      gaps: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          required: ['file', 'reason'],
          properties: { file: { type: 'string' }, reason: { type: 'string' } },
        },
      },
    },
  }

  phase('Test')
  const triage = await agent(
    `Run the test suite for change "${A.changeName}" and report results.
Run: ${A.test.runCmd}
Coverage: ${A.test.coverageCmd || '(none — skip coverage)'}
Return pass=true only if the whole suite passes. List failing tests, and list changed files that lack adequate test coverage.`,
    { label: 'test:triage', phase: 'Test', schema: TRIAGE }
  )

  if (triage && !triage.pass && triage.failures.length) {
    await parallel(triage.failures.map(f => () =>
      agent(`A test is failing for change "${A.changeName}": ${f}. Find the cause and fix it. Do not weaken the test to make it pass.`,
        { label: `test:fix`, phase: 'Test' })
    ))
  }

  if (triage && triage.gaps.length) {
    await parallel(triage.gaps.map(g => () =>
      agent(`Add tests covering ${g.file} for change "${A.changeName}". Gap: ${g.reason}. Target near-100% on this file's changed code. Edit only the test file(s) for ${g.file}.`,
        { label: `test:cover:${g.file}`, phase: 'Test' })
    ))
  }

  testStatus = triage || { error: 'triage agent returned null' }
}

return { completed: allCompleted, errors: allErrors, testStatus }
