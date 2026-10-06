import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { AnomalyCard, AnomalyPanel } from '../AnomalyPanel'
import { PredictionCard } from '../PredictionCard'
import { anomalous, prediction, reportWith } from './fixtures'

const text = (element) => renderToStaticMarkup(element).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')

describe('PredictionCard', () => {
  it('renders the real probability, device, model and reasons', () => {
    const html = text(<PredictionCard prediction={prediction} onAskAI={() => {}} />)
    expect(html).toContain('Living Room Fan')
    expect(html).toContain('91%')
    expect(html).toContain('random_forest_v1')
    expect(html).toContain('Temperature 30.2 °C (typical 25.6 °C)')
    expect(html).toContain('Room occupied')
    expect(html).not.toContain('Time 15:00') // not among the model's reason features
    expect(html).toContain('Ask AI why')
  })

  it('never presents a prediction as an executed action', () => {
    const html = text(<PredictionCard prediction={prediction} />)
    expect(html).toContain('Recommendation only; nothing has been switched on')
    expect(html).toContain('simulated history')
  })

  it('handles an unlikely prediction and missing data', () => {
    expect(text(<PredictionCard prediction={{ ...prediction, prediction: 'OFF', probability: 0.12 }} />)).toContain('unlikely')
    expect(text(<PredictionCard prediction={null} />)).toContain('No prediction available.')
  })
})

describe('AnomalyCard', () => {
  it('shows observed power against the learned normal range', () => {
    const html = text(<AnomalyCard result={anomalous} />)
    expect(html).toContain('Living Room Fan · Anomaly')
    expect(html).toContain('170.0 W observed · normal 34.6–42.5 W')
    expect(html).toContain('Score -0.118')
    expect(html).toContain('Isolation Forest classified this reading as anomalous')
  })

  it('marks a normal reading as normal', () => {
    expect(text(<AnomalyCard result={{ ...anomalous, is_anomaly: false, score: 0.1 }} />)).toContain('Normal')
  })
})

describe('AnomalyPanel', () => {
  it('lists active anomalies and the live device table', () => {
    const html = text(<AnomalyPanel report={reportWith([anomalous])} onAskAI={() => {}} />)
    expect(html).toContain('170.0 W observed')
    expect(html).toContain('Ask AI to explain')
    expect(html).toContain('Living Room Light')
  })

  it('says so when nothing is anomalous', () => {
    const html = text(<AnomalyPanel report={reportWith([])} />)
    expect(html).toContain('No anomalies')
    expect(html).not.toContain('⚠ Anomaly')
  })
})
