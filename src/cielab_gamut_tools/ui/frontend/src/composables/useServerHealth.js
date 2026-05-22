import { onMounted, onUnmounted, watch } from 'vue'
import { keepalive } from '../api.js'
import { useUiStore } from '../stores/uiStore.js'

const POLL_MS = 2000

export function useServerHealth() {
  const ui = useUiStore()
  let timer = null

  async function poll() {
    if (ui.clientClosing) return
    try {
      await keepalive()
      ui.serverAlive = true
    } catch {
      ui.serverAlive = false
    }
  }

  function start() {
    timer = setInterval(poll, POLL_MS)
    poll()  // immediate first check
  }

  function stop() {
    clearInterval(timer)
    timer = null
  }

  // Stop polling as soon as the client initiates close.
  watch(() => ui.clientClosing, (closing) => { if (closing) stop() })

  onMounted(start)
  onUnmounted(stop)
}
