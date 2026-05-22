import { ref } from 'vue'

// Module-level singleton — safe because the surface canvas is a singleton in the app.
const _fn = ref(null)  // fn() => Promise<Blob> | null when canvas is not mounted

export function useCanvasCapture() {
  return {
    captureCanvas: _fn,
    register(fn)  { _fn.value = fn },
    unregister()  { _fn.value = null },
  }
}
