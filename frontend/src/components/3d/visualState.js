/**
 * Pure mappings from *backend* device state to visual parameters.
 *
 * The 3D scene never stores device state of its own: every frame it renders what these
 * functions derive from the latest backend snapshot. Keeping them pure makes the
 * backend → visual contract unit-testable.
 */

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))
const lerp = (a, b, t) => a + (b - a) * t

// --- Light --------------------------------------------------------------------------------

/** Dimmest visible level, so brightness 1% is still distinguishable from "off". */
export const LIGHT_MIN_LEVEL = 0.12
export const LIGHT_MAX_POINT_INTENSITY = 40

/** brightness 0-100 → level 0-1 (0 when off). */
export function lightVisual(state) {
  const brightness = clamp(Number(state?.brightness ?? 0), 0, 100)
  const on = Boolean(state?.is_on) && brightness > 0
  const level = on ? lerp(LIGHT_MIN_LEVEL, 1, brightness / 100) : 0
  return {
    on,
    brightness,
    level,
    pointIntensity: level * LIGHT_MAX_POINT_INTENSITY,
    emissiveIntensity: on ? 0.4 + level * 3.6 : 0,
  }
}

// --- Fan ----------------------------------------------------------------------------------

export const FAN_MIN_RAD_PER_S = 2
export const FAN_MAX_RAD_PER_S = 24

/** speed 0-100 → blade angular velocity (rad/s) and a 0-1 multiplier. */
export function fanVisual(state) {
  const speed = clamp(Number(state?.speed ?? 0), 0, 100)
  const on = Boolean(state?.is_on) && speed > 0
  return {
    on,
    speed,
    multiplier: on ? speed / 100 : 0,
    angularVelocity: on ? lerp(FAN_MIN_RAD_PER_S, FAN_MAX_RAD_PER_S, speed / 100) : 0,
  }
}

// --- AC -----------------------------------------------------------------------------------

export const AC_MIN_C = 16
export const AC_MAX_C = 30

/** Colder set points → stronger, bluer airflow. Temperature is shown as-is. */
export function acVisual(state) {
  const on = Boolean(state?.is_on)
  const temperature = Number(state?.target_temperature_c ?? 24)
  const coolness = clamp((AC_MAX_C - temperature) / (AC_MAX_C - AC_MIN_C), 0, 1)
  return {
    on,
    temperature,
    coolness,
    airflow: on ? lerp(0.45, 1, coolness) : 0,
  }
}

// --- Door ---------------------------------------------------------------------------------

/** Unlocked doors are drawn slightly ajar (inwards) so the state reads at a glance. */
export const DOOR_AJAR_ANGLE = 0.6

export function doorVisual(state) {
  const locked = Boolean(state?.is_locked)
  return {
    locked,
    angle: locked ? 0 : DOOR_AJAR_ANGLE,
    indicator: locked ? 'secure' : 'warning',
    label: locked ? 'LOCKED' : 'UNLOCKED',
  }
}

export function deviceVisual(device) {
  switch (device?.device_type) {
    case 'light':
      return lightVisual(device.state)
    case 'fan':
      return fanVisual(device.state)
    case 'ac':
      return acVisual(device.state)
    case 'door_lock':
      return doorVisual(device.state)
    default:
      return null
  }
}

/**
 * Connectivity label for a device that is not reachable, or null when it is online.
 * Hardware devices report it over MQTT; the state shown is then the last confirmed one.
 */
export function connectivityLabel(device) {
  if (!device?.status || device.status === 'online') return null
  return device.status === 'offline' ? 'OFFLINE' : device.status === 'unknown' ? 'UNKNOWN' : device.status.toUpperCase()
}

/** Short status shown on 3D labels, e.g. "ON · 70%", "OFF · 24 °C", "LOCKED". */
export function deviceStatusLabel(device) {
  const state = device?.state ?? {}
  switch (device?.device_type) {
    case 'light':
      return state.is_on ? `ON · ${state.brightness}%` : 'OFF'
    case 'fan':
      return state.is_on ? `ON · ${state.speed}%` : 'OFF'
    case 'ac':
      return `${state.is_on ? 'ON' : 'OFF'} · ${state.target_temperature_c} °C`
    case 'door_lock':
      return state.is_locked ? 'LOCKED' : 'UNLOCKED'
    default:
      return ''
  }
}

// --- Animation helper -----------------------------------------------------------------------

/** Frame-rate independent exponential approach (used for fan spin-up and door swing). */
export function approach(current, target, rate, dt) {
  return target + (current - target) * Math.exp(-rate * dt)
}

// --- AI core ----------------------------------------------------------------------------------

export const ORB_STATES = ['idle', 'listening', 'thinking', 'planning', 'executing', 'success', 'error']

const ORB_APPEARANCE = {
  idle: { color: '#38bdf8', pulseSpeed: 1.1, pulseAmount: 0.04, glow: 0.45, ringSpeed: 0.15, rings: 1, particles: false, shell: false, waves: false },
  listening: { color: '#38bdf8', pulseSpeed: 1.8, pulseAmount: 0.06, glow: 0.6, ringSpeed: 0.3, rings: 1, particles: false, shell: false, waves: true },
  thinking: { color: '#22d3ee', pulseSpeed: 3.2, pulseAmount: 0.09, glow: 0.8, ringSpeed: 1.6, rings: 3, particles: true, shell: false, waves: false },
  planning: { color: '#22d3ee', pulseSpeed: 2.6, pulseAmount: 0.08, glow: 0.85, ringSpeed: 1.0, rings: 3, particles: true, shell: true, waves: false },
  executing: { color: '#67e8f9', pulseSpeed: 4.5, pulseAmount: 0.14, glow: 1, ringSpeed: 2.2, rings: 3, particles: true, shell: true, waves: false },
  success: { color: '#34d399', pulseSpeed: 1.6, pulseAmount: 0.06, glow: 0.9, ringSpeed: 0.4, rings: 1, particles: false, shell: false, waves: false, burst: true },
  error: { color: '#f87171', pulseSpeed: 5, pulseAmount: 0.05, glow: 0.9, ringSpeed: 0.2, rings: 1, particles: false, shell: false, waves: false, burst: true, shake: true },
}

export function orbAppearance(state) {
  return ORB_APPEARANCE[state] ?? ORB_APPEARANCE.idle
}
