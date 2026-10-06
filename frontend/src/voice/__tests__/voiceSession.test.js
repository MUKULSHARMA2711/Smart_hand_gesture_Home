import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { spokenSummary, voiceStatusLabel } from '../../lib/assistant'
import { createVoiceSession, speakText, splitWake } from '../voiceSession'

/** A stand-in for the browser's SpeechRecognition that tests drive by hand. */
class FakeRecognition {
  static instances = []
  constructor() {
    this.started = false
    this.aborted = false
    FakeRecognition.instances.push(this)
  }
  start() {
    this.started = true
  }
  abort() {
    this.aborted = true
  }
  say(text, isFinal = true) {
    const result = Object.assign([{ transcript: text }], { isFinal })
    this.onresult?.({ resultIndex: 0, results: [result] })
  }
  fail(error) {
    this.onerror?.({ error })
  }
  end() {
    this.onend?.()
  }
}

const current = () => FakeRecognition.instances.at(-1)
const flush = async () => {
  for (let i = 0; i < 5; i += 1) await Promise.resolve()
}

function session(overrides = {}) {
  const states = []
  const commands = []
  const spoken = []
  const voice = createVoiceSession({
    Recognition: FakeRecognition,
    onState: (s) => states.push(s.state),
    onCommand: async (text) => {
      commands.push(text)
      return overrides.reply ?? { speech: `Done: ${text}`, expectsReply: false }
    },
    speak: async (text) => spoken.push(text),
    commandWindowMs: 8000,
    ...overrides,
  })
  return { voice, states, commands, spoken }
}

beforeEach(() => {
  FakeRecognition.instances = []
  vi.useFakeTimers()
})
afterEach(() => vi.useRealTimers())

describe('wake phrase', () => {
  it.each([
    ['Hey IntelliHome, turn on the fan', true, 'turn on the fan'],
    ['hey intelli home turn off the light', true, 'turn off the light'],
    ['Hey IntelliHome.', true, ''],
    ['turn on the fan', false, ''],
    ['hey intelligent', false, ''],
  ])('%s', (text, woke, command) => {
    expect(splitWake(text)).toEqual({ woke, command })
  })
})

describe('voice session', () => {
  it('reports unsupported browsers without crashing', () => {
    const { voice, states } = session({ Recognition: null })
    voice.start()
    expect(states).toEqual(['unsupported'])
    expect(voice.active).toBe(false)
  })

  it('wake phrase + command in one utterance goes to the assistant, then back to listening', async () => {
    const { voice, states, commands, spoken } = session()
    voice.start()
    expect(current().continuous).toBe(true)

    current().say('turn on the fan') // no wake phrase: ignored
    expect(commands).toEqual([])
    const first = current()
    first.say('Hey IntelliHome, turn on the living room fan')
    await flush()

    expect(commands).toEqual(['turn on the living room fan'])
    expect(first.aborted).toBe(true) // the microphone pauses while processing and speaking
    expect(spoken).toEqual(['Done: turn on the living room fan'])
    expect(states).toEqual(['wake', 'processing', 'speaking', 'wake'])
    expect(current()).not.toBe(first) // listening again afterwards
  })

  it('wake phrase alone opens a command window that times out', async () => {
    const { voice, states, commands } = session()
    voice.start()
    current().say('Hey IntelliHome')
    expect(states.at(-1)).toBe('command')

    current().say('lock the front door')
    await flush()
    expect(commands).toEqual(['lock the front door'])

    current().say('hey intellihome')
    vi.advanceTimersByTime(8000)
    expect(states.at(-1)).toBe('wake')
    current().say('turn off the light') // after the window, needs the wake phrase again
    await flush()
    expect(commands).toEqual(['lock the front door'])
  })

  it('a pending door confirmation is answered without the wake phrase', async () => {
    const { voice, commands } = session({ reply: { speech: 'Are you sure?', expectsReply: true } })
    voice.start()
    current().say('Hey IntelliHome, unlock the main door')
    await flush()

    current().say('yes, unlock it')
    await flush()
    expect(commands).toEqual(['unlock the main door', 'yes, unlock it'])
  })

  it('ignores interim results', async () => {
    const heard = []
    const { voice, commands } = session({ onHeard: (text) => heard.push(text) })
    voice.start()
    current().say('Hey IntelliHome, turn', false)
    await flush()
    expect(commands).toEqual([])
    expect(heard).toEqual(['Hey IntelliHome, turn'])
  })

  it('microphone denial stops everything with a clear message', () => {
    const messages = []
    const voice = createVoiceSession({ Recognition: FakeRecognition, onCommand: vi.fn(), onState: (s) => messages.push(s) })
    voice.start()
    const recognizer = current()

    recognizer.fail('not-allowed')
    recognizer.end()

    expect(messages.at(-1)).toEqual({ state: 'error', message: 'Microphone access was denied. Allow it in the browser to use voice.' })
    expect(recognizer.aborted).toBe(true)
    expect(FakeRecognition.instances).toHaveLength(1) // never restarted
    expect(voice.active).toBe(false)
  })

  it('recognition failures are reported, and silence just restarts', () => {
    const { voice, states } = session()
    voice.start()
    current().fail('no-speech')
    current().end()
    expect(FakeRecognition.instances).toHaveLength(2)
    expect(states.at(-1)).toBe('wake')

    current().fail('network')
    expect(states.at(-1)).toBe('error')
  })

  it('a session that keeps ending is stopped instead of restarting forever', () => {
    const { voice, states } = session({ maxRestarts: 3 })
    voice.start()
    for (let i = 0; i < 4; i += 1) current().end()
    expect(states.at(-1)).toBe('error')
    expect(FakeRecognition.instances).toHaveLength(4)
  })

  it('stop releases the recogniser, timers and late results (no background listener)', async () => {
    let resolveCommand
    const { voice, states, spoken } = session({
      onCommand: () => new Promise((resolve) => (resolveCommand = resolve)),
    })
    voice.start()
    current().say('Hey IntelliHome')
    current().say('turn on the fan')
    voice.stop()

    resolveCommand({ speech: 'Done', expectsReply: false })
    await flush()
    vi.runAllTimers()

    expect(spoken).toEqual([]) // nothing spoken after stop
    expect(states.at(-1)).toBe('off')
    expect(FakeRecognition.instances.every((r) => r.aborted || !r.onend)).toBe(true)
    const count = FakeRecognition.instances.length
    FakeRecognition.instances.forEach((r) => r.end?.())
    expect(FakeRecognition.instances).toHaveLength(count) // no restart
  })
})

describe('speech output', () => {
  it('speaks through speechSynthesis and resolves when finished', async () => {
    const synth = { speak: vi.fn((u) => u.onend()), cancel: vi.fn() }
    class Utterance {
      constructor(text) {
        this.text = text
      }
    }
    await speakText('Done.', synth, Utterance)
    expect(synth.speak.mock.calls[0][0].text).toBe('Done.')
    await expect(speakText('x', undefined, undefined)).resolves.toBeUndefined() // unsupported: silent
  })

  it('summaries reflect the backend results, not the planner text', () => {
    const names = { fan_living_room: 'Living Room Fan', door_main: 'Main Door' }
    const base = { plan_valid: true, reply: "I'll turn it on and unlock the door!", actions: [] }
    expect(
      spokenSummary(
        {
          ...base,
          actions: [
            { device_id: 'fan_living_room', intent: 'TURN_ON', status: 'executed' },
            { device_id: 'fan_living_room', intent: 'SET_SPEED', parameters: { value: 70 }, status: 'executed' },
          ],
        },
        names,
      ),
    ).toBe('Done. Living Room Fan is now on, Living Room Fan speed is now 70%.')
    expect(
      spokenSummary({ ...base, actions: [{ device_id: 'door_main', intent: 'TURN_ON', status: 'rejected', reason: 'Not supported.' }] }, names),
    ).toBe('Main Door was not changed: Not supported.')
    expect(spokenSummary({ ...base, confirmation: { prompt: 'Are you sure?' } })).toBe('Are you sure?')
    expect(spokenSummary(null)).toMatch(/couldn't reach/)
    expect(spokenSummary({ ...base, reply: 'It is 26 °C.', actions: [{ intent: 'GET_STATUS', status: 'answered' }] })).toBe('It is 26 °C.')
  })

  it('status line follows the real request', () => {
    expect(voiceStatusLabel({ state: 'wake' })).toBe('Listening for “Hey IntelliHome”')
    expect(voiceStatusLabel({ state: 'processing' }, 'executing')).toBe('Executing…')
    expect(voiceStatusLabel({ state: 'processing' }, 'success')).toBe('Done')
    expect(voiceStatusLabel({ state: 'error', message: 'Microphone access was denied.' })).toBe('Microphone access was denied.')
  })
})
