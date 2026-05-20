<template>
  <header class="app-header">
    <span class="app-header__title">CIELab Gamut Tools</span>
    <Button label="Export" icon="pi pi-download" size="small" outlined disabled />
  </header>
</template>

<script setup>
import Button from 'primevue/button'
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  height: 3rem;
  border-bottom: 1px solid var(--p-surface-200);
  background: var(--p-surface-0);
  flex-shrink: 0;
}

.app-header__title {
  font-weight: 600;
  font-size: 1rem;
}
</style>
