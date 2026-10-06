import { describe, expect, it, vi } from 'vitest'
import { describeCameraError, startCameraSession } from '../cameraSession'

const flush = () => new Promise((resolve) => setTimeout(resolve, 0))

function fakeStream() {
  const track = { stopped: false, stop: vi.fn(() => (track.stopped = true)) }
  return { track, getTracks: () => [track] }
}

function deferred() {
  let resolve, reject
  const promise = new Promise((res, rej) => ((resolve = res), (reject = rej)))
  return { promise, resolve, reject }
}

/** A session wired to fakes: camera, recognizer, video/canvas and a manual frame clock. */
function harness({ mediaDevices, recognizer, getRecognizer } = {}) {
  const stream = fakeStream()
  const frames = new Map()
  let nextFrame = 1
  const video = { readyState: 4, currentTime: 0, videoWidth: 640, videoHeight: 480, srcObject: null, play: vi.fn(async () => {}) }
  const canvas = { width: 0, height: 0 }
  const rec = recognizer ?? { recognize: vi.fn(() => ({ gesture: 'THUMBS_UP', confidence: 0.9 })), draw: vi.fn() }
  const events = { statuses: [], errors: [], frames: [] }
  const camera = mediaDevices === undefined ? { getUserMedia: vi.fn(async () => stream) } : mediaDevices

  const stop = startCameraSession({
    getRecognizer: getRecognizer ?? (async () => rec),
    mediaDevices: camera,
    getVideo: () => video,
    getCanvas: () => canvas,
    onFrame: (result) => events.frames.push(result),
    onStatus: (status) => events.statuses.push(status),
    onError: (message) => events.errors.push(message),
    requestFrame: (callback) => {
      frames.set(nextFrame, callback)
      return nextFrame++
    },
    cancelFrame: (id) => frames.delete(id),
    now: () => video.currentTime * 1000,
  })

  /** Advance the video and run the pending animation frame, like the browser would. */
  const tick = () => {
    video.currentTime += 0.033
    const [id, callback] = [...frames.entries()].at(-1) ?? []
    if (!callback) return false
    frames.delete(id)
    callback()
    return true
  }
  return { stop, stream, video, recognizer: rec, events, frames, tick }
}

describe('camera session cleanup', () => {
  it('stops the camera, the frame loop and the video source when stopped while running', async () => {
    const h = harness()
    await flush()
    expect(h.events.statuses).toEqual(['loading', 'running'])
    h.tick()
    h.tick()
    const processed = h.events.frames.length
    expect(processed).toBe(3) // the first frame on start, then one per animation frame

    h.stop()

    expect(h.stream.track.stop).toHaveBeenCalled()
    expect(h.frames.size).toBe(0) // no requestAnimationFrame left scheduled
    expect(h.video.srcObject).toBeNull()
    expect(h.tick()).toBe(false)
    expect(h.recognizer.recognize).toHaveBeenCalledTimes(processed) // no MediaPipe work after leaving
  })

  it('releases a camera stream that arrives after the model failed to load (regression: camera stayed on)', async () => {
    const camera = deferred()
    const h = harness({
      mediaDevices: { getUserMedia: () => camera.promise },
      getRecognizer: async () => {
        throw new Error('model download failed')
      },
    })
    await flush()
    expect(h.events.statuses).toEqual(['loading', 'error'])
    expect(h.events.errors[0]).toMatch(/Could not load the hand-tracking model \(model download failed\)/)

    camera.resolve(h.stream) // the permission prompt is answered later
    await flush()

    expect(h.stream.track.stopped).toBe(true)
  })

  it('releases a camera stream that arrives after the user left the page', async () => {
    const camera = deferred()
    const h = harness({ mediaDevices: { getUserMedia: () => camera.promise } })
    await flush()

    h.stop()
    camera.resolve(h.stream)
    await flush()

    expect(h.stream.track.stopped).toBe(true)
    expect(h.events.statuses).toEqual(['loading']) // never "running", no error reported after leaving
    expect(h.events.errors).toEqual([])
  })

  it('stops cleanly when recognition throws mid-stream instead of failing every frame', async () => {
    const recognizer = {
      recognize: vi.fn(() => {
        throw new Error('WebGL context lost')
      }),
      draw: vi.fn(),
    }
    const h = harness({ recognizer })
    await flush()

    h.tick()

    expect(h.events.statuses.at(-1)).toBe('error')
    expect(h.events.errors).toEqual(['Gesture recognition stopped unexpectedly (WebGL context lost). Try again.'])
    expect(h.stream.track.stopped).toBe(true)
    expect(h.frames.size).toBe(0)
    expect(h.tick()).toBe(false)
  })
})

describe('camera errors', () => {
  it('explains a browser without camera access instead of crashing', async () => {
    const h = harness({ mediaDevices: null })
    await flush()
    expect(h.events.statuses).toEqual(['loading', 'error'])
    expect(h.events.errors[0]).toMatch(/^Camera access is unavailable/)
  })

  it.each([
    ['NotAllowedError', /permission was denied/],
    ['NotFoundError', /No camera was found/],
    ['NotReadableError', /already in use/],
  ])('%s → readable message, and the model is not left running', async (name, message) => {
    const error = Object.assign(new Error('x'), { name })
    const h = harness({
      mediaDevices: {
        getUserMedia: async () => {
          throw error
        },
      },
    })
    await flush()
    expect(h.events.errors[0]).toMatch(message)
    expect(h.frames.size).toBe(0)
  })

  it('has a generic fallback', () => {
    expect(describeCameraError(new Error('boom'))).toBe('Could not start gesture recognition: boom')
    expect(describeCameraError(undefined)).toBe('Could not start gesture recognition.')
  })
})
