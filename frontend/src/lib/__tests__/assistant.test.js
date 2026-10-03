import { describe, expect, it } from 'vitest'
import { changedDeviceStates, describeAction } from '../assistant'

const names = { fan_living_room: 'Living Room Fan', door_main: 'Main Door' }

describe('describeAction', () => {
  it.each([
    [{ device_id: 'fan_living_room', intent: 'TURN_ON', parameters: {} }, 'Living Room Fan → ON'],
    [{ device_id: 'fan_living_room', intent: 'SET_SPEED', parameters: { value: 70 } }, 'Living Room Fan speed → 70%'],
    [{ device_id: 'door_main', intent: 'LOCK_DOOR', parameters: {} }, 'Main Door → LOCKED'],
    [{ device_id: null, intent: 'GET_ENERGY', parameters: {} }, 'Home energy usage checked'],
    [{ device_id: 'ghost', intent: 'TURN_OFF', parameters: {} }, 'ghost → OFF'],
    [{ device_id: null, intent: null, parameters: {} }, 'Malformed action'],
  ])('labels %o', (result, expected) => {
    expect(describeAction(result, names)).toBe(expected)
  })
})

describe('changedDeviceStates', () => {
  it('returns the final state of each changed device', () => {
    const response = {
      changed_devices: ['fan_living_room'],
      actions: [
        { status: 'executed', device_id: 'fan_living_room', new_state: { is_on: true, speed: 50 } },
        { status: 'executed', device_id: 'fan_living_room', new_state: { is_on: true, speed: 70 } },
        { status: 'rejected', device_id: 'door_main', new_state: null },
      ],
    }
    expect(changedDeviceStates(response)).toEqual([{ id: 'fan_living_room', state: { is_on: true, speed: 70 } }])
  })
})
