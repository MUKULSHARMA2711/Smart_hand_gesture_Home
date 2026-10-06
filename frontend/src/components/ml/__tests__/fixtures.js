/** Fixtures shaped exactly like the backend's /ml/predict and /ml/anomalies responses. */

export const prediction = {
  device_id: 'fan_living_room',
  device_name: 'Living Room Fan',
  target: 'FAN_ON_SOON',
  prediction: 'ON',
  probability: 0.9132,
  threshold: 0.5,
  horizon_minutes: 30,
  features: { temperature_c: 30.2, occupied: 1, hour: 15 },
  missing_features: [],
  factors: [
    { feature: 'temperature_c', label: 'Temperature', value: 30.2, typical: 25.6, importance: 0.2, effect: 0.41, imputed: false, description: 'Temperature 30.2 °C (typical 25.6 °C)' },
    { feature: 'occupied', label: 'Occupancy', value: 1, typical: 0, importance: 0.05, effect: 0.22, imputed: false, description: 'Room occupied' },
    { feature: 'hour', label: 'Hour of day', value: 15, typical: 12, importance: 0.06, effect: 0.0, imputed: false, description: 'Time 15:00' },
  ],
  reason_features: { temperature_c: 30.2, occupied: 1 },
  explanation: 'Random Forest predicted a 91% probability…',
  model: 'random_forest_v1',
  generated_at: '2026-10-06T10:00:00Z',
}

export const anomalous = {
  device_id: 'fan_living_room',
  device_name: 'Living Room Fan',
  device_type: 'fan',
  is_anomaly: true,
  score: -0.1181,
  observed_power_watts: 170,
  expected_range: { min: 34.59, max: 42.53 },
  setting: 'on at speed 60%',
  source: 'reading',
  timestamp: '2026-10-06T10:01:00Z',
  explanation: 'Isolation Forest classified this reading as anomalous: the Living Room Fan drew 170.0 W…',
  model: 'isolation_forest_v1',
  event_id: 'evt-1',
}

export const normalLive = (deviceId, name) => ({
  ...anomalous,
  device_id: deviceId,
  device_name: name,
  is_anomaly: false,
  score: 0.12,
  observed_power_watts: 40.8,
  source: 'live',
  explanation: 'Within the learned normal pattern.',
  event_id: null,
})

export const reportWith = (active) => ({
  checked_at: '2026-10-06T10:02:00Z',
  live: [normalLive('fan_living_room', 'Living Room Fan'), normalLive('light_living_room', 'Living Room Light')],
  recent: active,
  active,
  active_count: active.length,
  model: 'isolation_forest_v1',
})
