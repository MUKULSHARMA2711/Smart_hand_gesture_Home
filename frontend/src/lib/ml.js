/** Presentation helpers for ML results. They format backend output; they never compute it. */

export function formatProbability(probability) {
  if (probability == null || Number.isNaN(probability)) return '—'
  return `${Math.round(probability * 100)}%`
}

export function formatWatts(watts) {
  return `${Number(watts).toFixed(1)} W`
}

/** Top reasons for a prediction, in the model's order of influence. */
export function predictionReasons(prediction, limit = 3) {
  if (!prediction) return []
  return prediction.factors
    .filter((factor) => factor.feature in prediction.reason_features)
    .slice(0, limit)
    .map((factor) => factor.description)
}

export function predictionHeadline(prediction) {
  if (!prediction) return ''
  const likely = prediction.prediction === 'ON' ? 'likely' : 'unlikely'
  return `${formatProbability(prediction.probability)} · ${likely} to be needed in the next ${prediction.horizon_minutes} min`
}

/** Device ids the backend currently flags as anomalous (recent readings + live checks). */
export function anomalousDeviceIds(report) {
  if (!report) return new Set()
  return new Set([...report.active, ...report.live.filter((r) => r.is_anomaly)].map((r) => r.device_id))
}

/** Probability per device for the 3D scene's prediction badge (only when a device is predicted ON). */
export function predictedDevices(prediction) {
  if (!prediction || prediction.prediction !== 'ON') return {}
  return { [prediction.device_id]: prediction.probability }
}

export function describeReading(result) {
  const { min, max } = result.expected_range
  return `${formatWatts(result.observed_power_watts)} observed · normal ${min.toFixed(1)}–${max.toFixed(1)} W`
}

export function formatScore(score) {
  return `${score >= 0 ? '+' : ''}${score.toFixed(3)}`
}

export function askAI(send, question) {
  window.location.hash = '#/assistant'
  send(question)
}
