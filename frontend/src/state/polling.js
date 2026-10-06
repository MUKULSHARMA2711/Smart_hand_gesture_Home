/**
 * Runs `task` now and then every `intervalMs` after the previous run *finishes*, so a
 * slow backend never causes overlapping requests (unlike setInterval). A failing task
 * keeps the poll alive, which is how the UI recovers once the backend is back.
 * Returns `stop()`, after which no further runs are scheduled.
 */
export function startPolling(task, intervalMs, { setTimer = setTimeout, clearTimer = clearTimeout } = {}) {
  let stopped = false
  let timer = null

  const run = async () => {
    try {
      await task()
    } catch {
      // The task reports its own errors; polling continues regardless.
    } finally {
      if (!stopped) timer = setTimer(run, intervalMs)
    }
  }
  run()

  return () => {
    stopped = true
    clearTimer(timer)
  }
}
