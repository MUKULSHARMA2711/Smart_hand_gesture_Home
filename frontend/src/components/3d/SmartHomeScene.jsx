import { Grid, OrbitControls } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'
import { AC3D } from './AC3D'
import { AIOrb } from './AIOrb'
import { CommandBeam, ImpactPulse } from './CommandBeam'
import { Door3D } from './Door3D'
import { Fan3D } from './Fan3D'
import { Halo } from './glow'
import { HouseModel } from './HouseModel'
import { anchorFor, GESTURE_ORIGIN, ORB_POSITION } from './layout'
import { Light3D } from './Light3D'
import { COLORS } from './palette'
import { LabelLayerContext } from './SceneHtml'

const DEVICE_COMPONENTS = { light: Light3D, fan: Fan3D, ac: AC3D, door_lock: Door3D }
const SOURCE_COLORS = { ai_agent: COLORS.system, gesture: COLORS.gesture, frontend: COLORS.success }

function Effects({ effects, devices, reducedMotion }) {
  const byId = Object.fromEntries(devices.map((device) => [device.id, device]))
  return effects.map((fx) => {
    const anchor = anchorFor(byId[fx.deviceId])
    if (!anchor) return null
    const color = SOURCE_COLORS[fx.source] ?? COLORS.system
    if (fx.source === 'frontend') return <ImpactPulse key={fx.id} at={anchor.target} color={color} startAt={fx.startAt} />
    const from = fx.source === 'gesture' ? GESTURE_ORIGIN : ORB_POSITION
    return (
      <CommandBeam
        key={fx.id}
        from={from}
        to={anchor.target}
        color={color}
        status={fx.status}
        startAt={fx.startAt}
        reducedMotion={reducedMotion}
      />
    )
  })
}

/**
 * Pure presentation of backend state. Every prop comes from the backend (devices,
 * environment, energy) or from real request lifecycles (orbState, effects).
 */
export default function SmartHomeScene({
  devices = [],
  selectedId,
  onSelect,
  orbState = 'idle',
  effects = [],
  compact = false,
  showGestureInput = false,
  alerts = new Set(),
  predictions = {},
  reducedMotion = false,
  active = true,
  labelLayer = null,
}) {
  const frameloop = !active ? 'never' : reducedMotion ? 'demand' : 'always'
  return (
    <Canvas
      frameloop={frameloop}
      dpr={[1, 1.75]}
      camera={{ position: compact ? [10.4, 9.2, 12.2] : [11.2, 9.8, 13], fov: compact ? 36 : 38 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      onPointerMissed={() => onSelect?.(null)}
    >
      <LabelLayerContext.Provider value={labelLayer}>
      <color attach="background" args={[COLORS.background]} />
      <fog attach="fog" args={[COLORS.background, 24, 46]} />
      <ambientLight intensity={0.7} color="#9db4ff" />
      <hemisphereLight args={['#4f73c9', '#050a18', 0.6]} />
      <directionalLight position={[6, 12, 6]} intensity={0.9} color="#d6e2ff" />

      <Grid
        position={[0, -0.21, 0]}
        args={[60, 60]}
        cellSize={0.5}
        cellThickness={0.5}
        cellColor="#10243a"
        sectionSize={2.5}
        sectionThickness={0.9}
        sectionColor="#14506e"
        fadeDistance={34}
        fadeStrength={1.6}
        infiniteGrid
      />

      <HouseModel showLabels={!compact} />
      {devices.map((device) => {
        const Component = DEVICE_COMPONENTS[device.device_type]
        return Component ? (
          <Component
            key={device.id}
            device={device}
            selected={device.id === selectedId}
            onSelect={onSelect}
            showTag={!compact}
            alert={alerts.has(device.id)}
            prediction={predictions[device.id] ?? null}
            reducedMotion={reducedMotion}
          />
        ) : null
      })}

      <AIOrb state={orbState} position={ORB_POSITION} reducedMotion={reducedMotion} showLabel={false} />
      {showGestureInput && <Halo position={GESTURE_ORIGIN} color={COLORS.gesture} opacity={0.7} scale={0.9} />}
      {/* With reduced motion the device change itself is the feedback; no travelling effects. */}
      {!reducedMotion && <Effects effects={effects} devices={devices} reducedMotion={reducedMotion} />}

      <OrbitControls
        makeDefault
        target={[0.3, 0.45, 0.6]}
        enablePan={false}
        enableDamping
        dampingFactor={0.08}
        minDistance={11}
        maxDistance={26}
        minPolarAngle={0.55}
        maxPolarAngle={1.18}
        minAzimuthAngle={-0.35}
        maxAzimuthAngle={1.45}
        rotateSpeed={0.6}
        zoomSpeed={0.6}
      />
      </LabelLayerContext.Provider>
    </Canvas>
  )
}
