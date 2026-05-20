import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', {
  state: () => ({
    activeView: 'rings',   // 'rings' | 'surface' | 'analysis'
    exportOptions: {
      format: 'png',
      dpi: 150,
      title: '',
      legend: true,
    },
  }),

  actions: {
    setView(view) {
      this.activeView = view
    },

    setExportOption(key, value) {
      this.exportOptions[key] = value
    },
  },

  persist: true,
})
