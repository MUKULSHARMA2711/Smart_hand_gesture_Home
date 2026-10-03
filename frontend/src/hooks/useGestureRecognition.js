import { useEffect, useRef, useState } from 'react'
import { getMediaPipeRecognizer } from '../gestures/mediapipeRecognizer'
import { GestureStabilizer } from '../gestures/stabilizer'
import { NO_HAND } from '../gestures/types'

const UI_UPDATE_INTERVAL_MS = 100 // re-render ~10×/s; drawing still runs every frame

const IDLE_LIVE = { ...NO_HAND, candidate: null, progress: 0, awaitingRelease: false }

function describeCameraError(error) {
  switch (error?.name) {
    case 'NotAllowedError':
      return 'Camera permission was denied. Allow camera access in the browser and try again.'
    case 'NotFoundError':
    case 'OverconstrainedError':
      return 'No camera was found on this device.'
    case 'NotReadableError':
      return 'The camera is already in use by another application.'
    default:
      return error?.message ? `Could not start gesture recognition: ${error.message}` : 'Could not start gesture recognition.'
  }
}

/**
 * Runs camera → recognizer → stabilizer in a requestAnimationFrame loop while `active`.
 * Calls `onCommit({gesture, confidence})` when a gesture has been held deliberately.
 * `getRecognizer` can be swapped for any implementation of the GestureRecognizer interface.
 * Changing `restartKey` restarts the camera (e.g. "Try again" after an error).
 */
export function useGestureRecognition({
  active,
  threshold,
  onCommit,
  restartKey = 0,
  getRecognizer = getMediaPipeRecognizer,
}) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const onCommitRef = useRef(onCommit)
  const stabilizerRef = useRef(new GestureStabilizer({ threshold }))
  const [status, setStatus] = useState('idle') // idle | loading | running | error
  const [error, setError] = useState(null)
  const [live, setLive] = useState(IDLE_LIVE)

  useEffect(() => {
    onCommitRef.current = onCommit
  }, [onCommit])

  // Apply threshold changes (e.g. once the backend config loads) without restarting the camera.
  useEffect(() => {
    stabilizerRef.current.threshold = threshold
  }, [threshold])

  useEffect(() => {
    if (!active) return undefined

    let cancelled = false
    let stream = null
    let frameId = 0
    let lastVideoTime = -1
    let lastUiUpdate = 0
    const stabilizer = stabilizerRef.current
    stabilizer.reset()

    const stopStream = () => stream?.getTracks().forEach((track) => track.stop())

    function loop(recognizer) {
      frameId = requestAnimationFrame(() => loop(recognizer))
      const video = videoRef.current
      const canvas = canvasRef.current
      if (!video || !canvas || video.readyState < 2 || video.currentTime === lastVideoTime) return
      lastVideoTime = video.currentTime

      if (canvas.width !== video.videoWidth) canvas.width = video.videoWidth
      if (canvas.height !== video.videoHeight) canvas.height = video.videoHeight

      const now = performance.now()
      const result = recognizer.recognize(video, now)
      recognizer.draw(canvas, result)
      const stable = stabilizer.update(result, now)

      if (stable.commit) onCommitRef.current?.(stable.commit)
      if (stable.commit || now - lastUiUpdate >= UI_UPDATE_INTERVAL_MS) {
        lastUiUpdate = now
        setLive({ ...result, ...stable })
      }
    }

    async function start() {
      setStatus('loading')
      setError(null)
      try {
        // Load the model and open the camera in parallel.
        const [recognizer, mediaStream] = await Promise.all([
          getRecognizer(),
          navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
            audio: false,
          }),
        ])
        stream = mediaStream
        if (cancelled) return stopStream()

        const video = videoRef.current
        video.srcObject = stream
        await video.play()
        if (cancelled) return stopStream()

        setStatus('running')
        loop(recognizer)
      } catch (err) {
        stopStream()
        if (!cancelled) {
          setStatus('error')
          setError(describeCameraError(err))
        }
      }
    }

    start()

    return () => {
      cancelled = true
      cancelAnimationFrame(frameId)
      stopStream()
      if (videoRef.current) videoRef.current.srcObject = null
      canvasRef.current?.getContext('2d')?.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)
      setStatus('idle')
      setLive(IDLE_LIVE)
    }
  }, [active, restartKey, getRecognizer])

  return { videoRef, canvasRef, status, error, live }
}
