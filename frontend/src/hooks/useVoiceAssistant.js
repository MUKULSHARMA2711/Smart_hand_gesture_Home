import { useCallback, useEffect, useRef, useState } from 'react'
import { spokenSummary } from '../lib/assistant'
import { cancelSpeech, chime, createVoiceSession, getSpeechRecognition, speakText } from '../voice/voiceSession'

/**
 * Voice on top of the existing assistant: recognised text goes through `send` (the same
 * /ai/command pipeline as typing). Stops on unmount, so leaving the page never leaves a
 * microphone listener running.
 */
export function useVoiceAssistant({ send, deviceNames }) {
  const [voice, setVoice] = useState({ state: 'off', message: null, heard: '' })
  const session = useRef(null)
  const latest = useRef({ send, deviceNames })
  latest.current = { send, deviceNames }
  const supported = Boolean(getSpeechRecognition())

  const stop = useCallback(() => {
    session.current?.stop()
    session.current = null
    cancelSpeech()
  }, [])

  const start = useCallback(() => {
    stop()
    const created = createVoiceSession({
      Recognition: getSpeechRecognition(),
      speak: speakText,
      sound: chime,
      onState: (update) => setVoice((current) => ({ ...current, ...update })),
      onHeard: (heard) => setVoice((current) => ({ ...current, heard })),
      onCommand: async (text) => {
        const response = await latest.current.send(text)
        return { speech: spokenSummary(response, latest.current.deviceNames), expectsReply: Boolean(response?.confirmation) }
      },
    })
    session.current = created
    created.start()
  }, [stop])

  useEffect(() => stop, [stop])

  return { ...voice, supported, start, stop }
}
