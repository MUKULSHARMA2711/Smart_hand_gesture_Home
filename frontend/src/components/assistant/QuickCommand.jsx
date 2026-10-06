import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { useAssistantContext } from '../../state/AssistantContext'

/** Compact "ask the house" bar overlaid on the 3D view; same conversation as the AI page. */
export function QuickCommand() {
  const { send, sending, turns, setTyping } = useAssistantContext()
  const [draft, setDraft] = useState('')
  const latest = turns.at(-1)

  const submit = (event) => {
    event.preventDefault()
    if (!draft.trim() || sending) return
    send(draft)
    setDraft('')
  }

  return (
    <div className="pointer-events-auto space-y-2">
      <AnimatePresence mode="wait">
        {latest && (
          <motion.p
            key={latest.interaction_id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="max-w-2xl rounded-xl border border-cyan-400/15 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 backdrop-blur"
          >
            <span className="font-semibold text-cyan-300">AI · </span>
            {latest.pending ? 'Planning…' : latest.transportError ? latest.transportError : `${latest.reply} `}
            {!latest.pending && latest.outcome && <span className="text-slate-500">({latest.outcome})</span>}
          </motion.p>
        )}
      </AnimatePresence>
      <form onSubmit={submit} className="flex max-w-2xl gap-2">
        <label htmlFor="quick-command" className="sr-only">
          Ask IntelliHome
        </label>
        <input
          id="quick-command"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onFocus={() => setTyping(true)}
          onBlur={() => setTyping(false)}
          maxLength={1000}
          autoComplete="off"
          placeholder="Ask IntelliHome… e.g. “Turn on the living room light”"
          className="command-input min-w-0 flex-1"
        />
        <button type="submit" disabled={sending || !draft.trim()} className="command-button">
          {sending ? '…' : 'Send'}
        </button>
      </form>
    </div>
  )
}
