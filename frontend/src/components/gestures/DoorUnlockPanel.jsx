import { useEffect, useState } from 'react'
import { confirmationSecondsLeft } from '../../lib/assistant'
import { Panel } from '../Panel'

const RESULT = {
  confirming: { text: 'Confirming with the door…', tone: 'text-cyan-200' },
  confirmed: { text: '✓ Unlocked: confirmed by the door', tone: 'text-emerald-300' },
  cancelled: { text: 'Cancelled · the door stays locked', tone: 'text-slate-300' },
  expired: { text: 'Expired · the door stays locked', tone: 'text-slate-300' },
  failed: { text: '✗ Not unlocked', tone: 'text-red-300' },
}

/** Secure gesture unlock: four fingers requests, a pinch confirms, an open palm cancels. */
export function DoorUnlockPanel({ doorUnlock }) {
  const [now, setNow] = useState(() => Date.now())
  const pending = doorUnlock?.status === 'pending'
  useEffect(() => {
    if (!pending) return undefined
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [pending])

  if (!doorUnlock) return null
  const name = doorUnlock.deviceName ?? 'the door'
  if (pending) {
    return (
      <Panel title="Door unlock">
        <div role="group" aria-label={`Confirm unlocking ${name}`} className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3">
          <p className="text-base font-semibold text-amber-100">
            <span aria-hidden="true">🔐 </span>Unlock {name}?
          </p>
          <p className="mt-1 text-xs text-amber-200">
            Waiting for confirmation · {confirmationSecondsLeft(doorUnlock.confirmation, now)} s
          </p>
          <ul className="mt-2 space-y-1 text-sm text-slate-200">
            <li>
              <span aria-hidden="true">👌 </span>Pinch to confirm
            </li>
            <li>
              <span aria-hidden="true">✋ </span>Open palm to cancel
            </li>
          </ul>
          <p className="mt-2 text-[11px] text-slate-400">The door stays locked until the backend confirms the unlock.</p>
        </div>
      </Panel>
    )
  }
  const result = RESULT[doorUnlock.status] ?? RESULT.failed
  return (
    <Panel title="Door unlock">
      <p role="status" className={`text-sm ${result.tone}`}>
        {result.text}
      </p>
      {doorUnlock.message && <p className="mt-1 text-xs text-slate-400">{doorUnlock.message}</p>}
    </Panel>
  )
}
