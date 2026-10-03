import { DeviceCard } from '../components/DeviceCard'
import { EnvironmentPanel } from '../components/EnvironmentPanel'
import { EventLog } from '../components/EventLog'
import { SectionHeading } from '../components/Panel'

export function DashboardPage({ home, events, pendingDeviceId, sendCommand }) {
  const deviceNames = Object.fromEntries(home.devices.map((device) => [device.id, device.name]))

  return (
    <div className="space-y-8">
      <EnvironmentPanel environment={home.environment} energy={home.energy} />

      <section aria-labelledby="devices-heading">
        <div className="mb-3">
          <SectionHeading id="devices-heading">Devices</SectionHeading>
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

      <EventLog events={events} deviceNames={deviceNames} />
    </div>
  )
}
