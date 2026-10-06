/**
 * Browser voice control: "Hey IntelliHome" → command → the existing AI agent.
 *
 * Uses the browser's SpeechRecognition (Chrome / Edge). Only recognised *text* goes to the
 * IntelliHome backend, through the same /ai/command pipeline as typed requests, so voice
 * gets the same validation, door policy and CommandService path. Independent of React so
 * every cleanup path can be tested: stop() (or any fatal error) releases the recogniser,
 * its handlers and all timers, and nothing restarts afterwards.
 *
 * States: off · wake (listening for the wake phrase) · command (listening for a request) ·
 * processing · speaking · error · unsupported.
 */

// "Hey IntelliHome" as recognisers tend to transcribe it.
const WAKE = /\b(?:hey|hi|okay|ok)[\s,!.]+intelli[\s-]?(?:home|homes)\b[\s,!.:]*/i

export function getSpeechRecognition(scope = globalThis) {
  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null
}

/** Whether `text` contains the wake phrase, and the command spoken after it (if any). */
export function splitWake(text) {
  const match = WAKE.exec(text)
  if (!match) return { woke: false, command: '' }
  return { woke: true, command: text.slice(match.index + match[0].length).trim() }
}

const ERROR_MESSAGES = {
  'not-allowed': 'Microphone access was denied. Allow it in the browser to use voice.',
  'service-not-allowed': 'Speech recognition is not allowed in this browser or context.',
  'audio-capture': 'No microphone was found.',
  network: "The browser's speech service could not be reached. Voice needs an internet connection here.",
  'language-not-supported': 'Speech recognition does not support this language here.',
}

export function createVoiceSession({
  Recognition,
  onCommand, // async (text) => ({ speech, expectsReply })
  speak = async () => {},
  onState = () => {},
  onHeard = () => {},
  sound = () => {},
  lang = 'en-US',
  commandWindowMs = 8000,
  maxRestarts = 5,
  restartWindowMs = 10_000,
  setTimer = (fn, ms) => setTimeout(fn, ms),
  clearTimer = (id) => clearTimeout(id),
  now = () => Date.now(),
}) {
  let active = false
  let paused = false // recognition deliberately stopped while processing / speaking
  let mode = 'wake'
  let recognizer = null
  let commandTimer = null
  let restarts = []

  const setState = (state, message = null) => onState({ state, message })

  function release() {
    clearTimer(commandTimer)
    commandTimer = null
    if (recognizer) {
      recognizer.onresult = recognizer.onerror = recognizer.onend = null
      try {
        recognizer.abort()
      } catch {
        // already stopped
      }
      recognizer = null
    }
  }

  function fail(message) {
    active = false
    release()
    sound('error')
    setState('error', message)
  }

  function listen() {
    const recognition = new Recognition()
    recognition.lang = lang
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1
    recognition.onresult = handleResult
    recognition.onerror = handleError
    recognition.onend = handleEnd
    recognizer = recognition
    try {
      recognition.start()
    } catch (error) {
      fail(`Could not start speech recognition: ${error?.message ?? error}`)
      return
    }
    setState(mode)
  }

  function handleResult(event) {
    if (!active || paused) return
    let interim = ''
    const finals = []
    for (let i = event.resultIndex ?? 0; i < event.results.length; i += 1) {
      const result = event.results[i]
      const text = result[0]?.transcript ?? ''
      if (result.isFinal) finals.push(text.trim())
      else interim += text
    }
    onHeard(interim || finals.join(' '))
    for (const text of finals) {
      if (!active || paused) break
      handleFinal(text)
    }
  }

  function handleFinal(text) {
    const { woke, command } = splitWake(text)
    if (mode === 'wake') {
      if (!woke) return // everything else is ignored until the wake phrase
      sound('wake')
      if (command) dispatch(command)
      else enterCommandMode()
      return
    }
    const request = woke ? command : text // "Hey IntelliHome" may be repeated
    if (request) dispatch(request)
  }

  function enterCommandMode() {
    mode = 'command'
    setState('command')
    clearTimer(commandTimer)
    commandTimer = setTimer(() => {
      commandTimer = null
      if (active && !paused && mode === 'command') {
        mode = 'wake'
        setState('wake', 'No command heard.')
      }
    }, commandWindowMs)
  }

  async function dispatch(text) {
    clearTimer(commandTimer)
    commandTimer = null
    paused = true
    if (recognizer) {
      recognizer.onresult = recognizer.onerror = recognizer.onend = null
      try {
        recognizer.abort() // do not listen while processing or speaking (it would hear itself)
      } catch {
        // already stopped
      }
      recognizer = null
    }
    setState('processing', text)
    let result
    try {
      result = await onCommand(text)
    } catch {
      result = { speech: 'Sorry, something went wrong. Nothing was changed.', expectsReply: false }
    }
    if (!active) return
    if (result?.speech) {
      setState('speaking', result.speech)
      await speak(result.speech)
      if (!active) return
    }
    paused = false
    // A pending confirmation is answered without the wake phrase.
    mode = result?.expectsReply ? 'command' : 'wake'
    listen()
    if (mode === 'command' && active) enterCommandMode()
  }

  function handleError(event) {
    const code = event?.error
    if (code === 'no-speech' || code === 'aborted') return // onend restarts the session
    fail(ERROR_MESSAGES[code] ?? `Speech recognition error: ${code ?? 'unknown'}.`)
  }

  function handleEnd() {
    if (!active || paused) return
    // Browsers end recognition after silence or a time limit: restart, but not forever.
    const t = now()
    restarts = restarts.filter((at) => t - at < restartWindowMs)
    if (restarts.length >= maxRestarts) {
      fail('Speech recognition keeps stopping, so voice was turned off. Try again.')
      return
    }
    restarts.push(t)
    recognizer = null
    listen()
  }

  return {
    start() {
      if (!Recognition) {
        setState('unsupported', 'Voice control needs a browser with speech recognition, such as Chrome or Edge.')
        return
      }
      if (active) return
      active = true
      paused = false
      mode = 'wake'
      restarts = []
      listen()
    },
    stop() {
      const wasActive = active
      active = false
      paused = false
      release()
      if (wasActive) setState('off')
    },
    get active() {
      return active
    },
  }
}

/** Speak `text` with the browser's speech synthesis; resolves when done (or if unavailable). */
export function speakText(text, synth = globalThis.speechSynthesis, Utterance = globalThis.SpeechSynthesisUtterance) {
  if (!text || !synth || !Utterance) return Promise.resolve()
  return new Promise((resolve) => {
    let done = false
    const finish = () => {
      if (done) return
      done = true
      clearTimeout(timer)
      resolve()
    }
    // Some browsers never fire onend for long text: never wait forever.
    const timer = setTimeout(finish, Math.min(20_000, 2000 + text.length * 90))
    const utterance = new Utterance(text)
    utterance.lang = 'en-US'
    utterance.onend = finish
    utterance.onerror = finish
    synth.cancel()
    synth.speak(utterance)
  })
}

export function cancelSpeech(synth = globalThis.speechSynthesis) {
  try {
    synth?.cancel()
  } catch {
    // not available
  }
}

/** Short audio cues (Web Audio, no files). Silent where audio is unavailable. */
let audioContext = null
export function chime(kind) {
  try {
    const AudioCtx = globalThis.AudioContext ?? globalThis.webkitAudioContext
    if (!AudioCtx) return
    audioContext ??= new AudioCtx()
    const t = audioContext.currentTime
    const oscillator = audioContext.createOscillator()
    const gain = audioContext.createGain()
    oscillator.frequency.value = kind === 'error' ? 220 : 880
    gain.gain.setValueAtTime(0.0001, t)
    gain.gain.exponentialRampToValueAtTime(0.06, t + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.2)
    oscillator.connect(gain).connect(audioContext.destination)
    oscillator.start(t)
    oscillator.stop(t + 0.22)
  } catch {
    // audio is optional
  }
}
