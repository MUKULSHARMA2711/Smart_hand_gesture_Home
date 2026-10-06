import { motion } from 'motion/react'
import { describeAction, describeAssistantError } from '../../lib/assistant'

/**
 * The request lifecycle for the latest assistant turn. Stage *content* comes only from
 * the backend response (or the user's own request); the stage *timing* is the frontend
 * pacing of that response (see state/aiLifecycle.js).
 */
const STAGES = ['request', 'understanding', 'context', 'plan', 'validation', 'execution', 'result']
const LABELS = {
  request: 'User request',
  understanding: 'Understanding',
  context: 'Home context',
  plan: 'Action plan',
  validation: 'Validation',
  execution: 'Execution',
  result: 'Result',
}

/** Which stage is "active" for each lifecycle phase; earlier stages are done, later ones pending. */
const ACTIVE_STAGE = { thinking: 'understanding', planning: 'plan', executing: 'execution' }

export function stageStatus(stage, phase) {
  const active = ACTIVE_STAGE[phase]
  if (!active) return 'done' // success, error, or a finished earlier turn
  const index = STAGES.indexOf(stage)
  const activeIndex = STAGES.indexOf(active)
  return index < activeIndex ? 'done' : index === activeIndex ? 'active' : 'idle'
}

function contextSummary(home) {
  if (!home) return null
  const on = home.devices.filter((d) => d.state?.is_on).map((d) => d.name)
  const door = home.devices.find((d) => d.device_type === 'door_lock')
  return [
    `${home.devices.length} devices`,
    on.length ? `${on.join(', ')} on` : 'all appliances off',
    door ? `${door.name} ${door.state.is_locked ? 'locked' : 'unlocked'}` : null,
    home.environment ? `${home.environment.temperature_c.toFixed(1)} °C` : 'sensors unavailable',
  ]
    .filter(Boolean)
    .join(' · ')
}

function StageBody({ stage, turn, contextAtSend, deviceNames, phase }) {
  const response = turn?.pending || turn?.transportError ? null : turn
  const actions = response?.actions ?? []
  switch (stage) {
    case 'request':
      return <p className="text-slate-200">“{turn?.request}”</p>
    case 'understanding':
      if (turn?.transportError) return <p className="text-red-300">{describeAssistantError(turn).title}</p>
      return response ? <p className="text-slate-300">{response.reply}</p> : <p className="text-slate-500">Planner is working…</p>
    case 'context':
      return (
        <p className="text-slate-400">
          Built server-side from live state. Dashboard snapshot at send time: {contextSummary(contextAtSend) ?? '—'}
        </p>
      )
    case 'plan':
      if (!response) return null
      if (!response.plan_valid) return <p className="text-red-300">No valid plan: {response.errors.join('; ')}</p>
      return actions.length ? (
        <ul className="space-y-0.5 font-mono text-[11px] text-slate-300">
          {actions.map((a) => (
            <li key={a.index}>
              {a.intent ?? 'malformed'} {a.device_id ? `→ ${a.device_id}` : ''}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-slate-400">No device actions needed.</p>
      )
    case 'validation': {
      if (!response) return null
      const rejected = actions.filter((a) => a.status === 'rejected')
      return (
        <div>
          <p className="text-slate-300">
            {actions.length - rejected.length} passed · {rejected.length} rejected
          </p>
          {rejected.map((a) => (
            <p key={a.index} className="text-[11px] text-red-300">
              ✗ {describeAction(a, deviceNames)}: {a.reason}
            </p>
          ))}
        </div>
      )
    }
    case 'execution': {
      if (!response) return null
      const run = actions.filter((a) => a.status === 'executed' || a.status === 'failed' || a.status === 'answered')
      if (!run.length) return <p className="text-slate-400">Nothing executed.</p>
      return (
        <ul className="space-y-0.5 text-[12px]">
          {run.map((a) => (
            <li key={a.index} className={a.status === 'failed' ? 'text-red-300' : 'text-emerald-300'}>
              {a.status === 'failed' ? '✗' : '✓'} {describeAction(a, deviceNames)}
              {phase === 'executing' && <span className="text-slate-500"> · via CommandService</span>}
            </li>
          ))}
        </ul>
      )
    }
    case 'result':
      return response ? <p className="text-slate-200">{response.outcome}</p> : null
    default:
      return null
  }
}

const DOT = {
  done: 'bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.8)]',
  active: 'bg-cyan-300 animate-pulse shadow-[0_0_14px_rgba(103,232,249,1)]',
  idle: 'bg-slate-700',
}

export function LifecyclePipeline({ turn, lifecycle, contextAtSend, deviceNames }) {
  if (!turn) {
    return <p className="text-sm text-slate-400">Send a request to see how the agent understands, plans, validates and executes it.</p>
  }
  const hasResponse = Boolean(turn && !turn.pending)
  const phase = turn.pending ? 'thinking' : lifecycle.request === turn.request ? lifecycle.phase : 'done'
  return (
    <ol className="relative space-y-3 pl-5 text-xs">
      <span className="absolute top-1 bottom-1 left-[5px] w-px bg-gradient-to-b from-cyan-400/60 via-cyan-400/20 to-transparent" aria-hidden="true" />
      {STAGES.map((stage, i) => {
        const status = stageStatus(stage, phase)
        return (
          <motion.li
            key={`${turn.interaction_id}-${stage}`}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: status === 'idle' ? 0.45 : 1, x: 0 }}
            transition={{ delay: hasResponse ? i * 0.08 : 0, duration: 0.3 }}
            className="relative"
          >
            <span className={`absolute top-1 -left-5 h-2.5 w-2.5 rounded-full ${DOT[status]}`} aria-hidden="true" />
            <p className="text-[10px] font-semibold tracking-[0.2em] text-slate-500 uppercase">{LABELS[stage]}</p>
            {status !== 'idle' && (
              <div className="mt-0.5">
                <StageBody stage={stage} turn={turn} contextAtSend={contextAtSend} deviceNames={deviceNames} phase={phase} />
              </div>
            )}
          </motion.li>
        )
      })}
    </ol>
  )
}
