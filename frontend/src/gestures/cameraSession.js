/**
 * Camera + recognizer lifecycle for gesture control, independent of React so every
 * cleanup path can be tested.
 *
 * Whatever stage startup reaches, `stop()` (or a failure) releases everything that was
 * acquired: the camera tracks, the requestAnimationFrame loop and the video source.
 * Resources that arrive after the session ended (a camera stream that resolves after the
 * model failed, or after the user navigated away) are released immediately.
 */

const CAMERA_CONSTRAINTS = {
  video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
  audio: false,
}

function named(name, cause) {
  const error = new Error(cause?.message ?? name)
  error.name = name
  return error
}

export function describeCameraError(error) {
  switch (error?.name) {
    case 'CameraUnsupported':
      return 'Camera access is unavailable in this browser. Use a recent browser on localhost or HTTPS.'
    case 'NotAllowedError':
    case 'SecurityError':
      return 'Camera permission was denied. Allow camera access in the browser and try again.'
    case 'NotFoundError':
    case 'OverconstrainedError':
      return 'No camera was found on this device.'
    case 'NotReadableError':
      return 'The camera is already in use by another application.'
    case 'ModelLoadError':
      return `Could not load the hand-tracking model (${error.message}). Check your connection and try again.`
    case 'RecognitionFailed':
      return `Gesture recognition stopped unexpectedly (${error.message}). Try again.`
    default:
      return error?.message ? `Could not start gesture recognition: ${error.message}` : 'Could not start gesture recognition.'
  }
}

/**
 * @param {object} options
 * @param {() => Promise<import('./types').GestureRecognizer>} options.getRecognizer
 * @param {MediaDevices | undefined} options.mediaDevices
 * @param {() => HTMLVideoElement | null} options.getVideo
 * @param {() => HTMLCanvasElement | null} options.getCanvas
 * @param {(result: object, nowMs: number) => void} options.onFrame  each recognised frame
 * @param {(status: 'loading' | 'running' | 'error') => void} options.onStatus
 * @param {(message: string) => void} options.onError
 * @returns {() => void} stop
 */
export function startCameraSession({
  getRecognizer,
  mediaDevices = globalThis.navigator?.mediaDevices,
  getVideo,
  getCanvas,
  onFrame,
  onStatus,
  onError,
  requestFrame = (callback) => requestAnimationFrame(callback),
  cancelFrame = (id) => cancelAnimationFrame(id),
  now = () => performance.now(),
}) {
  let live = true // false once stopped or failed
  let stream = null
  let frameId = 0
  let lastVideoTime = -1

  const stopTracks = (mediaStream) => mediaStream?.getTracks().forEach((track) => track.stop())

  const release = () => {
    live = false
    cancelFrame(frameId)
    stopTracks(stream)
    stream = null
    const video = getVideo()
    if (video) video.srcObject = null
  }

  const fail = (error) => {
    if (!live) return // already stopped: nothing to report
    release()
    onStatus('error')
    onError(describeCameraError(error))
  }

  function loop(recognizer) {
    if (!live) return
    frameId = requestFrame(() => loop(recognizer))
    const video = getVideo()
    const canvas = getCanvas()
    if (!video || !canvas || video.readyState < 2 || video.currentTime === lastVideoTime) return
    lastVideoTime = video.currentTime

    if (canvas.width !== video.videoWidth) canvas.width = video.videoWidth
    if (canvas.height !== video.videoHeight) canvas.height = video.videoHeight

    try {
      const timestamp = now()
      const result = recognizer.recognize(video, timestamp)
      recognizer.draw(canvas, result)
      onFrame(result, timestamp)
    } catch (error) {
      // e.g. the WebGL context behind MediaPipe was lost: stop cleanly instead of throwing every frame.
      fail(named('RecognitionFailed', error))
    }
  }

  async function start() {
    onStatus('loading')
    if (!mediaDevices?.getUserMedia) {
      fail(named('CameraUnsupported'))
      return
    }
    // Track the stream as soon as it exists, so it can always be stopped.
    const streamReady = mediaDevices.getUserMedia(CAMERA_CONSTRAINTS).then((mediaStream) => {
      if (live) stream = mediaStream
      else stopTracks(mediaStream)
      return mediaStream
    })
    const recognizerReady = Promise.resolve()
      .then(getRecognizer)
      .catch((error) => {
        throw named('ModelLoadError', error)
      })

    try {
      const [recognizer] = await Promise.all([recognizerReady, streamReady])
      if (!live) return
      const video = getVideo()
      if (!video) throw new Error('The video element is not available.')
      video.srcObject = stream
      await video.play()
      if (!live) return
      onStatus('running')
      loop(recognizer)
    } catch (error) {
      fail(error)
    }
  }

  start()
  return release
}
