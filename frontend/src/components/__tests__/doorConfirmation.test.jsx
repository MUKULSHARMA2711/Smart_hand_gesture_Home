import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { confirmationSecondsLeft } from '../../lib/assistant'
import { resultPhase, visualizedActions } from '../../state/aiLifecycle'
import { ChatTurn, ConfirmationCard } from '../assistant/ChatTurn'

const text = (element) => renderToStaticMarkup(element).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')

const inSeconds = (s) => new Date(Date.now() + s * 1000).toISOString()
const confirmation = (expiresIn = 30) => ({
  confirmation_id: 'c1',
  device_id: 'door_main',
  intent: 'UNLOCK_DOOR',
  prompt: "Are you sure you want to unlock the Main Door? Say 'yes, unlock it' to confirm, or 'cancel'.",
  created_at: new Date().toISOString(),
  expires_at: inSeconds(expiresIn),
})
const held = (status, extra = {}) => ({
  interaction_id: 'i1',
  request: 'unlock the main door',
  reply: confirmation().prompt,
  outcome: '1 awaiting confirmation.',
  plan_valid: true,
  errors: [],
  changed_devices: [],
  actions: [{ index: 0, device_id: 'door_main', intent: 'UNLOCK_DOOR', parameters: {}, status }],
  ...extra,
})

describe('door unlock confirmation UI', () => {
  it('shows the request as waiting for confirmation, with the time left and both choices', () => {
    const html = text(
      <ChatTurn turn={held('awaiting_confirmation', { confirmation: confirmation(30) })} deviceNames={{ door_main: 'Main Door' }} devicesById={{}} isLatest />,
    )
    expect(html).toContain('Waiting for confirmation: Main Door → UNLOCKED')
    expect(html).toMatch(/Waiting for confirmation · (29|30) s/)
    expect(html).toContain('Confirm unlock')
    expect(html).toContain('Cancel')
  })

  it('offers no buttons on an older turn or after expiry', () => {
    expect(text(<ConfirmationCard confirmation={confirmation()} active={false} />)).toBe('')
    expect(text(<ConfirmationCard confirmation={confirmation(-1)} active />)).toContain('Confirmation expired. The door stays locked.')
    expect(confirmationSecondsLeft(confirmation(-5))).toBe(0)
  })

  it('shows cancelled and executed outcomes from the backend', () => {
    const names = { door_main: 'Main Door' }
    expect(text(<ChatTurn turn={held('cancelled')} deviceNames={names} devicesById={{}} />)).toContain('Cancelled: Main Door → UNLOCKED')
    expect(text(<ChatTurn turn={held('executed')} deviceNames={names} devicesById={{}} />)).toContain('Done: Main Door → UNLOCKED')
  })

  it('sends no command beam for a held or cancelled unlock, and is not an error', () => {
    for (const status of ['awaiting_confirmation', 'cancelled']) {
      expect(visualizedActions(held(status))).toEqual([])
      expect(resultPhase(held(status))).toBe('success')
    }
    expect(visualizedActions(held('executed'))).toHaveLength(1)
  })
})
