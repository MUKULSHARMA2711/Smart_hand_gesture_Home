import { useEffect } from 'react'
import { useVoiceAssistant } from '../../hooks/useVoiceAssistant'
import { voiceStatusLabel } from '../../lib/assistant'
import { useAssistantContext } from '../../state/AssistantContext'

const LISTENING = new Set(['wake', 'command'])

/** Hands-free voice: "Hey Nova, turn on the living room fan." */
export function VoicePanel({ deviceNames }) {
  const assistant = useAssistantContext()
  const voice = useVoiceAssistant({ send: assistant.send, deviceNames })
  const { setVoiceListening } = assistant
  const on = !['off', 'error', 'unsupported'].includes(voice.state)

  // The AI core shows "listening" while the microphone is waiting for speech.
  useEffect(() => {
    setVoiceListening(LISTENING.has(voice.state))
    return () => setVoiceListening(false)
  }, [voice.state, setVoiceListening])

  if (!voice.supported) {
    return (
      <p role="status" className="rounded-lg border border-slate-700 p-3 text-xs text-slate-400">
        Voice control needs a browser with speech recognition, such as Chrome or Edge. Typing and gestures still work.
      </p>
    )
  }

  return (
    <div className="rounded-lg border border-slate-700/80 p-3" aria-label="Voice control">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p role="status" aria-live="polite" className={`text-sm ${voice.state === 'error' ? 'text-red-300' : 'text-slate-200'}`}>
          <span aria-hidden="true">{on ? '🎙 ' : ''}</span>
          {voiceStatusLabel(voice, assistant.lifecycle.phase)}
        </p>
        <button
          type="button"
          aria-pressed={on}
          onClick={on ? voice.stop : voice.start}
          className="rounded-lg border border-cyan-400/40 px-3 py-1 text-xs font-semibold text-cyan-200 hover:bg-cyan-400/10"
        >
          {on ? 'Turn off voice' : 'Enable voice'}
        </button>
      </div>
      {on && voice.heard && <p className="mt-1 truncate text-xs text-slate-400">Heard: “{voice.heard}”</p>}
      <p className="mt-2 text-[11px] text-slate-500">
        Say “Hey Nova, …”. Speech is recognised by your browser (in Chrome and Edge, by the browser's speech
        service); only the recognised text is sent to IntelliHome. Door unlocks still need an explicit confirmation.
      </p>
    </div>
  )
}
