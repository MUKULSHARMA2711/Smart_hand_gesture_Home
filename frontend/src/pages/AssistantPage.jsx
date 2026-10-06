import { useEffect, useRef, useState } from 'react'
import { ChatTurn } from '../components/assistant/ChatTurn'
import { LifecyclePipeline } from '../components/assistant/LifecyclePipeline'
import { HouseView } from '../components/house/HouseView'
import { PredictionCard } from '../components/ml/PredictionCard'
import { VoicePanel } from '../components/assistant/VoicePanel'
import { OrbStatus } from '../components/OrbStatus'
import { Panel } from '../components/Panel'
import { useAssistantContext } from '../state/AssistantContext'
import { useHomeData } from '../state/HomeDataContext'
import { describeStateChange, formatTime } from '../lib/format'

const SUGGESTIONS = [
  'Turn on the living room light',
  'Turn on the fan and set it to 70',
  'Turn off everything',
  "I'm leaving home",
  'Lock the front door',
  "What's happening in my house?",
  'How much energy are we using?',
  'Should I turn on the fan?',
  'Is anything unusual?',
]

function Composer({ sending, onSend, onTyping }) {
  const [draft, setDraft] = useState('')
  const submit = (event) => {
    event.preventDefault()
    if (!draft.trim() || sending) return
    onSend(draft)
    setDraft('')
  }
  return (
    <form onSubmit={submit} className="flex gap-2">
      <label htmlFor="assistant-input" className="sr-only">
        Message the assistant
      </label>
      <input
        id="assistant-input"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onFocus={() => onTyping?.(true)}
        onBlur={() => onTyping?.(false)}
        maxLength={1000}
        placeholder="Ask about your home or tell it what to do…"
        autoComplete="off"
        className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm focus:border-indigo-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950"
      />
      <button
        type="submit"
        disabled={sending || !draft.trim()}
        className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-400"
      >
        {sending ? 'Sending…' : 'Send'}
      </button>
    </form>
  )
}

function ProviderPanel({ status, statusError }) {
  return (
    <Panel title="AI provider">
      {statusError && <p className="text-sm text-red-700 dark:text-red-400">{statusError}</p>}
      {status && (
        <dl className="space-y-3 text-sm">
          <div className="flex items-center justify-between gap-3">
            <dt className="text-slate-500 dark:text-slate-400">Provider</dt>
            <dd className="font-mono">
              {status.provider}
              {status.model && <span className="text-slate-500 dark:text-slate-400"> · {status.model}</span>}
            </dd>
          </div>
          {status.mock && (
            <p className="rounded-lg bg-amber-50 p-2 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
              Mock mode: a deterministic rule-based planner, no LLM. Set <span className="font-mono">AI_PROVIDER=anthropic</span> to use Claude.
            </p>
          )}
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Safety</dt>
            <dd className="mt-1 text-xs text-slate-600 dark:text-slate-300">
              Every action is checked against device capabilities before it runs. Door locks change only when you
              explicitly say “lock” or “unlock”{status.security_policy?.allow_unlock ? '' : ', and unlocking is disabled'}.
            </dd>
          </div>
        </dl>
      )}
    </Panel>
  )
}

function RecentAIActions({ events, deviceNames }) {
  const aiEvents = events.filter((event) => event.source === 'ai_agent').slice(0, 8)
  return (
    <Panel title="Recent AI actions">
      {aiEvents.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No device changes by the assistant yet.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {aiEvents.map((event) => (
            <li key={event.event_id} className="flex flex-wrap justify-between gap-x-3">
              <span>
                <span className="font-medium">{deviceNames[event.device_id] ?? event.device_id}</span>
                <span className="text-slate-500 dark:text-slate-400"> · {describeStateChange(event.previous_state, event.new_state)}</span>
              </span>
              <span className="text-xs text-slate-500 tabular-nums dark:text-slate-400">{formatTime(event.timestamp)}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}

export function AssistantPage() {
  const { home, events, deviceNames, ml } = useHomeData()
  const devicesById = Object.fromEntries(home.devices.map((device) => [device.id, device]))
  const assistant = useAssistantContext()
  const scrollRef = useRef(null)
  const latestTurn = assistant.turns.at(-1)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [assistant.turns])

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <Panel title="Assistant" className="flex flex-col">
        <div ref={scrollRef} className="-mx-1 max-h-[62vh] min-h-64 overflow-y-auto px-1">
          {assistant.turns.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">
              Ask a question or tell IntelliHome what to do.
            </p>
          ) : (
            <ol className="space-y-5 pb-2" aria-live="polite">
              {assistant.turns.map((turn, index) => (
                <ChatTurn
                  key={turn.interaction_id}
                  turn={turn}
                  devicesById={devicesById}
                  deviceNames={deviceNames}
                  isLatest={index === assistant.turns.length - 1}
                  busy={assistant.sending}
                  onDecide={assistant.decide}
                />
              ))}
            </ol>
          )}
        </div>

        <div className="mt-4 space-y-3 border-t border-slate-100 pt-4 dark:border-slate-800">
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={assistant.sending}
                onClick={() => assistant.send(suggestion)}
                className="rounded-full border border-slate-300 px-3 py-1 text-xs text-slate-700 transition-colors hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                {suggestion}
              </button>
            ))}
          </div>
          <Composer sending={assistant.sending} onSend={assistant.send} onTyping={assistant.setTyping} />
          <VoicePanel deviceNames={deviceNames} />
        </div>
      </Panel>

      <div className="space-y-6">
        <section className="scene-frame h-100" aria-label="3D command visualization">
          <HouseView compact />
          <OrbStatus state={assistant.orbState} className="absolute top-4 right-4" />
        </section>
        <Panel title="Request lifecycle">
          <LifecyclePipeline
            turn={latestTurn}
            lifecycle={assistant.lifecycle}
            contextAtSend={assistant.contextAtSend}
            deviceNames={deviceNames}
          />
        </Panel>
        <PredictionCard
          prediction={ml.prediction}
          onAskAI={() => assistant.send(`Why is the ${ml.prediction?.device_name ?? 'fan'} recommended?`)}
        />
        <div className="grid gap-6 md:grid-cols-2">
          <ProviderPanel status={assistant.status} statusError={assistant.statusError} />
          <RecentAIActions events={events} deviceNames={deviceNames} />
        </div>
      </div>
    </div>
  )
}
