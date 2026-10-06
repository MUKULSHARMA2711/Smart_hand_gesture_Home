/**
 * Merges the three real activity sources (device events, gesture events, AI interactions)
 * into one time-ordered stream for the observability console. Nothing is invented.
 */

export const SOURCE_TAGS = {
  frontend: 'DASHBOARD',
  gesture: 'GESTURE',
  ai_agent: 'AI AGENT',
  automation: 'AUTOMATION',
  mqtt: 'MQTT',
  ml: 'ML',
}

const ACTION_RESULTS = {
  turn_on: () => 'ON',
  turn_off: () => 'OFF',
  lock: () => 'LOCKED',
  unlock: () => 'UNLOCKED',
  set_brightness: (v) => `BRIGHTNESS ${v}%`,
  set_speed: (v) => `SPEED ${v}%`,
  set_temperature: (v) => `TARGET ${v} °C`,
}

export function deviceEventLine(event, deviceNames = {}) {
  const name = (deviceNames[event.device_id] ?? event.device_id).toUpperCase()
  const result = ACTION_RESULTS[event.action]?.(event.value) ?? event.action.toUpperCase()
  return `${name} → ${result}`
}

/** "LIVING ROOM FAN → ENERGY ANOMALY 170.0 W (normal 34.6–42.5 W)" from a real ML event. */
export function anomalyEventLine(event, deviceNames = {}) {
  const name = (deviceNames[event.device_id] ?? event.device_id).toUpperCase()
  const range = event.details?.expected_range
  const normal = range ? ` (normal ${range.min.toFixed(1)}–${range.max.toFixed(1)} W)` : ''
  return `${name} → ENERGY ANOMALY ${Number(event.value).toFixed(1)} W${normal}`
}

export function buildActivityFeed({ deviceEvents = [], gestureEvents = [], aiInteractions = [], deviceNames = {} }) {
  const entries = [
    ...deviceEvents.map((event) =>
      event.event_type === 'energy_anomaly'
        ? {
            id: `device:${event.event_id}`,
            timestamp: event.timestamp,
            kind: 'ml',
            source: event.source,
            tag: 'ML',
            text: anomalyEventLine(event, deviceNames),
            detail: `Isolation Forest · score ${event.details?.score ?? '—'}`,
            tone: 'error',
          }
        : {
            id: `device:${event.event_id}`,
            timestamp: event.timestamp,
            kind: 'device',
            source: event.source,
            tag: SOURCE_TAGS[event.source] ?? event.source.toUpperCase(),
            text: deviceEventLine(event, deviceNames),
            tone: 'ok',
          },
    ),
    ...gestureEvents.map((event) => ({
      id: `gesture:${event.event_id}`,
      timestamp: event.timestamp,
      kind: 'gesture',
      source: 'gesture',
      tag: 'GESTURE',
      text: `${event.gesture} ${Math.round(event.confidence * 100)}% → ${event.intent}`,
      detail: event.success ? event.action ?? event.outcome : event.detail ?? event.outcome,
      tone: event.success ? 'ok' : 'error',
    })),
    ...aiInteractions.map((interaction) => ({
      id: `ai:${interaction.interaction_id}`,
      timestamp: interaction.timestamp,
      kind: 'ai',
      source: 'ai_agent',
      tag: 'AI AGENT',
      text: `“${interaction.request}”`,
      detail: interaction.outcome,
      tone: interaction.any_rejected || !interaction.plan_valid ? 'warning' : 'ok',
    })),
  ]
  return entries.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
}
