/**
 * Who receives a stable pinch. Decided by the selected device first, so the door can never
 * reach the fan / AC adjustment (which would answer "has no adjustable value"):
 *
 *   door unlock pending or in flight → door unlock (confirm / ignore)
 *   Main Door (door lock) selected    → door unlock (first pinch = request)
 *   anything else (fan, AC, light)   → the existing adjustment, unchanged
 *
 * @returns {'door'|'adjust'} where the event went
 */
export function routePinch(event, { device, unlock, adjuster }) {
  if (unlock.busy || device?.device_type === 'door_lock') {
    unlock.pinch(event)
    return 'door'
  }
  adjuster.handle(event)
  return 'adjust'
}
