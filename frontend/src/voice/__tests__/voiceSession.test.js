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

describe('wake phrase "Hey Nova"', () => {
  it.each([
    ['hey nova', 'lower case'],
    ['Hey Nova', 'title case'],
    ['HEY NOVA', 'upper case'],
    ['Hey, Nova!', 'punctuation'],
    ['hey   nova.', 'extra spacing'],
    ['Hey-Nova', 'hyphen'],
    ['hay nova', 'hey heard as hay'],
    ['um hey nova', 'short filler first'],
  ])('%s (%s) wakes, with no command', (text) => {
    expect(splitWake(text)).toEqual({ woke: true, command: '' })
  })

  it('extracts the command spoken in the same breath, keeping its wording', () => {
    expect(splitWake('Hey Nova, turn on the fan')).toEqual({ woke: true, command: 'turn on the fan' })
    expect(splitWake("hey nova don't unlock the door")).toEqual({ woke: true, command: "don't unlock the door" })
  })

  it('joins a wake phrase split across two recognition results', () => {
    expect(splitWake('nova turn on the fan', 'hey')).toEqual({ woke: true, command: 'turn on the fan' })
    expect(splitWake('nova', 'hey')).toEqual({ woke: true, command: '' })
  })

  it.each([
    'turn on the fan',
    'hey there',
    'nova',
    'hey novak how are you',
    'the supernova was bright',
    'they nova',
    'I watched a show about nova and then said hey',
    'my neighbour said hey nova loudly yesterday', // "hey" is not at the start of the utterance
  ])('ordinary speech does not wake: %s', (text) => {
    expect(splitWake(text).woke).toBe(false)
  })

  it.each(['Hey IntelliHome', 'hey intelli home', 'Hey IntelliHome, turn on the fan'])(
    'the old phrase "%s" no longer wakes the assistant',
    (text) => {
      expect(splitWake(text).woke).toBe(false)
    },
  )

  it('normalises transcripts', () => {
    expect(normalizeTranscript('  Hey, Nova!  Turn ON the fan. ')).toBe('hey nova turn on the fan')
  })
})

describe('wake phrase in a live session', () => {
  it('detects a wake phrase the browser split across results, and sends only the command', async () => {
    const { voice, commands } = session()
    voice.start()
    current().say('hey')
    current().say('nova turn on the fan')
    await flush()
    expect(commands).toEqual(['turn on the fan'])
  })

  it('split wake phrase with nothing after it opens the command window', async () => {
    const { voice, states, commands } = session()
    voice.start()
    current().say('hey')
    current().say('Nova.')
    expect(states.at(-1)).toBe('command')
    current().say('turn off the light')
    await flush()
    expect(commands).toEqual(['turn off the light']) // "Hey Nova" itself is never sent
  })

  it('does not join results that are too far apart', () => {
    let clock = 0
    const { voice, states } = session({ now: () => clock })
    voice.start()
    current().say('hey')
    clock += 10_000
    current().say('nova')
    expect(states.at(-1)).toBe('wake')
  })

  it('a repeated wake phrase in the command window is not sent as a command', async () => {
    const { voice, commands } = session()
    voice.start()
    current().say('Hey Nova')
    current().say('hey nova')
    current().say('lock the front door')
    await flush()
    expect(commands).toEqual(['lock the front door'])
  })

  it('the old IntelliHome phrase is ignored while waiting for the wake phrase', async () => {
    const { voice, states, commands } = session()
    voice.start()
    current().say('Hey IntelliHome, turn on the fan')
    await flush()
    expect(commands).toEqual([])
    expect(states.at(-1)).toBe('wake')
  })
})

describe('wake → command transition', () => {
  const live = () => FakeRecognition.instances.filter((r) => r.started && !r.aborted && r.onresult)

  it('exact final transcript "hey nova" opens the command window', () => {
    const { voice, states } = session()
    voice.start()
    current().say('hey nova')
    expect(states.at(-1)).toBe('command')
  })

  it('wakes on interim "hey nova" even if the browser never finalises it (the Edge case)', async () => {
    const { voice, states, commands } = session()
    voice.start()
    current().say('hey nova', false) // shown as "Heard: hey nova"
    expect(states.at(-1)).toBe('command') // regression: stayed in "wake" before

    current().say('turn on the fan')
    await flush()
    expect(commands).toEqual(['turn on the fan'])
  })

  it('handles text left unfinalised when the browser ends the session', async () => {
    const { voice, commands } = session()
    voice.start()
    current().say('hey nova turn on the fan', false)
    current().end() // Edge ends the session without a final result
    await flush()
    expect(commands).toEqual(['turn on the fan'])
  })

  it('wake + command in one final result submits only the command', async () => {
    const { voice, commands } = session()
    voice.start()
    current().say('hey nova', false)
    current().say('hey nova turn on the fan') // interim, then the final of the same utterance
    await flush()
    expect(commands).toEqual(['turn on the fan'])
  })

  it('never submits the wake phrase or its leftover pieces as a command', async () => {
    const { voice, commands, states } = session()
    voice.start()
    current().say('hey nova', false)
    current().say('hey') // a split final: "hey" | "nova"
    current().say('nova')
    current().say('Hey Nova.')
    await flush()
    expect(commands).toEqual([])
    expect(states.at(-1)).toBe('command')
  })

  it('the command window expires back to listening for the wake phrase', async () => {
    const { voice, states, commands } = session()
    voice.start()
    current().say('hey nova', false)
    vi.advanceTimersByTime(8000)
    expect(states.at(-1)).toBe('wake')
    current().say('turn on the fan')
    await flush()
    expect(commands).toEqual([]) // needs the wake phrase again
  })

  it('"yes" after the wake phrase is sent as an ordinary request (the backend decides; it cannot unlock)', async () => {
    const { voice, commands } = session()
    voice.start()
    current().say('Hey Nova')
    current().say('yes')
    await flush()
    expect(commands).toEqual(['yes'])
  })

  it('repeated wake phrases and browser restarts never create duplicate listeners', () => {
    const { voice, states } = session()
    voice.start()
    for (let i = 0; i < 3; i += 1) {
      current().say('hey nova', false)
      current().say('hey nova')
    }
    expect(live()).toHaveLength(1)
    current().end() // the browser ends the session: one replacement, still in the command window
    current().end()
    expect(live()).toHaveLength(1)
    expect(states.at(-1)).toBe('command')
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
    first.say('Hey Nova, turn on the living room fan')
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
    current().say('Hey Nova')
    expect(states.at(-1)).toBe('command')

    current().say('lock the front door')
    await flush()
    expect(commands).toEqual(['lock the front door'])

    current().say('hey nova')
    vi.advanceTimersByTime(8000)
    expect(states.at(-1)).toBe('wake')
    current().say('turn off the light') // after the window, needs the wake phrase again
    await flush()
    expect(commands).toEqual(['lock the front door'])
  })

  it('a pending door confirmation is answered without the wake phrase', async () => {
    const { voice, commands } = session({ reply: { speech: 'Are you sure?', expectsReply: true } })
    voice.start()
    current().say('Hey Nova, unlock the main door')
    await flush()

    current().say('yes, unlock it')
    await flush()
    expect(commands).toEqual(['unlock the main door', 'yes, unlock it'])
  })

  it('ignores interim results', async () => {
    const heard = []
    const { voice, commands } = session({ onHeard: (text) => heard.push(text) })
    voice.start()
    current().say('Hey Nova, turn', false)
    await flush()
    expect(commands).toEqual([])
    expect(heard).toEqual(['Hey Nova, turn'])
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
    current().say('Hey Nova')
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
    expect(voiceStatusLabel({ state: 'wake' })).toBe('Listening for “Hey Nova”')
    expect(voiceStatusLabel({ state: 'processing' }, 'executing')).toBe('Executing…')
    expect(voiceStatusLabel({ state: 'processing' }, 'success')).toBe('Done')
    expect(voiceStatusLabel({ state: 'error', message: 'Microphone access was denied.' })).toBe('Microphone access was denied.')
  })
})
