import { useMemo, useState } from 'react'
import { QuickCommand } from '../components/assistant/QuickCommand'
import { EventConsole } from '../components/console/EventConsole'
import { DeviceCard } from '../components/DeviceCard'
import { HomeHealthPanel } from '../components/HomeHealthPanel'
import { PredictionCard } from '../components/ml/PredictionCard'
import { askAI } from '../lib/ml'
import { DeviceInspector } from '../components/house/DeviceInspector'
import { HouseView } from '../components/house/HouseView'
import { SceneSensors } from '../components/house/SceneSensors'
import { OrbStatus } from '../components/OrbStatus'
import { SectionHeading } from '../components/Panel'
import { SensorStrip } from '../components/SensorStrip'
import { buildActivityFeed } from '../state/activityFeed'
import { useAssistantContext } from '../state/AssistantContext'
import { useHomeData } from '../state/HomeDataContext'

export function HomePage() {
  const { home, events, gestureEvents, aiInteractions, deviceNames, sendCommand, pendingDeviceId, ml } = useHomeData()
  const { orbState, send } = useAssistantContext()
  const [selectedId, setSelectedId] = useState(null)
  const feed = useMemo(
    () => buildActivityFeed({ deviceEvents: events, gestureEvents, aiInteractions, deviceNames }),
    [events, gestureEvents, aiInteractions, deviceNames],
  )

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="scene-frame h-[640px]" aria-label="3D view of the home">
          <HouseView selectedId={selectedId} onSelect={setSelectedId} />
          <div className="pointer-events-none absolute top-4 left-5 space-y-3">
            <div>
              <p className="text-[11px] font-semibold tracking-[0.3em] text-cyan-300/80 uppercase">Digital twin</p>
              <p className="text-xs text-slate-400">Live backend state · drag to orbit · click a device</p>
            </div>
            <SceneSensors environment={home.environment} energy={home.energy} />
          </div>
          <OrbStatus state={orbState} className="absolute top-4 right-5" />
          <div className="pointer-events-none absolute inset-x-5 bottom-5">
            <QuickCommand />
          </div>
        </section>

        <aside className="space-y-6">
          <DeviceInspector deviceId={selectedId} onClose={() => setSelectedId(null)} />
          <PredictionCard
            prediction={ml.prediction}
            onAskAI={() => askAI(send, `Why is the ${ml.prediction?.device_name ?? 'fan'} recommended?`)}
          />
          <HomeHealthPanel home={home} anomalies={ml.anomalies} />
          <EventConsole entries={feed} limit={7} />
        </aside>
      </div>

      <SensorStrip home={home} />

      <section aria-labelledby="devices-heading">
        <div className="mb-3">
          <SectionHeading id="devices-heading">Device controls</SectionHeading>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {home.devices.map((device) => (
            <DeviceCard
              key={device.id}
              device={device}
              busy={pendingDeviceId === device.id}
              onCommand={(action, value) => sendCommand(device.id, action, value)}
            />
          ))}
        </div>
      </section>
    </div>
  )
}
