import { useState } from 'react'
import { CameraPanel } from '../components/gestures/CameraPanel'
import { DetectionPanel } from '../components/gestures/DetectionPanel'
import { GestureGuide } from '../components/gestures/GestureGuide'
import { GestureHistory } from '../components/gestures/GestureHistory'
import { LastActionPanel } from '../components/gestures/LastActionPanel'
import { TargetSelector } from '../components/gestures/TargetSelector'
import { useGestureControl } from '../hooks/useGestureControl'
import { useGestureRecognition } from '../hooks/useGestureRecognition'

export function GesturePage({ home, refreshHome }) {
  const devices = home?.devices ?? []
  const deviceNames = Object.fromEntries(devices.map((device) => [device.id, device.name]))
  const control = useGestureControl({ devices, onDevicesChanged: refreshHome })

  const [cameraOn, setCameraOn] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const recognition = useGestureRecognition({
    active: cameraOn,
    threshold: control.config.confidenceThreshold,
    onCommit: control.execute,
    restartKey: attempt,
  })

  return (
    <div className="space-y-8">
      {control.configError && (
        <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
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
          <GestureGuide intents={control.config.intents} blockedActions={control.config.blockedActions} />
        </div>
        <div className="space-y-6 lg:col-span-2">
          <DetectionPanel
            live={recognition.live}
            running={recognition.status === 'running'}
            threshold={control.config.confidenceThreshold}
            intents={control.config.intents}
          />
          <TargetSelector devices={devices} selectedId={control.selectedId} onSelect={control.setSelectedId} />
          <LastActionPanel lastAction={control.lastAction} deviceNames={deviceNames} />
        </div>
      </div>

      <GestureHistory events={control.events} deviceNames={deviceNames} />
    </div>
  )
}
