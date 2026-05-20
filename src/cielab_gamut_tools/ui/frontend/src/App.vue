<template>
  <div class="app-shell">
    <AppHeader />
    <div class="app-shell__body">
      <GamutSidebar />
      <MainPanel />
    </div>
  </div>
</template>

<script setup>
import AppHeader from './components/AppHeader.vue'
import GamutSidebar from './components/GamutSidebar.vue'
import MainPanel from './components/MainPanel.vue'
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
</style>
