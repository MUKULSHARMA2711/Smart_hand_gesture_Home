import { forwardRef } from 'react'
import * as THREE from 'three'

let glowTexture = null

/** A soft radial gradient generated once in code (no image assets). */
export function getGlowTexture() {
  if (glowTexture) return glowTexture
  const size = 128
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')
  const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  gradient.addColorStop(0, 'rgba(255,255,255,1)')
  gradient.addColorStop(0.25, 'rgba(255,255,255,0.55)')
  gradient.addColorStop(0.6, 'rgba(255,255,255,0.12)')
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  context.fillStyle = gradient
  context.fillRect(0, 0, size, size)
  glowTexture = new THREE.CanvasTexture(canvas)
  glowTexture.colorSpace = THREE.SRGBColorSpace
  return glowTexture
}

/** Additive camera-facing glow — a cheap stand-in for bloom. */
export const Halo = forwardRef(function Halo({ color = '#ffffff', opacity = 1, scale = 1, ...props }, ref) {
  return (
    <sprite ref={ref} scale={[scale, scale, scale]} {...props}>
      <spriteMaterial
        map={getGlowTexture()}
        color={color}
        transparent
        opacity={opacity}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        toneMapped={false}
      />
    </sprite>
  )
})

/** Flat additive glow lying on a surface (e.g. a pool of lamp light on the floor). */
export const FloorGlow = forwardRef(function FloorGlow({ color = '#ffffff', opacity = 1, size = 1, ...props }, ref) {
  return (
    <mesh rotation-x={-Math.PI / 2} {...props}>
      <planeGeometry args={[size, size]} />
      <meshBasicMaterial
        ref={ref}
        map={getGlowTexture()}
        color={color}
        transparent
        opacity={opacity}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        toneMapped={false}
      />
    </mesh>
  )
})
