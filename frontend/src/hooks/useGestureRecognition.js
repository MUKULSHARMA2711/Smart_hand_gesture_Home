import { useEffect, useRef, useState } from 'react'
import { startCameraSession } from '../gestures/cameraSession'
import { getMediaPipeRecognizer } from '../gestures/mediapipeRecognizer'
import { createPinchDetector } from '../gestures/pinch'
import { GestureStabilizer } from '../gestures/stabilizer'
import { NO_HAND } from '../gestures/types'

const UI_UPDATE_INTERVAL_MS = 100 // re-render ~10×/s; drawing still runs every frame

const IDLE_LIVE = { ...NO_HAND, candidate: null, progress: 0, awaitingRelease: false }

/**
 * Runs camera → recognizer → stabilizer in a requestAnimationFrame loop while `active`.
 * Calls `onCommit({gesture, confidence})` when a gesture has been held deliberately.
 * `getRecognizer` can be swapped for any implementation of the GestureRecognizer interface.
 * Changing `restartKey` restarts the camera (e.g. "Try again" after an error).
 * Leaving the page (or `active` becoming false) stops the camera, the loop and MediaPipe work.
 * `onPinch(event)` receives pinch start / move / end / cancel for adjustment; while a pinch
 * is forming or held, the stabilizer sees no gesture, so no other command can fire.
 */
export function useGestureRecognition({
  active,
  threshold,
  onCommit,
  onPinch,
  restartKey = 0,
  getRecognizer = getMediaPipeRecognizer,
}) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const onCommitRef = useRef(onCommit)
  const onPinchRef = useRef(onPinch)
  const pinchRef = useRef(createPinchDetector())
  const stabilizerRef = useRef(new GestureStabilizer({ threshold }))
  const [status, setStatus] = useState('idle') // idle | loading | running | error
  const [error, setError] = useState(null)
  const [live, setLive] = useState(IDLE_LIVE)

  useEffect(() => {
    onCommitRef.current = onCommit
    onPinchRef.current = onPinch
  }, [onCommit, onPinch])

  // Apply threshold changes (e.g. once the backend config loads) without restarting the camera.
  useEffect(() => {
    stabilizerRef.current.threshold = threshold
  }, [threshold])

  useEffect(() => {
    if (!active) return undefined

    const stabilizer = stabilizerRef.current
    stabilizer.reset()
    const pinch = pinchRef.current
    pinch.reset()
    setError(null)
    let lastUiUpdate = 0

    const stop = startCameraSession({
      getRecognizer,
      getVideo: () => videoRef.current,
      getCanvas: () => canvasRef.current,
      onStatus: setStatus,
      onError: setError,
      onFrame: (result, now) => {
        const pinchEvent = pinch.update(result)
        if (pinchEvent) onPinchRef.current?.(pinchEvent)
        // The stabilizer itself is unchanged; it just sees no gesture during a pinch.
        const stable = stabilizer.update(pinch.engaged || pinchEvent ? { ...result, gesture: 'UNKNOWN' } : result, now)
        if (stable.commit) onCommitRef.current?.(stable.commit)
        if (stable.commit || now - lastUiUpdate >= UI_UPDATE_INTERVAL_MS) {
          lastUiUpdate = now
          setLive({ ...result, ...stable })
        }
      },
    })

    return () => {
      stop()
      const ended = pinch.pinching
      pinch.reset()
      if (ended) onPinchRef.current?.({ type: 'cancel', y: null, confidence: 0 })
      const canvas = canvasRef.current
      canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height)
      setStatus('idle')
      setLive(IDLE_LIVE)
    }
  }, [active, restartKey, getRecognizer])

  return { videoRef, canvasRef, status, error, live }
}
