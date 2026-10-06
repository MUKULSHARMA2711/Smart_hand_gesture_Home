import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

/**
 * Conversation with the AI agent. Each turn is an AgentResponse from the backend
 * (or a pending/failed placeholder while a request is in flight).
 *
 * Lifecycle callbacks let the caller drive visualisation from real request events:
 * onSend(text) → onResponse(response) | onError(message).
 */
export function useAssistant({ onSend, onResponse, onError } = {}) {
  const [status, setStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)
  const [turns, setTurns] = useState([])
  const [sending, setSending] = useState(false)
  const sendingRef = useRef(false)
  const callbacks = useRef({ onSend, onResponse, onError })
  callbacks.current = { onSend, onResponse, onError }

  useEffect(() => {
    api.getAIStatus().then(setStatus).catch((error) => setStatusError(error.message))
    api
      .getAIHistory(20)
      .then((history) => setTurns((current) => (current.length ? current : [...history].reverse())))
      .catch(() => {})
  }, [])

  const send = useCallback(async (message) => {
    const text = message.trim()
    if (!text || sendingRef.current) return
    sendingRef.current = true
    setSending(true)
    callbacks.current.onSend?.(text)

    const placeholderId = `pending-${Date.now()}`
    setTurns((current) => [...current, { interaction_id: placeholderId, request: text, pending: true }])
    try {
      const response = await api.aiCommand(text)
      setTurns((current) => current.map((turn) => (turn.interaction_id === placeholderId ? response : turn)))
      callbacks.current.onResponse?.(response)
    } catch (error) {
      setTurns((current) =>
        current.map((turn) =>
          turn.interaction_id === placeholderId ? { ...turn, pending: false, transportError: error.message } : turn,
        ),
      )
      callbacks.current.onError?.(error.message)
    } finally {
      sendingRef.current = false
      setSending(false)
    }
  }, [])

  return { status, statusError, turns, sending, send }
}
