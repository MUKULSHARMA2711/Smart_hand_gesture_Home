import { useEffect, useRef, useState } from 'react'
import { useCursor } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
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

function DeviceTag({ position, device, selected }) {
  return (
    <SceneHtml position={position} center style={{ pointerEvents: 'none' }} zIndexRange={[20, 0]}>
      <div className={`scene-tag ${selected ? 'scene-tag--selected' : ''}`}>
        <span className={`scene-tag-dot ${TAG_TONES[tagTone(device)]}`} />
        <span className="scene-tag-name">{device.name}</span>
        <span className="scene-tag-status">{deviceStatusLabel(device)}</span>
      </div>
    </SceneHtml>
  )
}

/** Click/hover handling, selection ring and floating label shared by every device. */
export function DeviceShell({ device, anchor, selected, onSelect, showTag, reducedMotion, children }) {
  const [hovered, setHovered] = useState(false)
  useCursor(hovered && Boolean(onSelect))
  useInvalidateOn(selected, hovered)

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
      {(showTag || selected || hovered) && <DeviceTag position={anchor.label} device={device} selected={selected} />}
    </group>
  )
}
