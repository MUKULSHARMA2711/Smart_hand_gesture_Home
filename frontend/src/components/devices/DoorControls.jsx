import { StateSummary } from './StateSummary'

export function DoorControls({ device, busy, onCommand }) {
  const { is_locked: isLocked } = device.state

  return (
    <div className="space-y-4">
      <StateSummary
        primary={isLocked ? 'Locked' : 'Unlocked'}
        secondary={isLocked ? 'secured' : 'not secured'}
        active={!isLocked}
      />
      <button
        type="button"
        disabled={busy}
        onClick={() => onCommand(isLocked ? 'unlock' : 'lock')}
        className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-400"
      >
        {isLocked ? 'Unlock door' : 'Lock door'}
      </button>
    </div>
  )
}
