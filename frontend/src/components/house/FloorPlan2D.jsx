import { connectivityLabel, deviceStatusLabel } from '../3d/visualState'

/** Non-3D fallback: a top-down plan with the same real device state and selection. */
const POSITIONS = {
  light: { x: 240, y: 300 },
  fan: { x: 70, y: 70 },
  ac: { x: 400, y: 50 },
  door_lock: { x: 395, y: 345 },
}

function tone(device) {
  if (device.device_type === 'door_lock') return device.state?.is_locked ? '#34d399' : '#fbbf24'
  return device.state?.is_on ? '#38bdf8' : '#475569'
}

export function FloorPlan2D({ devices, selectedId, onSelect, reason, alerts = new Set() }) {
  return (
    <div className="flex h-full flex-col">
      <svg viewBox="0 0 500 360" className="h-full w-full" role="img" aria-label="Floor plan of the home with device states">
        <rect x="10" y="10" width="480" height="340" rx="10" fill="#0b1324" stroke="#1e3a5f" strokeWidth="2" />
        <line x1="298" y1="10" x2="298" y2="190" stroke="#1e3a5f" strokeWidth="2" />
        <line x1="298" y1="230" x2="460" y2="230" stroke="#1e3a5f" strokeWidth="2" />
        {[
          ['Living room', 30, 340],
          ['Bedroom', 312, 32],
          ['Entrance', 312, 252],
        ].map(([label, x, y]) => (
          <text key={label} x={x} y={y} fill="#64748b" fontSize="12" style={{ textTransform: 'uppercase', letterSpacing: 1 }}>
            {label}
          </text>
        ))}
        {devices.map((device) => {
          const point = POSITIONS[device.device_type]
          if (!point) return null
          const selected = device.id === selectedId
          return (
            <g
              key={device.id}
              role="button"
              tabIndex={0}
              aria-label={`${device.name}: ${[deviceStatusLabel(device), connectivityLabel(device)].filter(Boolean).join(', ')}`}
              onClick={() => onSelect?.(device.id)}
              onKeyDown={(event) => event.key === 'Enter' && onSelect?.(device.id)}
              className="cursor-pointer"
            >
              {selected && <circle cx={point.x} cy={point.y} r="24" fill="none" stroke="#38bdf8" strokeWidth="2" />}
              {alerts.has(device.id) && (
                <circle cx={point.x} cy={point.y} r="29" fill="none" stroke="#f87171" strokeWidth="2" strokeDasharray="4 3" />
              )}
              <circle cx={point.x} cy={point.y} r="15" fill={tone(device)} opacity="0.9" />
              <text x={point.x} y={point.y + 34} textAnchor="middle" fill="#e2e8f0" fontSize="11">
                {device.name}
              </text>
              <text x={point.x} y={point.y + 48} textAnchor="middle" fill="#94a3b8" fontSize="10">
                {deviceStatusLabel(device)}
              </text>
            </g>
          )
        })}
      </svg>
      {reason && <p className="px-4 pb-3 text-xs text-slate-400">{reason}</p>}
    </div>
  )
}
