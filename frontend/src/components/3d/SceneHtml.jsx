import { createContext, useContext } from 'react'
import { Html } from '@react-three/drei'

/**
 * A DOM layer owned by HouseView that sits exactly over the canvas. Scene labels are
 * portalled into it instead of drei's default target (R3F's internal wrapper), which
 * otherwise throws "removeChild … not a child of this node" when a page with the
 * canvas unmounts.
 */
export const LabelLayerContext = createContext(null)

export function SceneHtml(props) {
  const layer = useContext(LabelLayerContext)
  return <Html portal={layer ?? undefined} {...props} />
}
