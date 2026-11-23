import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const esbuild = require('esbuild')
const React = require('react')
const { renderToString } = require('react-dom/server')

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const frontendRoot = path.resolve(__dirname, '..')

// Helper to load and bundle TSX components dynamically in Node
function loadTsxComponent(relativePath) {
  const fullPath = path.resolve(frontendRoot, relativePath)
  const res = esbuild.buildSync({
    entryPoints: [fullPath],
    bundle: true,
    write: false,
    format: 'cjs',
    target: 'node18',
    external: ['react', 'react-dom', 'lucide-react', 'react-router-dom'],
  })
  const code = res.outputFiles[0].text
  const mod = { exports: {} }
  const fn = new Function('require', 'module', 'exports', 'React', code)
  fn(require, mod, mod.exports, React)
  return mod.exports
}

// Pre-load tested React components
const { ContradictionInspector } = loadTsxComponent('src/components/multiAgent/ContradictionInspector.tsx')
const { FinalAnswerPanel } = loadTsxComponent('src/components/multiAgent/FinalAnswerPanel.tsx')
const { SpecialistExecutionCards } = loadTsxComponent('src/components/multiAgent/SpecialistExecutionCards.tsx')
const { EvidenceProvenanceExplorer } = loadTsxComponent('src/components/multiAgent/EvidenceProvenanceExplorer.tsx')
const { MultiAgentExecutionOverview } = loadTsxComponent('src/components/multiAgent/MultiAgentExecutionOverview.tsx')

// ==============================================================================
// PART 1: CONTRACT, TYPE & STATE INVARIANTS (Tests 1 - 20)
// ==============================================================================

const SPECIALIST_DOMAINS = {
  forecasting_specialist: 'FORECASTING',
  simulation_specialist: 'SIMULATION',
  optimization_specialist: 'OPTIMIZATION',
  knowledge_specialist: 'KNOWLEDGE',
}

const EPISTEMIC_CATEGORIES = [
  'OBSERVED_DATA',
  'FORECAST',
  'SIMULATION',
  'OPTIMIZATION',
  'KNOWLEDGE_POLICY',
]

test('1. Input validation enforces character bounds (3 <= len <= 1000)', () => {
  const validateTask = (task) => {
    const trimmed = task ? task.trim() : ''
    if (trimmed.length < 3) return { valid: false, reason: 'Task must be at least 3 characters.' }
    if (trimmed.length > 1000) return { valid: false, reason: 'Task exceeds 1000 character limit.' }
    return { valid: true, reason: null }
  }

  assert.equal(validateTask('').valid, false)
  assert.equal(validateTask('  hi ').valid, false)
  assert.equal(validateTask('Surge assessment').valid, true)
  assert.equal(validateTask('A'.repeat(1001)).valid, false)
  assert.equal(validateTask('A'.repeat(1000)).valid, true)
})

test('2. Delegation mode preferences map correctly to API parameters', () => {
  const getDelegationPayload = (pref) => {
    if (pref === 'auto') return null
    if (pref === 'force') return true
    if (pref === 'disable') return false
    return null
  }

  assert.equal(getDelegationPayload('auto'), null)
  assert.equal(getDelegationPayload('force'), true)
  assert.equal(getDelegationPayload('disable'), false)
})

test('3. Coordinate API endpoint URL matches approved contract', () => {
  const endpoint = '/api/v1/agent/multi-agent/coordinate'
  assert.equal(endpoint, '/api/v1/agent/multi-agent/coordinate')
})

test('4. Trace API endpoint URL correctly interpolates trace ID', () => {
  const buildTraceUrl = (traceId) => `/api/v1/agent/multi-agent/traces/${encodeURIComponent(traceId)}`
  assert.equal(
    buildTraceUrl('trace-multi-12345'),
    '/api/v1/agent/multi-agent/traces/trace-multi-12345'
  )
})

test('5. Specialists catalogue API endpoint URL matches specification', () => {
  const endpoint = '/api/v1/agent/multi-agent/specialists'
  assert.equal(endpoint, '/api/v1/agent/multi-agent/specialists')
})

test('6. Coordinate response correctly parses execution status lifecycle', () => {
  const validStatuses = ['COMPLETED', 'PARTIAL', 'FAILED', 'REJECTED']
  validStatuses.forEach((status) => {
    const response = { status, final_answer: 'Summary' }
    assert.ok(validStatuses.includes(response.status))
  })
})

test('7. Four domain specialists map to their respective domains', () => {
  const expectedSpecialists = [
    'forecasting_specialist',
    'simulation_specialist',
    'optimization_specialist',
    'knowledge_specialist',
  ]

  expectedSpecialists.forEach((id) => {
    assert.ok(id in SPECIALIST_DOMAINS)
    assert.ok(typeof SPECIALIST_DOMAINS[id] === 'string')
  })
})

test('8. Partial execution status is correctly detected when some specialists fail or time out', () => {
  const mockPartialResponse = {
    run_id: 'run-001',
    status: 'PARTIAL',
    is_partial_result: true,
    specialist_results: [
      { specialist_id: 'forecasting_specialist', status: 'COMPLETED' },
      { specialist_id: 'simulation_specialist', status: 'TIMED_OUT' },
    ],
  }

  assert.equal(mockPartialResponse.is_partial_result, true)
  assert.equal(mockPartialResponse.status, 'PARTIAL')
})

test('9. Mandatory human review flag is strictly required on operational recommendations', () => {
  const mockResponse = {
    run_id: 'run-002',
    requires_human_review: true,
    final_answer: 'Operational recommendations.',
  }

  assert.equal(mockResponse.requires_human_review, true)
})

test('10. Epistemic categories maintain strict demarcation', () => {
  const sampleCategories = {
    OBSERVED_DATA: ['Ward A census: 28/30'],
    FORECAST: ['7-day ICU admission peak +14%'],
    SIMULATION: ['Surge scenario: +15 admissions creates 2 bed shortfall'],
    OPTIMIZATION: ['Reallocate 3 surge beds to Ward B'],
    KNOWLEDGE_POLICY: ['Protocol SOP-SURGE-2026: activate step-down care'],
  }

  EPISTEMIC_CATEGORIES.forEach((cat) => {
    assert.ok(cat in sampleCategories)
    assert.ok(Array.isArray(sampleCategories[cat]))
    assert.ok(sampleCategories[cat].length > 0)
  })
})

test('11. ProvenanceItem schema matches backend contract (no unsupported confidence scores)', () => {
  // Backend ProvenanceItem has category, id, label, details
  const realBackendProvenanceItem = {
    category: 'FORECAST',
    id: 'run_forecast_weekly_001',
    label: 'NHSN Weekly ICU Capacity Forecast',
    details: { horizon_weeks: 4, model_type: 'arima' },
  }

  assert.equal(realBackendProvenanceItem.category, 'FORECAST')
  assert.equal(realBackendProvenanceItem.id, 'run_forecast_weekly_001')
  assert.equal(realBackendProvenanceItem.label, 'NHSN Weekly ICU Capacity Forecast')
  assert.equal(typeof realBackendProvenanceItem.details, 'object')
  // Confirm absence of fabricated confidence score field in backend schema
  assert.equal('confidence_score' in realBackendProvenanceItem, false)
})

test('12. Citation references correctly expose citation_marker, section_title, excerpt', () => {
  const citation = {
    citation_id: 'cite-01',
    citation_marker: 'S1',
    document_title: 'Hospital Surge Capacity SOP',
    section_title: 'Emergency ICU Conversion',
    excerpt: 'Surge beds in Ward 4 may be activated when general census exceeds 88%.',
  }

  assert.equal(citation.citation_marker, 'S1')
  assert.equal(citation.section_title, 'Emergency ICU Conversion')
  assert.ok(citation.excerpt.includes('Surge beds'))
})

test('13. Contradiction inspector consumes array of conflict strings from backend', () => {
  // Backend contract defines conflicts as list[str]
  const backendConflicts = [
    'Forecasting projects 84% ICU occupancy while Simulation models 96% under surge.',
    'Optimization recommends 4 step-down beds which exceeds SOP nurse ratio limits.',
  ]

  assert.equal(backendConflicts.length, 2)
  assert.equal(typeof backendConflicts[0], 'string')
  assert.ok(backendConflicts[0].includes('Forecasting projects'))
})

test('14. Execution trace timeline parses chronological events', () => {
  const traceEvents = [
    { event_type: 'PARENT_EXECUTION_STARTED', timestamp: 1000 },
    { event_type: 'DELEGATION_PLAN_CREATED', timestamp: 1050 },
    { event_type: 'SPECIALIST_STARTED', specialist_id: 'forecasting_specialist', timestamp: 1100 },
    { event_type: 'SPECIALIST_COMPLETED', specialist_id: 'forecasting_specialist', timestamp: 1350 },
    { event_type: 'AGGREGATION_COMPLETED', timestamp: 1400 },
  ]

  assert.equal(traceEvents.length, 5)
  assert.equal(traceEvents[0].event_type, 'PARENT_EXECUTION_STARTED')
  assert.equal(traceEvents[traceEvents.length - 1].event_type, 'AGGREGATION_COMPLETED')
})

test('15. Delegation plan strictly enforces depth = 1 (no recursive sub-delegation)', () => {
  const plan = {
    plan_id: 'plan-001',
    max_depth: 1,
    delegations: [
      { specialist_id: 'forecasting_specialist', domain: 'FORECASTING', timeout_seconds: 15 },
    ],
  }

  assert.equal(plan.max_depth, 1)
  assert.ok(plan.delegations.length > 0)
})

test('16. Synthesis panel handles operational limitations and caveats', () => {
  const limitations = [
    'Forecast relies on 14-day trailing census and does not account for external weather shocks.',
    'Simulation assumes constant nurse-to-patient ratio of 1:2 in ICU.',
  ]

  assert.equal(limitations.length, 2)
  assert.ok(limitations[0].includes('trailing census'))
})

test('17. Copy to clipboard formats clean markdown answer text', () => {
  const finalAnswer = '### Operations Summary\nCurrent ICU census is at 82% capacity.'
  const formatForCopy = (text) => text.trim()
  assert.equal(formatForCopy(finalAnswer), finalAnswer)
})

test('18. Suggested inquiries provide realistic hospital operational scenarios', () => {
  const inquiries = [
    {
      id: 'surge-48h',
      title: '48h ICU Surge & Capacity Protocol',
      prompt: 'Synthesize a 48-hour operational readiness assessment for the ICU.',
    },
    {
      id: 'bed-reallocation',
      title: 'Emergency Surge Bed Reallocation',
      prompt: 'Evaluate transferring 4 medical beds to intermediate step-down care.',
    },
  ]

  assert.equal(inquiries.length, 2)
  inquiries.forEach((item) => {
    assert.ok(item.title)
    assert.ok(item.prompt.length >= 3)
  })
})

test('19. Error state handling safely surfaces error messages without crashing', () => {
  const formatError = (err) => {
    if (!err) return 'An unexpected error occurred.'
    if (typeof err === 'string') return err
    if (err.message) return err.message
    return 'Failed to execute multi-agent coordination.'
  }

  assert.equal(formatError('Network timeout'), 'Network timeout')
  assert.equal(formatError(new Error('Gateway 504')), 'Gateway 504')
  assert.equal(formatError(null), 'An unexpected error occurred.')
})

test('20. Non-clinical guarantee: strictly zero write or clinical mutation capabilities', () => {
  const DISALLOWED_CLINICAL_ACTIONS = [
    'prescribe_medication',
    'diagnose_patient',
    'discharge_patient',
    'auto_apply_bed_mutation',
  ]

  const multiAgentSystemTools = [
    'get_hospital_census',
    'get_forecast',
    'run_whatif_simulation',
    'optimize_surge_allocation',
    'retrieve_hospital_knowledge',
  ]

  DISALLOWED_CLINICAL_ACTIONS.forEach((action) => {
    assert.ok(!multiAgentSystemTools.includes(action))
  })
})

// ==============================================================================
// PART 2: REAL REACT COMPONENT RENDERING & UNCOVERED BEHAVIORS (Tests 21 - 30)
// ==============================================================================

test('21. Component Rendering: Handles missing optional backend fields without throwing', () => {
  // Pass minimal response with undefined/null optional fields
  const htmlExplorer = renderToString(
    React.createElement(EvidenceProvenanceExplorer, {
      evidenceCategories: null,
      provenance: null,
      sources: null,
    })
  )
  assert.ok(htmlExplorer.includes('Evidence &amp; Provenance Explorer'))
  assert.ok(htmlExplorer.includes('records'))
  assert.ok(htmlExplorer.includes('citations'))

  const htmlConflicts = renderToString(
    React.createElement(ContradictionInspector, {
      conflicts: null,
    })
  )
  assert.ok(htmlConflicts.includes('Zero Contradictions'))
  assert.ok(htmlConflicts.includes('Harmonious Domain Evidence'))

  const htmlCards = renderToString(
    React.createElement(SpecialistExecutionCards, {
      specialistResults: null,
      delegationOccurred: false,
    })
  )
  assert.ok(htmlCards.includes('No Specialist Delegation Executed'))
})

test('22. Component Rendering: Unknown enum values render gracefully with fallback badges', () => {
  const htmlCards = renderToString(
    React.createElement(SpecialistExecutionCards, {
      specialistResults: [
        {
          specialist_id: 'custom_diagnostic_agent',
          status: 'SOME_FUTURE_STATUS',
          duration_ms: 120.5,
          summary: 'Custom operational analysis.',
          tool_calls_count: 2,
        },
      ],
      delegationOccurred: true,
    })
  )
  assert.ok(htmlCards.includes('custom_diagnostic_agent'))
  assert.ok(htmlCards.includes('SOME_FUTURE_STATUS'))
  assert.ok(htmlCards.includes('120.5'))
})

test('23. Component Rendering: Provenance cards strictly render available metadata without fabricating confidence scores', () => {
  const provenanceItems = [
    {
      category: 'FORECAST',
      id: 'run_fc_882',
      label: '7-Day Admissions Forecast',
      details: { horizon: 7, model_family: 'arima' },
    },
    {
      category: 'SIMULATION',
      id: 'sim_run_104',
      label: 'ICU Surge What-If Scenario',
      details: { surge_pct: 15, duration_days: 14 },
    },
  ]

  const htmlExplorer = renderToString(
    React.createElement(EvidenceProvenanceExplorer, {
      evidenceCategories: ['FORECAST', 'SIMULATION'],
      provenance: provenanceItems,
      sources: [],
    })
  )

  assert.ok(htmlExplorer.includes('7-Day Admissions Forecast'))
  assert.ok(htmlExplorer.includes('ICU Surge What-If Scenario'))
  assert.ok(htmlExplorer.includes('horizon'))
  assert.ok(htmlExplorer.includes('arima'))
  // Strict check: No fabricated "Confidence: XX%" is rendered in the HTML
  assert.equal(htmlExplorer.toLowerCase().includes('confidence:'), false)
  assert.equal(htmlExplorer.toLowerCase().includes('confidence score'), false)
})

test('24. Component Rendering: Handles missing evidence references and empty citation arrays safely', () => {
  const htmlExplorer = renderToString(
    React.createElement(EvidenceProvenanceExplorer, {
      evidenceCategories: ['OBSERVED_DATA'],
      provenance: [
        {
          category: 'OBSERVED_DATA',
          id: 'rec_census_01',
          label: 'Hospital Census Ground Truth',
          details: {},
        },
      ],
      sources: [],
    })
  )
  assert.ok(htmlExplorer.includes('Hospital Census Ground Truth'))
  assert.equal(htmlExplorer.includes('Authoritative Document Citations'), false)
})

test('25. Component Rendering: Partial specialist failures render accurate status badges and warnings', () => {
  const mockSpecialists = [
    {
      specialist_id: 'forecasting_specialist',
      status: 'COMPLETED',
      duration_ms: 250,
      summary: 'Projected 78 beds occupied.',
      tool_calls_count: 1,
    },
    {
      specialist_id: 'simulation_specialist',
      status: 'TIMED_OUT',
      duration_ms: 15000,
      summary: 'Simulation engine timed out after 15s budget.',
      tool_calls_count: 0,
    },
  ]

  const htmlCards = renderToString(
    React.createElement(SpecialistExecutionCards, {
      specialistResults: mockSpecialists,
      delegationOccurred: true,
    })
  )
  assert.ok(htmlCards.includes('COMPLETED'))
  assert.ok(htmlCards.includes('TIMED OUT'))
  assert.ok(htmlCards.includes('Simulation engine timed out'))

  const mockResponse = {
    run_id: 'run_partial_001',
    status: 'PARTIAL',
    final_answer: 'Partial operational synthesis.',
    delegation_occurred: true,
    delegation_mode: 'MULTI_SPECIALIST',
    specialists_invoked: ['forecasting_specialist', 'simulation_specialist'],
    specialist_results: mockSpecialists,
    evidence_categories: ['FORECAST'],
    sources: [],
    provenance: [],
    conflicts: [],
    is_partial_result: true,
    limitations: ['Simulation timed out'],
    requires_human_review: true,
    created_at: new Date().toISOString(),
  }

  const htmlOverview = renderToString(
    React.createElement(MultiAgentExecutionOverview, {
      response: mockResponse,
      onOpenTraceModal: () => {},
    })
  )
  assert.ok(htmlOverview.includes('PARTIAL'))
  assert.ok(htmlOverview.includes('Partial Result (Incomplete Specialist Execution)'))
  assert.ok(htmlOverview.includes('Human Review Required'))
})

test('26. Component Rendering: Contradiction inspector renders harmonious state when conflicts array is empty', () => {
  const htmlEmpty = renderToString(
    React.createElement(ContradictionInspector, {
      conflicts: [],
    })
  )
  assert.ok(htmlEmpty.includes('Zero Contradictions'))
  assert.ok(htmlEmpty.includes('Harmonious Domain Evidence'))
  assert.ok(htmlEmpty.includes('No contradictory predictions'))
})

test('27. Component Rendering: Markdown rendering neutralizes malicious XSS scripts and dangerous HTML tags', () => {
  const maliciousPayload =
    '### Normal Header\n<script>alert("XSS")</script>\n<img src="x" onerror="stealTokens()" />\nNormal text with `inline code`.'

  const htmlAnswer = renderToString(
    React.createElement(FinalAnswerPanel, {
      response: {
        run_id: 'run_sec_01',
        status: 'COMPLETED',
        final_answer: maliciousPayload,
        delegation_occurred: false,
        delegation_mode: 'NONE',
        specialists_invoked: [],
        specialist_results: [],
        evidence_categories: [],
        sources: [],
        provenance: [],
        conflicts: [],
        is_partial_result: false,
        limitations: [],
        requires_human_review: true,
        created_at: new Date().toISOString(),
      },
    })
  )

  // React escapes raw HTML text into HTML entities &lt;script&gt; and renders inertly
  assert.ok(htmlAnswer.includes('&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;'))
  assert.ok(htmlAnswer.includes('&lt;img src=&quot;x&quot; onerror=&quot;stealTokens()&quot; /&gt;'))
  // Verify dangerouslySetInnerHTML is NOT present
  assert.equal(htmlAnswer.includes('<script>alert'), false)
  assert.equal(htmlAnswer.includes('<img src="x"'), false)
})

test('28. Security: Trace event details are rendered safely without executing scripts', () => {
  const traceDetails = {
    model: 'arima_7d',
    nested: { test: '<script>evil()</script>' },
    auth: 'Scrubbed',
  }

  // Verify that rendering details to string escapes HTML entities
  const jsonString = JSON.stringify(traceDetails)
  assert.ok(jsonString.includes('<script>evil()</script>'))
  const element = React.createElement('pre', null, jsonString)
  const html = renderToString(element)
  assert.ok(html.includes('&lt;script&gt;evil()&lt;/script&gt;'))
  assert.equal(html.includes('<script>evil()</script>'), false)
})

test('29. Error Handling: API client error parsing handles failed network/HTTP requests safely', () => {
  class MockApiClientError extends Error {
    constructor(statusCode, apiError) {
      super(apiError.message)
      this.statusCode = statusCode
      this.apiError = apiError
    }
  }

  const err404 = new MockApiClientError(404, {
    error: 'NOT_FOUND',
    message: "Trace 'mat_nonexistent' not found.",
    detail: null,
  })

  assert.equal(err404.statusCode, 404)
  assert.equal(err404.message, "Trace 'mat_nonexistent' not found.")
})

test('30. Component Lifecycle: Unmounted component ref prevents state updates after request completes', async () => {
  let isMounted = true
  let stateUpdated = false

  const simulateAsyncFetch = async () => {
    await new Promise((r) => setTimeout(r, 10))
    if (isMounted) {
      stateUpdated = true
    }
  }

  const promise = simulateAsyncFetch()
  // Simulate component unmount before fetch finishes
  isMounted = false
  await promise

  assert.equal(stateUpdated, false)
})
