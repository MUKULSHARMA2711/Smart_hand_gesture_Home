import { useEffect, useRef, useState } from 'react'
import { AdjustmentPanel } from '../components/gestures/AdjustmentPanel'
import { CameraPanel } from '../components/gestures/CameraPanel'
import { DetectionPanel } from '../components/gestures/DetectionPanel'
import { GestureGuide } from '../components/gestures/GestureGuide'
import { GestureHistory } from '../components/gestures/GestureHistory'
import { LastActionPanel } from '../components/gestures/LastActionPanel'
import { TargetSelector } from '../components/gestures/TargetSelector'
import { HouseView } from '../components/house/HouseView'
import { OrbStatus } from '../components/OrbStatus'
import { Panel } from '../components/Panel'
import { useGestureControl } from '../hooks/useGestureControl'
import { useGestureRecognition } from '../hooks/useGestureRecognition'
import { useAssistantContext } from '../state/AssistantContext'
import { useCommandFx } from '../state/CommandFxContext'
import { useHomeData } from '../state/HomeDataContext'

export function GesturePage() {
  const { home, refresh, deviceNames, connected } = useHomeData()
  const { emit } = useCommandFx()
  const { setGestureActive, orbState } = useAssistantContext()
  const devices = home?.devices ?? []
  const control = useGestureControl({ devices, onDevicesChanged: refresh, connected })

  const [cameraOn, setCameraOn] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const recognition = useGestureRecognition({
    active: cameraOn,
    threshold: control.config.confidenceThreshold,
    onCommit: control.execute,
    onPinch: control.onPinch,
    restartKey: attempt,
  })

  // The AI core shows "listening" while the gesture camera is running.
  useEffect(() => {
    setGestureActive(recognition.status === 'running')
    return () => setGestureActive(false)
  }, [recognition.status, setGestureActive])

  // Visualise each finished gesture command from its real backend result.
  const visualised = useRef(null)
  useEffect(() => {
    const action = control.lastAction
    if (!action || action.status === 'pending' || visualised.current === action.at) return
    visualised.current = action.at
    if (action.intent === 'SELECT') return // targeting only; the selection ring moves instead
    emit({ source: 'gesture', deviceId: action.targetId, status: action.status === 'success' ? 'executed' : 'rejected' })
  }, [control.lastAction, emit])

  return (
    <div className="space-y-8">
      {control.configError && (
        <p role="alert" className="rounded-xl border border-amber-900 bg-amber-950 p-3 text-sm text-amber-200">
          Could not load gesture settings ({control.configError}). Using defaults.
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-3">
          <CameraPanel
            {...recognition}
            cameraOn={cameraOn}
            onToggle={() => setCameraOn((on) => !on)}
            onRetry={() => setAttempt((n) => n + 1)}
          />
          <Panel title="Command visualization">
            <div className="scene-frame h-90">
              <HouseView selectedId={control.selectedId} onSelect={(id) => id && control.setSelectedId(id)} compact showGestureInput />
              <OrbStatus state={orbState} className="absolute top-3 right-3" />
              {control.adjustment?.status === 'adjusting' && (
                <p className="scene-sensors absolute bottom-3 left-3" aria-hidden="true">
                  {control.adjustment.deviceName} · {control.adjustment.range.title}: {control.adjustment.value}
                  {control.adjustment.range.unit} (preview)
                </p>
              )}
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Confirmed gestures send a command beam from the gesture input to the selected device. The device changes
              only when the backend reports its new state.
            </p>
          </Panel>
        </div>
        <div className="space-y-6 lg:col-span-2">
          <DetectionPanel
            live={recognition.live}
            running={recognition.status === 'running'}
            threshold={control.config.confidenceThreshold}
            intents={control.config.intents}
          />
          <TargetSelector devices={devices} selectedId={control.selectedId} onSelect={control.setSelectedId} />
          <AdjustmentPanel adjustment={control.adjustment} />
          <LastActionPanel lastAction={control.lastAction} deviceNames={deviceNames} />
          <GestureGuide intents={control.config.intents} blockedActions={control.config.blockedActions} />
        </div>
      </div>

      <GestureHistory events={control.events} deviceNames={deviceNames} />
    </div>
  )
}
