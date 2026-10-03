import { Panel } from '../Panel'

const GUIDE = [
  { gesture: 'THUMBS_UP', symbol: '👍', pose: 'Thumb up, other fingers curled' },
  { gesture: 'FIST', symbol: '✊', pose: 'All fingers curled, thumb tucked' },
  { gesture: 'OPEN_PALM', symbol: '✋', pose: 'All fingers spread' },
  { gesture: 'ONE_FINGER', symbol: '☝️', pose: 'Index finger up' },
  { gesture: 'TWO_FINGERS', symbol: '✌️', pose: 'Index and middle fingers up' },
]

const INTENT_EFFECTS = {
  TURN_ON: 'Turn on (locks a door)',
  TURN_OFF: 'Turn off (unlocks a door)',
  STOP: 'Safe state: off, or locked',
  SELECT: 'Next device',
  TOGGLE: 'Flip on/off or lock/unlock',
}

export function GestureGuide({ intents, blockedActions }) {
  return (
    <Panel title="Gestures">
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">
        {GUIDE.map(({ gesture, symbol, pose }) => (
          <li key={gesture} className="flex items-center gap-3 py-2 first:pt-0 last:pb-0">
            <span className="w-8 text-2xl" aria-hidden="true">
              {symbol}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium">{pose}</span>
              <span className="block text-xs text-slate-500 dark:text-slate-400">{INTENT_EFFECTS[intents[gesture]]}</span>
            </span>
            <span className="font-mono text-xs text-slate-600 dark:text-slate-300">{intents[gesture]}</span>
          </li>
        ))}
      </ul>
      {blockedActions.length > 0 && (
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          For safety, gestures cannot trigger: <span className="font-mono">{blockedActions.join(', ')}</span>.
        </p>
      )}
    </Panel>
  )
}
