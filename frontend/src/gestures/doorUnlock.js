/**
 * Secure gesture unlock, frontend side. The backend does all the security work; this only
 * routes gestures while a door unlock is pending:
 *
 *   FOUR_FINGERS on the door → backend creates a pending confirmation (nothing unlocks)
 *   stable PINCH            → POST /ai/confirmations/{id} {"decision": "confirm"} (once)
 *   OPEN_PALM / other gesture / hand lost / camera off / page left → cancel (fail closed)
 *
 * The door's state is never changed here: the 3D view and the device card update only from
 * the backend's confirmed state after the confirmation succeeds.
 */

export const UNLOCK_GESTURE = 'FOUR_FINGERS'

/**
 * @param {{
 *   decide: (confirmationId: string, decision: 'confirm'|'cancel') => Promise<object>,
 *   onChange: (state: object|null) => void,
 *   onSettled?: () => void,
 *   now?: () => number,
 * }} options
 */
export function createDoorUnlockController({ decide, onChange, onSettled = () => {}, now = () => Date.now() }) {
  let pending = null // { confirmation, deviceName }
  let state = null

  const set = (next) => {
    state = next
    onChange(next)
  }

  function expired() {
    return pending !== null && new Date(pending.confirmation.expires_at).getTime() <= now()
  }

  async function finish(decision, reason) {
    const { confirmation, deviceName } = pending
    pending = null // a confirmation is answered at most once, whatever happens next
    if (decision === 'cancel') {
      set({ status: 'cancelled', deviceName, message: reason })
      try {
        await decide(confirmation.confirmation_id, 'cancel')
      } catch {
        // fail closed: the backend also expires it
      }
      return
    }
    set({ status: 'confirming', deviceName, confirmation })
    try {
      const response = await decide(confirmation.confirmation_id, 'confirm')
      const action = response?.actions?.[0]
      if (action?.status === 'executed') set({ status: 'confirmed', deviceName })
      else set({ status: 'failed', deviceName, message: action?.reason ?? 'The unlock was not executed.' })
    } catch (error) {
      const status = error?.code === 'confirmation_expired' ? 'expired' : 'failed'
      set({ status, deviceName, message: error?.message ?? 'The unlock was not executed.' })
    } finally {
      onSettled()
    }
  }

  return {
    get pending() {
      return pending !== null
    },
    get state() {
      return state
    },
    /** The backend answered FOUR_FINGERS with a pending confirmation. */
    requested(confirmation, deviceName) {
      pending = { confirmation, deviceName }
      set({ status: 'pending', deviceName, confirmation })
    },
    /**
     * A pinch event. Returns true if it belonged to the unlock (so it must not adjust anything).
     * Only a stable pinch start confirms; the pinch detector already requires several frames.
     */
    pinch(event) {
      if (!pending) return false
      if (event.type === 'start') {
        if (expired()) {
          pending = null
          set({ status: 'expired', deviceName: state?.deviceName, message: 'The request expired. The door stays locked.' })
        } else {
          finish('confirm')
        }
      }
      return true
    },
    /**
     * A committed (stabilised) gesture. Returns true if it was consumed by the unlock flow.
     * OPEN_PALM cancels; any other gesture cancels and then runs normally; FOUR_FINGERS
     * again simply requests a fresh confirmation (the backend replaces the old one).
     */
    gesture(name) {
      if (!pending) return false
      if (name === 'OPEN_PALM') {
        finish('cancel', 'Cancelled with an open palm. The door stays locked.')
        return true
      }
      if (name !== UNLOCK_GESTURE) finish('cancel', 'Cancelled: another gesture was used. The door stays locked.')
      return false
    },
    /** Hand out of view, camera stopped or page left. */
    cancel(reason) {
      if (pending) finish('cancel', reason)
    },
    /** Called on a timer: mark an expired request (the backend refuses it anyway). */
    tick() {
      if (expired()) {
        pending = null
        set({ status: 'expired', deviceName: state?.deviceName, message: 'The request expired. The door stays locked.' })
      }
    },
    clear() {
      if (!pending) set(null)
    },
  }
}
