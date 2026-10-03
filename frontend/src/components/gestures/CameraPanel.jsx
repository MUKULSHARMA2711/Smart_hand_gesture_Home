import { Panel } from '../Panel'

const BUTTON =
  'rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500'

function Overlay({ status, error, onStart }) {
  if (status === 'loading') {
    return <p className="text-sm text-slate-200">Starting camera and loading the hand model…</p>
  }
  if (status === 'error') {
    return (
      <div className="max-w-sm space-y-3 text-center">
        <p className="text-sm text-red-200">{error}</p>
        <button type="button" onClick={onStart} className={`${BUTTON} bg-white text-slate-900 hover:bg-slate-200`}>
          Try again
        </button>
      </div>
    )
  }
  return (
    <div className="space-y-3 text-center">
      <p className="text-sm text-slate-300">Camera is off</p>
      <button type="button" onClick={onStart} className={`${BUTTON} bg-indigo-500 text-white hover:bg-indigo-400`}>
        Start camera
      </button>
    </div>
  )
}

export function CameraPanel({ videoRef, canvasRef, status, error, cameraOn, onToggle, onRetry }) {
  return (
    <Panel
      title="Camera"
      action={
        cameraOn && (
          <button
            type="button"
            onClick={onToggle}
            className={`${BUTTON} border border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800`}
          >
            Stop camera
          </button>
        )
      }
    >
      {/* Video and landmark canvas share size and fit, and are mirrored like a selfie view. */}
      <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-slate-950">
        <video ref={videoRef} playsInline muted className="absolute inset-0 h-full w-full -scale-x-100 object-cover" />
        <canvas
          ref={canvasRef}
          className="pointer-events-none absolute inset-0 h-full w-full -scale-x-100 object-cover"
          aria-hidden="true"
        />
        {status !== 'running' && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/80 p-6">
            <Overlay status={status} error={error} onStart={status === 'error' ? onRetry : onToggle} />
          </div>
        )}
      </div>
      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
        Video is processed locally in your browser with MediaPipe. Only the recognised gesture, intent and
        confidence are sent to the server.
      </p>
    </Panel>
  )
}
