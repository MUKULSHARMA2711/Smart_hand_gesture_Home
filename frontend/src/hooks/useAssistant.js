import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

/**
 * Conversation with the AI agent. Each turn is an AgentResponse from the backend
 * (or a pending/failed placeholder while a request is in flight).
 *
 * Lifecycle callbacks let the caller drive visualisation from real request events:
 * onSend(text) → onResponse(response) | onError(message).
 * `connected` (backend reachable) lets status and history load again after an outage.
 */
export function useAssistant({ onSend, onResponse, onError, connected = true } = {}) {
  const [status, setStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)
  const [turns, setTurns] = useState([])
  const [sending, setSending] = useState(false)
  const sendingRef = useRef(false)
  const callbacks = useRef({ onSend, onResponse, onError })
  callbacks.current = { onSend, onResponse, onError }

  const haveStatus = status != null
  useEffect(() => {
    if (!connected || haveStatus) return undefined
    let cancelled = false
    api
      .getAIStatus()
      .then((result) => {
        if (cancelled) return
        setStatus(result)
        setStatusError(null)
      })
      .catch((error) => !cancelled && setStatusError(error.message))
    api
      .getAIHistory(20)
      .then((history) => !cancelled && setTurns((current) => (current.length ? current : [...history].reverse())))
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [connected, haveStatus])

  const send = useCallback(async (message) => {
    const text = message.trim()
    if (!text || sendingRef.current) return // one request at a time: no duplicate submissions
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
          turn.interaction_id === placeholderId
            ? { ...turn, pending: false, transportError: error.message, errorCode: error.code, errorReason: error.details?.reason }
            : turn,
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
