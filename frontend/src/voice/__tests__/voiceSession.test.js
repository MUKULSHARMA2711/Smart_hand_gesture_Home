import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { spokenSummary, voiceStatusLabel } from '../../lib/assistant'
import { createVoiceSession, normalizeTranscript, speakText, splitWake } from '../voiceSession'

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

describe('Edge wake-phrase variants', () => {
  it.each([
    ['hey intellihome', 'exact'],
    ['Hey IntelliHome.', 'case and punctuation'],
    ['hey intelli home', 'split word'],
    ['hey intel home', 'Intel'],
    ['hey intelly home', 'intelly'],
    ['Hey intelli-home!', 'hyphen'],
    ['Hey, Intelli. Home?', 'punctuation between words'],
    ['hey  INTELLI   home', 'extra whitespace'],
    ['hay intellihome', 'hey heard as hay'],
    ['hey intelligent home', 'intelligent'],
    ['um hey intel home', 'short filler first'],
  ])('%s (%s) wakes, with no command', (text) => {
    expect(splitWake(text)).toEqual({ woke: true, command: '' })
  })

  it('extracts the command spoken in the same breath, keeping its wording', () => {
    expect(splitWake('Hey Intel home, turn on the fan')).toEqual({ woke: true, command: 'turn on the fan' })
    expect(splitWake("hey intelli-home don't unlock the door")).toEqual({ woke: true, command: "don't unlock the door" })
  })

  it('joins a wake phrase split across two recognition results', () => {
    expect(splitWake('home turn on the fan', 'hey intelli')).toEqual({ woke: true, command: 'turn on the fan' })
    expect(splitWake('intellihome', 'hey')).toEqual({ woke: true, command: '' })
  })

  it.each([
    'turn on the fan',
    'hey there',
    'hey intel how are you',
    'they intel home office',
    'I came home and said hey',
    'the new intel home router is fast hey', // "hey" is not at the start of an utterance
    'my neighbour said hey intelli home loudly yesterday', // ... nor here
    'hey home',
  ])('ordinary speech does not wake: %s', (text) => {
    expect(splitWake(text).woke).toBe(false)
  })

  it('normalises transcripts', () => {
    expect(normalizeTranscript('  Hey, Intelli-Home!  Turn ON the fan. ')).toBe('hey intelli home turn on the fan')
  })
})

describe('wake phrase in a live session', () => {
  it('detects a wake phrase that Edge split across results, and sends only the command', async () => {
    const { voice, commands } = session()
    voice.start()
    current().say('hey intelli')
    current().say('home turn on the fan')
    await flush()
    expect(commands).toEqual(['turn on the fan'])
  })

  it('split wake phrase with nothing after it opens the command window', async () => {
    const { voice, states, commands } = session()
    voice.start()
    current().say('hey intel')
    current().say('home')
    expect(states.at(-1)).toBe('command')
    current().say('turn off the light')
    await flush()
    expect(commands).toEqual(['turn off the light']) // "Hey IntelliHome" itself is never sent
  })

  it('does not join results that are too far apart', () => {
    let clock = 0
    const { voice, states } = session({ now: () => clock })
    voice.start()
    current().say('hey intelli')
    clock += 10_000
    current().say('home')
    expect(states.at(-1)).toBe('wake')
  })

  it('a repeated wake phrase in the command window is not sent as a command', async () => {
    const { voice, commands } = session()
    voice.start()
    current().say('Hey Intel home')
    current().say('hey intel home')
    current().say('lock the front door')
    await flush()
    expect(commands).toEqual(['lock the front door'])
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
