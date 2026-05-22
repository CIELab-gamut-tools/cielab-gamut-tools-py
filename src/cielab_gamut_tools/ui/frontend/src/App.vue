<template>
  <div class="app-shell">
    <AppHeader />
    <div class="app-shell__body">
      <GamutSidebar />
      <MainPanel />
    </div>
  </div>

  <Teleport to="body">
    <div v-if="showOverlay" class="server-overlay">
      <div class="server-overlay__box">
        <i class="pi server-overlay__icon"
           :class="ui.clientClosing ? 'pi-power-off' : 'pi-exclamation-triangle'" />
        <p class="server-overlay__msg">{{ overlayMessage }}</p>
        <p class="server-overlay__hint">You can close this tab or window.</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import AppHeader from './components/AppHeader.vue'
import GamutSidebar from './components/GamutSidebar.vue'
import MainPanel from './components/MainPanel.vue'
import { useServerHealth } from './composables/useServerHealth.js'
import { useUiStore } from './stores/uiStore.js'

const ui = useUiStore()
useServerHealth()

const showOverlay = computed(() => ui.clientClosing || !ui.serverAlive)
const overlayMessage = computed(() =>
  ui.clientClosing
    ? 'Stopping the server…'
    : 'The server has stopped.'
)
</script>

<style>
*, *::before, *::after {
  box-sizing: border-box;
}

html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
}
</style>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-shell__body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.server-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.server-overlay__box {
  background: var(--p-surface-0);
  border-radius: 0.75rem;
  padding: 2.5rem 3rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  max-width: 22rem;
}

.server-overlay__icon {
  font-size: 2.5rem;
  color: var(--p-text-muted-color);
}

.server-overlay__msg {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
}

.server-overlay__hint {
  margin: 0;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}
</style>
