/**
 * Home status checks computed only from real HomeState data.
 *
 * There is deliberately no numeric "intelligence score": the backend has no anomaly
 * detection or baselines yet, so we report verifiable checks and label what is missing.
 */
import { formatPower } from '../lib/format'

export const SENSOR_STALE_MS = 20_000

export function homeHealth(home, now = Date.now(), anomalies = null) {
  if (!home) return { checks: [], info: [], passed: 0, total: 0 }
  const devices = home.devices ?? []
  const online = devices.filter((device) => device.status === 'online').length
  const doors = devices.filter((device) => device.device_type === 'door_lock')
  const unlocked = doors.filter((door) => !door.state?.is_locked)
  const ageMs = now - new Date(home.timestamp).getTime()
  const sensorsFresh = Number.isFinite(ageMs) && ageMs < SENSOR_STALE_MS && home.environment != null

  const checks = [
    {
      id: 'devices',
      label: 'Devices online',
      status: online === devices.length ? 'ok' : 'warning',
      detail: `${online} of ${devices.length} online`,
    },
    {
      id: 'security',
      label: 'Entrance security',
      status: unlocked.length ? 'warning' : 'ok',
      detail: unlocked.length ? `${unlocked.map((d) => d.name).join(', ')} unlocked` : 'All doors locked',
    },
    {
      id: 'sensors',
      label: 'Sensors reporting',
      status: sensorsFresh ? 'ok' : 'warning',
      detail: sensorsFresh
        ? `Updated ${Math.max(0, Math.round(ageMs / 1000))} s ago`
        : home.environment == null
          ? 'Sensors unavailable'
          : 'No recent readings',
    },
  ]

  if (anomalies) {
    // Real Isolation Forest results from GET /ml/anomalies.
    const flagged = [...anomalies.active, ...anomalies.live.filter((r) => r.is_anomaly)]
    checks.push({
      id: 'energy_anomalies',
      label: 'Energy anomalies',
      status: flagged.length ? 'warning' : 'ok',
      detail: flagged.length
        ? `${flagged[0].device_name}: ${flagged[0].observed_power_watts.toFixed(1)} W (normal ${flagged[0].expected_range.min.toFixed(1)}–${flagged[0].expected_range.max.toFixed(1)} W)`
        : 'None (Isolation Forest)',
    })
  }

  const total = home.energy?.total_power_w ?? 0
  const top = [...devices].sort((a, b) => b.power_w - a.power_w)[0]
  const info = [
    {
      id: 'energy',
      label: 'Power draw',
      detail: top && total ? `${formatPower(total)} · ${top.name} ${Math.round((100 * top.power_w) / total)}%` : formatPower(total),
    },
    ...(anomalies ? [] : [{ id: 'anomalies', label: 'Anomaly detection', detail: 'Not available yet' }]),
  ]

  return { checks, info, passed: checks.filter((c) => c.status === 'ok').length, total: checks.length }
}
