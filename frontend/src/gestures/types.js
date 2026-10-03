/**
 * Shared gesture vocabulary. Kept in sync with the backend's `Gesture` / `Intent` enums;
 * the backend's GET /gestures/config is the source of truth for the intent mapping.
 *
 * @typedef {'THUMBS_UP'|'FIST'|'OPEN_PALM'|'ONE_FINGER'|'TWO_FINGERS'|'NEUTRAL'|'UNKNOWN'} Gesture
 *
 * @typedef {object} RecognitionResult
 * @property {Gesture} gesture
 * @property {number} confidence  0..1
 * @property {Array<{x:number,y:number,z:number}>|null} landmarks  21 normalized image landmarks, or null
 * @property {Record<string, number>} [fingers]  per-finger extension scores (0 = curled, 1 = extended)
 *
 * @typedef {object} GestureRecognizer  Anything that turns a video frame into a gesture.
 * @property {(video: HTMLVideoElement, timestampMs: number) => RecognitionResult} recognize
 * @property {(canvas: HTMLCanvasElement, result: RecognitionResult) => void} draw
 */

export const GESTURES = Object.freeze({
  THUMBS_UP: 'THUMBS_UP',
  FIST: 'FIST',
  OPEN_PALM: 'OPEN_PALM',
  ONE_FINGER: 'ONE_FINGER',
  TWO_FINGERS: 'TWO_FINGERS',
  NEUTRAL: 'NEUTRAL',
  UNKNOWN: 'UNKNOWN',
})

/** Fallback until the backend config has loaded. */
export const DEFAULT_GESTURE_INTENTS = Object.freeze({
  THUMBS_UP: 'TURN_ON',
  FIST: 'TURN_OFF',
  OPEN_PALM: 'STOP',
  ONE_FINGER: 'SELECT',
  TWO_FINGERS: 'TOGGLE',
  NEUTRAL: 'NONE',
  UNKNOWN: 'NONE',
})

export const DEFAULT_CONFIDENCE_THRESHOLD = 0.75

export function isActionable(gesture) {
  return gesture !== GESTURES.NEUTRAL && gesture !== GESTURES.UNKNOWN
}

/** @type {RecognitionResult} */
export const NO_HAND = Object.freeze({ gesture: GESTURES.NEUTRAL, confidence: 0, landmarks: null })
