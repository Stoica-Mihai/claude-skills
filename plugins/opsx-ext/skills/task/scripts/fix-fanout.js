export const meta = {
  name: 'opsx-fix-fanout',
  description: 'Fix a batch of verify/review findings, one subagent per file, in parallel. The skill runs /opsx:verify itself, then calls this with the findings; it loops until verify is clean.',
  phases: [{ title: 'Fix' }],
}

// args shape:
// {
//   changeName: "add-foo",
//   findings: [ { file: "src/x.rs", items: ["finding 1", "finding 2"] }, ... ]
// }

// args may arrive JSON-stringified depending on how the workflow is invoked.
const A = typeof args === 'string' ? JSON.parse(args) : args
if (!A || !Array.isArray(A.findings)) {
  throw new Error('A.findings missing — pass findings grouped by file')
}

const FIXED = {
  type: 'object',
  additionalProperties: false,
  required: ['file', 'fixed', 'notes'],
  properties: {
    file: { type: 'string' },
    fixed: { type: 'boolean' },
    notes: { type: 'string' },
  },
}

log(`fixing findings across ${A.findings.length} file(s)`)

const results = await parallel(A.findings.map(f => () =>
  agent(
    `Fix these findings in ${f.file} for OpenSpec change "${A.changeName}":
${f.items.map((it, i) => `  ${i + 1}. ${it}`).join('\n')}

Edit only ${f.file} (and its direct test if a finding requires it). Address every finding, including suggestions. Return fixed=true only if all are resolved.`,
    { label: `fix:${f.file}`, phase: 'Fix', schema: FIXED }
  )
))

return { results: results.filter(Boolean) }
