/**
 * Secure gesture unlock by double pinch, frontend side. The backend does all the security
 * work; this only routes pinches while the Main Door is selected:
 *
 *   1st stable pinch on the door → backend creates a pending confirmation (nothing unlocks)
 *   2nd stable pinch            → POST /ai/confirmations/{id} {"decision": "confirm"} (once)
 *   OPEN_PALM / other gesture / hand lost / camera off / page left → cancel (fail closed)
 *
 * With the fan or AC selected, pinches are not touched here (they adjust, as before). The
 * door's state is never changed here: the 3D view and the device card update only from the
 * backend's confirmed state after the confirmation succeeds.
 */

/**
 * @param {{
 *   requestUnlock: (pinchConfidence: number) => Promise<{confirmation?: object, device?: {name: string}}>,
 *   decide: (confirmationId: string, decision: 'confirm'|'cancel') => Promise<object>,
 *   isDoorSelected: () => boolean,
 *   onChange: (state: object|null) => void,
 *   onSettled?: () => void,
 *   now?: () => number,
 * }} options
 */
export function createDoorUnlockController({
  requestUnlock,
  decide,
  isDoorSelected,
  onChange,
  onSettled = () => {},
  now = () => Date.now(),
}) {
  let pending = null // { confirmation, deviceName }
  let requesting = false // the first pinch is being answered
  let confirming = false // the second pinch is being answered
  let state = null

  const set = (next) => {
    state = next
    onChange(next)
  }

  function expired() {
    return pending !== null && new Date(pending.confirmation.expires_at).getTime() <= now()
  }

  async function request(confidence) {
    requesting = true
    set({ status: 'requesting' })
    try {
      const response = await requestUnlock(confidence)
      if (response?.confirmation) {
        pending = { confirmation: response.confirmation, deviceName: response.device?.name ?? 'Main Door' }
        set({ status: 'pending', deviceName: pending.deviceName, confirmation: pending.confirmation })
      } else {
        set({ status: 'failed', message: 'The unlock request was not accepted.' })
      }
    } catch (error) {
      set({ status: 'failed', message: error?.message ?? 'The unlock request was not accepted.' })
    } finally {
      requesting = false
    }
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
    confirming = true
    try {
      const response = await decide(confirmation.confirmation_id, 'confirm')
      const action = response?.actions?.[0]
      if (action?.status === 'executed') set({ status: 'confirmed', deviceName })
      else set({ status: 'failed', deviceName, message: action?.reason ?? 'The unlock was not executed.' })
    } catch (error) {
      const status = error?.code === 'confirmation_expired' ? 'expired' : 'failed'
      set({ status, deviceName, message: error?.message ?? 'The unlock was not executed.' })
    } finally {
      confirming = false
      onSettled()
    }
  }

  return {
    get pending() {
      return pending !== null
    },
    /** A request or confirmation is pending or in flight: every pinch belongs to the door. */
    get busy() {
      return pending !== null || requesting || confirming
    },
    get state() {
      return state
    },
    /**
     * A pinch event. Returns true if it belongs to the door unlock (so it must not adjust).
     * Only a pinch *start* acts; the pinch detector already requires a stable pinch.
     */
    pinch(event) {
      if (requesting || confirming) return true // a pinch is still being answered: ignore more
      if (pending) {
        if (event.type !== 'start') return true // the rest of the first pinch, or of this one
        if (expired()) {
          pending = null
          set({ status: 'expired', deviceName: state?.deviceName, message: 'The request expired. The door stays locked.' })
        } else {
          finish('confirm')
        }
        return true
      }
      if (!isDoorSelected()) return false // fan / AC: adjustment as before
      if (event.type === 'start') request(event.confidence)
      return true
    },
    /**
     * A committed (stabilised) gesture. Returns true if it was consumed by the unlock flow.
     * OPEN_PALM or FIST cancels a pending unlock and does nothing else (no STOP, no lock in the
     * same gesture; a new fist afterwards locks); any other gesture cancels it and then runs
     * normally. A fist while a request or confirmation is in flight is ignored.
     */
    gesture(name) {
      if (name === 'FIST' && (requesting || confirming)) return true
      if (!pending) return false
      if (name === 'OPEN_PALM') {
        finish('cancel', 'Cancelled with an open palm. The door stays locked.')
        return true
      }
      if (name === 'FIST') {
        finish('cancel', 'Cancelled with a fist. The door stays locked.')
        return true
      }
      finish('cancel', 'Cancelled: another gesture was used. The door stays locked.')
      return false
    },
    /** Hand out of view, camera stopped, another device selected or page left. */
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
  }
}
