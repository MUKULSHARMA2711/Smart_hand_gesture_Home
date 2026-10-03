/**
 * MediaPipe HandLandmarker adapter. Runs entirely in the browser (WebAssembly + WebGL);
 * frames never leave the device. Implements the `GestureRecognizer` interface from
 * ./types, so a different detector or classifier can replace it without UI changes.
 */
import { DrawingUtils, HandLandmarker } from '@mediapipe/tasks-vision'
// Bundled and self-hosted by Vite, so the runtime always matches the installed package.
import wasmLoaderPath from '@mediapipe/tasks-vision/vision_wasm_internal.js?url'
import wasmBinaryPath from '@mediapipe/tasks-vision/vision_wasm_internal.wasm?url'
import { classifyHand } from './ruleClassifier'
import { NO_HAND } from './types'

const MODEL_URL =
  import.meta.env.VITE_HAND_LANDMARKER_MODEL_URL ??
  'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'

async function createLandmarker(delegate) {
  return HandLandmarker.createFromOptions(
    { wasmLoaderPath, wasmBinaryPath },
    {
      baseOptions: { modelAssetPath: MODEL_URL, delegate },
      runningMode: 'VIDEO',
      numHands: 1,
      minHandDetectionConfidence: 0.6,
      minHandPresenceConfidence: 0.6,
      minTrackingConfidence: 0.5,
    },
  )
}

/** @returns {Promise<import('./types').GestureRecognizer>} */
async function createMediaPipeRecognizer() {
  let landmarker
  try {
    landmarker = await createLandmarker('GPU')
  } catch (error) {
    console.warn('MediaPipe GPU delegate unavailable, falling back to CPU.', error)
    landmarker = await createLandmarker('CPU')
  }

  let drawingContext = null
  let drawingUtils = null

  return {
    recognize(video, timestampMs) {
      const result = landmarker.detectForVideo(video, timestampMs)
      if (!result.landmarks?.length) return NO_HAND

      const landmarks = result.landmarks[0]
      const aspectRatio = video.videoWidth && video.videoHeight ? video.videoWidth / video.videoHeight : 4 / 3
      const { gesture, confidence, fingers } = classifyHand({
        landmarks,
        worldLandmarks: result.worldLandmarks[0],
        aspectRatio,
      })
      return { gesture, confidence, landmarks, fingers }
    },

    draw(canvas, result) {
      const context = canvas.getContext('2d')
      if (context !== drawingContext) {
        drawingContext = context
        drawingUtils = new DrawingUtils(context)
      }
      context.clearRect(0, 0, canvas.width, canvas.height)
      if (!result.landmarks) return
      drawingUtils.drawConnectors(result.landmarks, HandLandmarker.HAND_CONNECTIONS, { color: '#a5b4fc', lineWidth: 3 })
      drawingUtils.drawLandmarks(result.landmarks, { color: '#4f46e5', fillColor: '#ffffff', lineWidth: 1, radius: 3 })
    },
  }
}

let recognizerPromise = null

/** Loads the model once per page and reuses it when the camera is restarted. */
export function getMediaPipeRecognizer() {
  recognizerPromise ??= createMediaPipeRecognizer().catch((error) => {
    recognizerPromise = null // allow a retry after a network failure
    throw error
  })
  return recognizerPromise
}
