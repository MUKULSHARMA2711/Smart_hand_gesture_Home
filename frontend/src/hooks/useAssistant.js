import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

/**
 * Conversation with the AI agent. Each turn is an AgentResponse from the backend
 * (or a pending/failed placeholder while a request is in flight).
 */
export function useAssistant({ onDevicesChanged }) {
  const [status, setStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)
  const [turns, setTurns] = useState([])
  const [sending, setSending] = useState(false)
  const sendingRef = useRef(false)

  useEffect(() => {
    api.getAIStatus().then(setStatus).catch((error) => setStatusError(error.message))
    api
      .getAIHistory(20)
      .then((history) => setTurns((current) => (current.length ? current : [...history].reverse())))
      .catch(() => {})
  }, [])

  const send = useCallback(
    async (message) => {
      const text = message.trim()
      if (!text || sendingRef.current) return
      sendingRef.current = true
      setSending(true)

      const placeholderId = `pending-${Date.now()}`
      setTurns((current) => [...current, { interaction_id: placeholderId, request: text, pending: true }])
      try {
        const response = await api.aiCommand(text)
        setTurns((current) => current.map((turn) => (turn.interaction_id === placeholderId ? response : turn)))
      } catch (error) {
        setTurns((current) =>
          current.map((turn) =>
            turn.interaction_id === placeholderId ? { ...turn, pending: false, transportError: error.message } : turn,
          ),
        )
      } finally {
        sendingRef.current = false
        setSending(false)
        onDevicesChanged?.()
      }
    },
    [onDevicesChanged],
  )

  return { status, statusError, turns, sending, send }
}
