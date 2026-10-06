import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { homeHealth } from '../../state/homeHealth'
import { ChatTurn } from '../assistant/ChatTurn'
import { SceneSensors } from '../house/SceneSensors'
import { prediction } from '../ml/__tests__/fixtures'
import { PredictionCard } from '../ml/PredictionCard'
import { SensorStrip } from '../SensorStrip'

const text = (element) => renderToStaticMarkup(element).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')

const energy = { total_power_w: 3.6, energy_kwh: 0.01, per_device_w: {} }
const offlineHome = {
  timestamp: new Date(1_000_000).toISOString(),
  environment: null,
  sensor_error: 'Implausible sensor reading rejected (temperature_c: Input should be greater than or equal to -40).',
  energy,
  devices: [],
}

describe('missing sensor data is shown as unavailable, never as numbers', () => {
  it('sensor strip', () => {
    const html = text(<SensorStrip home={offlineHome} />)
    expect(html).toContain('Sensors unavailable')
    expect(html).toContain('Values are not estimated')
    expect(html).toContain('Implausible sensor reading rejected')
    expect(html).not.toContain('°C')
  })

  it('3D overlay and home status', () => {
    expect(text(<SceneSensors environment={null} energy={energy} />)).toContain('Unavailable')
    const sensors = homeHealth(offlineHome, 1_001_000).checks.find((check) => check.id === 'sensors')
    expect(sensors).toMatchObject({ status: 'warning', detail: 'Sensors unavailable' })
  })

  it('prediction made from imputed sensor inputs is labelled low confidence', () => {
    const html = text(
      <PredictionCard prediction={{ ...prediction, reliable: false, missing_features: ['temperature_c', 'occupied'] }} />,
    )
    expect(html).toContain('Low confidence')
    expect(html).toContain('temperature, occupancy')
    expect(text(<PredictionCard prediction={prediction} />)).not.toContain('Low confidence')
  })
})

describe('assistant turn states', () => {
  it('shows a thinking state while the request is in flight', () => {
    expect(text(<ChatTurn turn={{ interaction_id: 'p', request: 'hi', pending: true }} devicesById={{}} deviceNames={{}} />)).toContain(
      'IntelliHome is thinking',
    )
  })

  it('shows an AI outage clearly, without a fake reply', () => {
    const turn = {
      interaction_id: 'p',
      request: 'turn on the fan',
      transportError: 'AI service is currently unavailable.',
      errorCode: 'ai_unavailable',
      errorReason: 'Could not reach the AI provider.',
    }
    const html = renderToStaticMarkup(<ChatTurn turn={turn} devicesById={{}} deviceNames={{}} />)
    expect(html).toContain('role="alert"')
    expect(text(<ChatTurn turn={turn} devicesById={{}} deviceNames={{}} />)).toContain(
      'AI service is currently unavailable. Nothing was changed. Device controls, gestures and the dashboard still work.',
    )
  })
})
