import { useEffect, useRef, useState } from 'react'
import { useCursor } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { Halo } from './glow'
import { COLORS } from './palette'
import { SceneHtml } from './SceneHtml'
import { deviceStatusLabel } from './visualState'

/** Re-render once when a value changes (needed when the canvas only renders on demand). */
export function useInvalidateOn(...deps) {
  const invalidate = useThree((state) => state.invalidate)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => invalidate(), deps)
}

function SelectionRing({ position, radius, selected, hovered, reducedMotion }) {
  const material = useRef()
  useFrame(({ clock }) => {
    if (!material.current) return
    material.current.opacity = selected
      ? reducedMotion
        ? 0.75
        : 0.55 + 0.3 * Math.sin(clock.elapsedTime * 3)
      : 0.3
  })
  if (!selected && !hovered) return null
  return (
    <mesh position={[position[0], 0.025, position[2]]} rotation-x={-Math.PI / 2}>
      <ringGeometry args={[radius, radius + 0.06, 48]} />
      <meshBasicMaterial
        ref={material}
        color={COLORS.system}
        transparent
        opacity={0.6}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        toneMapped={false}
      />
    </mesh>
  )
}

const TAG_TONES = { on: 'scene-tag-dot--on', off: 'scene-tag-dot--off', secure: 'scene-tag-dot--secure', warning: 'scene-tag-dot--warning' }

function tagTone(device) {
  if (device.device_type === 'door_lock') return device.state?.is_locked ? 'secure' : 'warning'
  return device.state?.is_on ? 'on' : 'off'
}

function DeviceTag({ position, device, selected, alert, prediction }) {
  return (
    <SceneHtml position={position} center style={{ pointerEvents: 'none' }} zIndexRange={[20, 0]}>
      <div className={`scene-tag ${selected ? 'scene-tag--selected' : ''}`}>
        <span className={`scene-tag-dot ${TAG_TONES[tagTone(device)]}`} />
        <span className="scene-tag-name">{device.name}</span>
        <span className="scene-tag-status">{deviceStatusLabel(device)}</span>
        {alert && <span className="scene-tag-badge scene-tag-badge--alert">⚠ Anomaly</span>}
        {!alert && prediction != null && (
          <span className="scene-tag-badge scene-tag-badge--prediction">AI {Math.round(prediction * 100)}%</span>
        )}
      </div>
    </SceneHtml>
  )
}

/** Energy anomaly from Isolation Forest: pulsing red ring and glow at the device. */
function WarningRing({ anchor, reducedMotion }) {
  const material = useRef()
  useFrame(({ clock }) => {
    if (material.current) material.current.opacity = reducedMotion ? 0.8 : 0.45 + 0.4 * Math.abs(Math.sin(clock.elapsedTime * 4))
  })
  const [x, , z] = anchor.base
  return (
    <group>
      <mesh position={[x, 0.03, z]} rotation-x={-Math.PI / 2}>
        <ringGeometry args={[anchor.ring + 0.12, anchor.ring + 0.22, 48]} />
        <meshBasicMaterial
          ref={material}
          color={COLORS.danger}
          transparent
          opacity={0.7}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          toneMapped={false}
        />
      </mesh>
      <Halo position={anchor.target} color={COLORS.danger} opacity={0.55} scale={1.3} />
    </group>
  )
}

/** Click/hover handling, selection ring and floating label shared by every device. */
export function DeviceShell({ device, anchor, selected, onSelect, showTag, reducedMotion, alert = false, prediction = null, children }) {
  const [hovered, setHovered] = useState(false)
  useCursor(hovered && Boolean(onSelect))
  useInvalidateOn(selected, hovered, alert, prediction)

  return (
    <group
      onClick={(event) => {
        event.stopPropagation()
        onSelect?.(device.id)
      }}
      onPointerOver={(event) => {
        event.stopPropagation()
        setHovered(true)
      }}
      onPointerOut={() => setHovered(false)}
    >
      {children}
      <SelectionRing
        position={anchor.base}
        radius={anchor.ring}
        selected={selected}
        hovered={hovered}
        reducedMotion={reducedMotion}
      />
      {alert && <WarningRing anchor={anchor} reducedMotion={reducedMotion} />}
      {(showTag || selected || hovered || alert) && (
        <DeviceTag position={anchor.label} device={device} selected={selected} alert={alert} prediction={prediction} />
      )}
    </group>
  )
}
