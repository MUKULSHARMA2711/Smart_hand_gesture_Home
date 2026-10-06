import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { startPolling } from '../polling'

describe('startPolling', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('never overlaps a slow request with the next poll (regression: setInterval stacked requests)', async () => {
    let inFlight = 0
    let maxInFlight = 0
    let calls = 0
    const slowTask = async () => {
      calls += 1
      inFlight += 1
      maxInFlight = Math.max(maxInFlight, inFlight)
      await new Promise((resolve) => setTimeout(resolve, 12_000)) // backend slower than the 5 s interval
      inFlight -= 1
    }

    const stop = startPolling(slowTask, 5000)
    await vi.advanceTimersByTimeAsync(40_000)
    stop()

    expect(maxInFlight).toBe(1)
    expect(calls).toBe(3) // 0 s, 17 s, 34 s: each poll waits for the previous one
  })

  it('keeps polling after failures, so the UI recovers when the backend returns', async () => {
    const task = vi.fn().mockRejectedValueOnce(new Error('down')).mockRejectedValueOnce(new Error('down')).mockResolvedValue('ok')

    const stop = startPolling(task, 1000)
    await vi.advanceTimersByTimeAsync(2500)
    stop()

    expect(task).toHaveBeenCalledTimes(3)
    await expect(task.mock.results[2].value).resolves.toBe('ok')
  })

  it('stops scheduling once stopped, even if a request is still in flight', async () => {
    let finish
    const task = vi.fn(() => new Promise((resolve) => (finish = resolve)))

    const stop = startPolling(task, 1000)
    stop()
    finish()
    await vi.advanceTimersByTimeAsync(10_000)

    expect(task).toHaveBeenCalledTimes(1)
  })
})
