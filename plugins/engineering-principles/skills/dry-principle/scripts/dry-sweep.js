export const meta = {
  name: 'dry-sweep',
  description: 'Deterministic whole-repo DRY audit — exactly one agent per lens, then a merge pass',
  phases: [
    { title: 'Sweep', detail: 'six single-lens readers in parallel' },
    { title: 'Merge', detail: 'dedup + Rule-of-Three count + leverage-ranked report' },
  ],
}

const SCOPE = (args && args.scope) || (typeof args === 'string' && args) || 'the current repository'
const PATTERNS = (args && args.patternsPath) || 'the dry-principle skill references/patterns.md (read it if reachable; otherwise rely on the lens description below)'

const LENSES = [
  {
    key: 'P1-knowledge',
    title: 'Knowledge & business rules',
    q: 'if this rule, policy, or calculation changes, how many places must I edit?',
    section: 'Knowledge duplication (the real target)',
    note: 'Whole-repo lens — a business rule can live in frontend + backend + a test fixture at once.',
  },
  {
    key: 'P2-perinstance',
    title: 'Per-instance / fan-out state',
    q: 'if there were two monitors or ten rows, would this state, timer, fetch, or cache run or store twice — and does it need to?',
    section: 'Per-instance and fan-out duplication',
    note: 'Whole-repo lens. Invisible to grep — the source appears once and duplicates at RUNTIME. Flag MED/HIGH even at instance-count 1: per-instance mutable state is a latent desync bug. Look for components instantiated via Variants/Repeater/.map holding screen-independent members.',
  },
  {
    key: 'P3-magic',
    title: 'Magic values & boundary literals',
    q: 'does this literal carry meaning, and does a name for it already exist?',
    section: 'Code-level duplication (magic numbers/strings, boundary literals)',
    note: 'Whole-repo lens — a constant may already exist in a shared module. Include 0/1/-1 comparisons that ask a semantic question, and stringly-typed code ignoring an existing enum.',
  },
  {
    key: 'P4-logic',
    title: 'Repeated logic, parameters & orchestration',
    q: 'what did every caller do AROUND the interesting call, and what block got copied with one or two values changed?',
    section: 'Code-level duplication (repeated logic, parameter sprawl) and Call-site duplication',
    note: 'Whole-repo lens. Includes copied blocks, parameter sprawl, and call-site orchestration (begin/try/commit/rollback, load->auth->authorize) wrapped around a varying call.',
  },
  {
    key: 'P5-siblings',
    title: 'Cross-file siblings, wiring & symbol-label',
    q: 'do 3+ sibling files expose the same outward shape, and does any wired token reappear as a bare string or label in another file?',
    section: 'UI components, Interaction and wiring duplication, Symbol / label duplication',
    note: 'Whole-repo lens — definitionally cross-file. NEVER restrict to one directory: diff sibling interface surfaces (signals, events, props), and match typed tokens (KeyCode::Tab, route enums, flag fields) against bare string literals in other files.',
  },
  {
    key: 'P6-samefile',
    title: 'Same-file scattered & beyond-code',
    q: 'within a single file, is the same block embedded in several functions; and is config, docs, schema, or test setup duplicated beyond code?',
    section: 'Beyond code (plus same-file scattered scanning)',
    note: 'Read each file with several similarly-shaped functions (multiple format*/parse*/handle*, or all methods on a struct) and compare bodies side by side. Also config/env duplication, doc drift, schema-vs-validation, and duplicated test setup.',
  },
]

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    lens: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          knowledge: { type: 'string', description: 'what KNOWLEDGE is duplicated, not just what code looks alike' },
          severity: { type: 'string', enum: ['HIGH', 'MED', 'LOW'] },
          fix: { type: 'string' },
          occurrences: { type: 'integer', description: 'how many sites this reader found for this knowledge' },
          confidence: { type: 'string', enum: ['high', 'med', 'low'] },
        },
        required: ['file', 'knowledge', 'severity', 'fix', 'occurrences'],
      },
    },
    rejected: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          candidate: { type: 'string' },
          why: { type: 'string', description: 'the factor found by reading the real code that disqualifies the merge' },
        },
        required: ['candidate', 'why'],
      },
    },
  },
  required: ['lens', 'findings', 'rejected'],
}

const REPORT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    summary: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          knowledge: { type: 'string' },
          severity: { type: 'string', enum: ['HIGH', 'MED', 'LOW'] },
          fix: { type: 'string' },
          lenses: { type: 'array', items: { type: 'string' } },
        },
        required: ['file', 'knowledge', 'severity', 'fix', 'lenses'],
      },
    },
    topToActFirst: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ref: { type: 'string', description: 'which finding(s)' },
          why: { type: 'string', description: 'why first — leverage (subsumes others) or silent-on-drift hazard' },
        },
        required: ['ref', 'why'],
      },
    },
    rejectedNote: { type: 'string' },
  },
  required: ['summary', 'findings', 'topToActFirst'],
}

function lensPrompt(l) {
  return `You are the ${l.key} reader in a deterministic DRY audit. You own EXACTLY ONE lens. Do not look for any other kind of duplication — a different reader owns each of the others, and your single-mindedness is the point.

Scope: ${SCOPE}
Your lens: ${l.title}
The one question you ask of the code: ${l.q}
${l.note}

For worked before/after examples of this lens, read ${PATTERNS} -> "${l.section}".

Method:
- Scan the scope asking ONLY your question.
- Treat every match as a HYPOTHESIS, not a finding. Open and read each site in full, including the surrounding code, and actively try to DISPROVE it. A factor visible only in the real code often disqualifies a merge: an error path or edge case one site lacks; blocks that read alike but consume different outputs; literals that are near but not equal (-0.3 vs -0.03); a divergence that is intentional and noted in a comment, a convention, or project memory; or two things that change for different reasons.
- Apply the guardrails: Rule of Three (don't propose abstracting under three genuine occurrences), coincidental similarity, wrong-abstraction risk, YAGNI.
- Report only candidates that survived a genuine attempt to disprove them. For each, give file, line, the KNOWLEDGE that is duplicated (not just "these look alike"), a severity, a concrete fix, and how many sites you found.
- Record what you rejected and WHY, so the merge step does not re-flag it.

Return structured output per the schema.`
}

function mergePrompt(perLens) {
  return `You are the merge step of a deterministic DRY audit of ${SCOPE}. Six single-lens readers each returned findings and a rejection list. Their raw output as JSON:

${JSON.stringify(perLens, null, 2)}

Produce ONE consolidated report:
1. Cross-lens dedup: when two lenses flagged the same site, keep one entry and record both lenses in its "lenses" field.
2. Rule-of-Three across the FULL set: you are the only step that sees every lens and every region, so YOU do the counting. Drop two-instance coincidences unless they are clearly the same knowledge; surface three-across-file patterns no single reader could count alone.
3. Severity sort: per-instance / silent-desync bugs lead even at instance-count 1; merely-verbose repetition trails.
4. topToActFirst: rank by LEVERAGE — the fix that subsumes the most other findings goes first (e.g. a registry or singleton that erases many scattered literals). Put silent-on-drift hazards above cosmetic ones.
5. rejectedNote: one line summarizing what was considered and dismissed, and why.

Findings only — name the duplicated knowledge, where it lives, severity, and the concrete fix. Return structured output per the schema.`
}

phase('Sweep')
log(`DRY sweep over: ${SCOPE} — six lens agents in parallel`)
const perLens = (await parallel(
  LENSES.map(l => () => agent(lensPrompt(l), { label: l.key, phase: 'Sweep', schema: FINDINGS_SCHEMA }))
)).filter(Boolean)

phase('Merge')
log(`Merging ${perLens.reduce((n, r) => n + (r.findings ? r.findings.length : 0), 0)} raw findings across ${perLens.length} lenses`)
const report = await agent(mergePrompt(perLens), { label: 'merge', phase: 'Merge', schema: REPORT_SCHEMA })

return report
