/**
 * The intent a committed gesture sends for the selected device. The mapping from the backend
 * (GET /gestures/config) is used unchanged, with one device-aware exception: a FIST on a device
 * that can LOCK (the Main Door) means LOCK_DOOR, since a lock has nothing to turn off. On the fan,
 * AC and light a fist stays TURN_OFF. The backend re-checks the gesture, the intent and the
 * device's capability; no gesture ever maps to UNLOCK_DOOR here.
 */
export function gestureIntent(gesture, device, intents) {
  if (gesture === 'FIST' && device?.capabilities?.includes('LOCK')) return 'LOCK_DOOR'
  return intents[gesture]
}
