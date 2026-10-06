import { Component, lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useReducedMotion } from 'motion/react'
import { useAssistantContext, useDisplayDevices } from '../../state/AssistantContext'
import { useCommandFx } from '../../state/CommandFxContext'
import { useHomeData } from '../../state/HomeDataContext'
import { anomalousDeviceIds, predictedDevices } from '../../lib/ml'
import { FloorPlan2D } from './FloorPlan2D'

// Three.js is only downloaded when a page actually shows the house.
const SmartHomeScene = lazy(() => import('../3d/SmartHomeScene'))

function hasWebGL() {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(window.WebGLRenderingContext && (canvas.getContext('webgl2') || canvas.getContext('webgl')))
  } catch {
    return false
  }
}

class SceneErrorBoundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch(error) {
    console.warn('3D scene failed, showing the 2D plan instead.', error)
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

/** Pause rendering while the canvas is scrolled out of view. */
function useInView(ref) {
  const [inView, setInView] = useState(true)
  useEffect(() => {
    if (!ref.current || !('IntersectionObserver' in window)) return undefined
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: 0.01 })
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [ref])
  return inView
}

/**
 * The live house: backend devices (via HomeData / AssistantContext), the AI core state
 * and real command effects. Falls back to a 2D plan without WebGL.
 */
export function HouseView({ selectedId, onSelect, compact = false, showGestureInput = false }) {
  const devices = useDisplayDevices()
  const { orbState } = useAssistantContext()
  const { effects } = useCommandFx()
  const { ml } = useHomeData()
  const alerts = anomalousDeviceIds(ml.anomalies)
  const predictions = predictedDevices(ml.prediction)
  const reducedMotion = Boolean(useReducedMotion())
  const container = useRef(null)
  const labelLayer = useRef(null)
  const inView = useInView(container)
  const [webgl] = useState(hasWebGL)

  const fallback = (
    <FloorPlan2D
      devices={devices}
      selectedId={selectedId}
      onSelect={onSelect}
      alerts={alerts}
      reason={webgl ? '3D view failed to start; showing the 2D plan.' : 'WebGL is not available in this browser; showing the 2D plan.'}
    />
  )

  return (
    <div ref={container} className="relative h-full w-full">
      {!webgl ? (
        fallback
      ) : (
        <SceneErrorBoundary fallback={fallback}>
          <Suspense fallback={<div className="grid h-full place-items-center text-sm text-slate-500">Loading 3D view…</div>}>
            <SmartHomeScene
              devices={devices}
              selectedId={selectedId}
              onSelect={onSelect}
              orbState={orbState}
              effects={effects}
              compact={compact}
              showGestureInput={showGestureInput}
              reducedMotion={reducedMotion}
              active={inView}
              labelLayer={labelLayer}
              alerts={alerts}
              predictions={predictions}
            />
          </Suspense>
        </SceneErrorBoundary>
      )}
      {/* Scene labels are portalled here (see 3d/SceneHtml.jsx). */}
      <div ref={labelLayer} className="pointer-events-none absolute inset-0 overflow-hidden" />
    </div>
  )
}
