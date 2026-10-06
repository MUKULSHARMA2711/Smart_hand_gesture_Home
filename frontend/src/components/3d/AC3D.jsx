import { useMemo, useRef } from 'react'
import { RoundedBox } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { DeviceShell, useInvalidateOn } from './DeviceShell'
import { Halo } from './glow'
import { ANCHORS } from './layout'
import { COLORS } from './palette'
import { SceneHtml } from './SceneHtml'
import { acVisual } from './visualState'

const PARTICLES = 28
const VENT_Y = 1.44
const VENT_Z = -3.12

/** Cool-air particles. Only mounted while the AC is on (and motion is allowed). */
function Airflow({ x, airflow, coolness }) {
  const mesh = useRef()
  const dummy = useMemo(() => new THREE.Object3D(), [])
  const seeds = useMemo(
    () => Array.from({ length: PARTICLES }, (_, i) => ({ phase: i / PARTICLES, offset: ((i * 37) % 23) / 23 - 0.5 })),
    [],
  )
  const color = useMemo(() => new THREE.Color('#e0f2fe').lerp(new THREE.Color('#38bdf8'), coolness), [coolness])

  useFrame(({ clock }) => {
    if (!mesh.current) return
    const time = clock.elapsedTime * (0.35 + 0.45 * airflow)
    seeds.forEach(({ phase, offset }, i) => {
      const t = (time + phase) % 1
      dummy.position.set(x + offset * 1.25, VENT_Y - t * 1.05 - t * t * 0.25, VENT_Z + t * 1.7)
      dummy.scale.setScalar((1 - t) * (0.6 + airflow * 0.6))
      dummy.updateMatrix()
      mesh.current.setMatrixAt(i, dummy.matrix)
    })
    mesh.current.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, PARTICLES]} frustumCulled={false}>
      <sphereGeometry args={[0.03, 6, 6]} />
      <meshBasicMaterial color={color} transparent opacity={0.75} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false} />
    </instancedMesh>
  )
}

/** Wall-mounted split AC with airflow and its real set point. */
export function AC3D({ device, reducedMotion, ...shell }) {
  const visual = acVisual(device.state)
  const anchor = ANCHORS.ac
  const x = anchor.base[0]
  useInvalidateOn(visual.on, visual.temperature)

  return (
    <DeviceShell device={device} anchor={anchor} reducedMotion={reducedMotion} {...shell}>
      <RoundedBox args={[1.5, 0.42, 0.26]} radius={0.07} smoothness={3} position={[x, 1.62, -3.3]}>
        <meshStandardMaterial color="#d6dde8" roughness={0.45} metalness={0.05} />
      </RoundedBox>
      <mesh position={[x, VENT_Y, VENT_Z - 0.04]}>
        <boxGeometry args={[1.3, 0.035, 0.02]} />
        <meshStandardMaterial
          color="#0f172a"
          emissive={COLORS.system}
          emissiveIntensity={visual.on ? 1.2 + visual.airflow * 1.8 : 0}
          toneMapped={false}
        />
      </mesh>
      <mesh position={[x + 0.6, 1.73, -3.16]}>
        <sphereGeometry args={[0.025, 8, 8]} />
        <meshBasicMaterial color={visual.on ? COLORS.success : '#334155'} toneMapped={false} />
      </mesh>
      {visual.on && <Halo position={[x, VENT_Y - 0.2, VENT_Z + 0.3]} color={COLORS.system} opacity={0.18 + visual.airflow * 0.25} scale={1.8} />}
      {visual.on && !reducedMotion && <Airflow x={x} airflow={visual.airflow} coolness={visual.coolness} />}
      <SceneHtml position={[x, 1.62, -3.14]} center transform distanceFactor={4} style={{ pointerEvents: 'none' }}>
        <span className={`scene-ac-display ${visual.on ? 'scene-ac-display--on' : ''}`}>{visual.temperature}°</span>
      </SceneHtml>
    </DeviceShell>
  )
}
