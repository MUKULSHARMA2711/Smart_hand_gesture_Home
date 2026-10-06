/**
 * Power history sampled by this browser from real /home/state polls.
 * The backend keeps no energy history, so this only covers the time the page is open.
 */

export const MAX_SAMPLES = 180 // 15 minutes at the 5 s polling interval

export function appendSample(history, home, maxSamples = MAX_SAMPLES) {
  if (!home?.energy) return history
  const t = new Date(home.timestamp).getTime()
  if (!Number.isFinite(t) || (history.length && history.at(-1).t >= t)) return history
  const sample = {
    t,
    totalW: home.energy.total_power_w,
    energyKwh: home.energy.energy_kwh,
    perDevice: { ...home.energy.per_device_w },
  }
  const next = [...history, sample]
  return next.length > maxSamples ? next.slice(next.length - maxSamples) : next
}

export function summarize(history) {
  if (!history.length) return null
  const values = history.map((sample) => sample.totalW)
  return {
    current: values.at(-1),
    peak: Math.max(...values),
    average: values.reduce((sum, v) => sum + v, 0) / values.length,
    samples: history.length,
    spanMs: history.at(-1).t - history[0].t,
  }
}
