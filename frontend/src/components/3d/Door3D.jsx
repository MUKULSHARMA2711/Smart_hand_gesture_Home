import { useRef } from 'react'
import { Edges } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { DeviceShell, useInvalidateOn } from './DeviceShell'
import { Halo } from './glow'
import { ANCHORS, DOOR } from './layout'
import { COLORS } from './palette'
import { approach, doorVisual } from './visualState'

/** Front door: closed with a green indicator when locked, ajar with amber when unlocked. */
export function Door3D({ device, reducedMotion, ...shell }) {
  const visual = doorVisual(device.state)
  const hinge = useRef()
  const indicatorColor = visual.locked ? COLORS.success : COLORS.warning
  useInvalidateOn(visual.angle)

  useFrame((_, delta) => {
    if (!hinge.current) return
    hinge.current.rotation.y = reducedMotion
      ? visual.angle
      : approach(hinge.current.rotation.y, visual.angle, 3, Math.min(delta, 0.1))
  })

  const frameX = DOOR.hingeX + DOOR.width + 0.08
  return (
    <DeviceShell device={device} anchor={ANCHORS.door_lock} reducedMotion={reducedMotion} {...shell}>
      {/* Frame */}
      {[DOOR.hingeX - 0.06, frameX].map((px) => (
        <mesh key={px} position={[px, 1.03, DOOR.z]}>
          <boxGeometry args={[0.1, 2.06, 0.18]} />
          <meshStandardMaterial color="#1e293b" roughness={0.7} />
          <Edges color={COLORS.wallEdge} />
        </mesh>
      ))}
      <mesh position={[(DOOR.hingeX + frameX) / 2 - 0.03, 2.08, DOOR.z]}>
        <boxGeometry args={[DOOR.width + 0.26, 0.1, 0.18]} />
        <meshStandardMaterial color="#1e293b" roughness={0.7} />
        <Edges color={COLORS.wallEdge} />
      </mesh>
      {/* Leaf, pivoting on its hinge */}
      <group ref={hinge} position={[DOOR.hingeX, 0, DOOR.z]}>
        <mesh position={[DOOR.width / 2, DOOR.height / 2 + 0.02, 0]}>
          <boxGeometry args={[DOOR.width, DOOR.height, 0.07]} />
          <meshStandardMaterial color="#55688a" roughness={0.55} metalness={0.15} />
          <Edges color="#4b8bb0" />
        </mesh>
        <mesh position={[DOOR.width - 0.15, 1.0, 0.06]}>
          <boxGeometry args={[0.04, 0.22, 0.04]} />
          <meshStandardMaterial color="#cbd5e1" metalness={0.8} roughness={0.25} />
        </mesh>
      </group>
      {/* Lock indicator on the frame */}
      <mesh position={[frameX, 1.05, DOOR.z + 0.1]}>
        <boxGeometry args={[0.05, 0.16, 0.03]} />
        <meshBasicMaterial color={indicatorColor} toneMapped={false} />
      </mesh>
      <Halo position={[frameX, 1.05, DOOR.z + 0.12]} color={indicatorColor} opacity={0.85} scale={0.55} />
    </DeviceShell>
  )
}
