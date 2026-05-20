import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', {
  state: () => ({
    activeView: 'rings',
    exportOptions: {
      format: 'png',
      dpi: 150,
    },
    ringsOptions: {
      // Axis
      scale: '',              // '' | 'emissive' | '150' | '300' | '600'
      // Reference
      intersection: false,
      // Ring levels
      lRings: '',             // '' = default; '20,40,60,80' = custom
      // Colour bands
      showBands: true,
      bandChroma: 50,
      bandLs: '20,90',
      // Primary indicators
      primaries: 'rgb',       // 'none' | 'rgb' | 'all'
      refPrimaries: 'none',
      primaryColor: 'output', // 'input' | 'output'
      primaryOrigin: 'centre',// 'centre' | 'ring'
      primaryChroma: 'auto',  // 'auto' | numeric string
      showCentMark: true,
      // Ring labels
      lLabels: '10,50',       // 'none' | comma-separated L* values
      lLabelColor: '',        // '' = default
      // Chroma reference circles
      chromaRings: '',        // '' | '50,100,150'
      // Title & labels
      autoTitle: true,
      customTitle: '',
      dutLabel: '',           // '' = auto
      refLabel: '',           // '' = auto
      // Figure
      dpi: 150,
    },
    ringsRenderCounter: 0,
    surfaceOptions: {
      perGamut: {},  // id → { visible: bool, alpha: number }
    },
  }),

  actions: {
    setView(view) {
      this.activeView = view
    },
    setExportOption(key, value) {
      this.exportOptions[key] = value
    },
    setRingsOption(key, value) {
      this.ringsOptions[key] = value
    },
    forceRender() {
      this.ringsRenderCounter++
    },
    setSurfaceVisible(id, visible) {
      const cur = this.surfaceOptions.perGamut[id]
      this.surfaceOptions.perGamut[id] = { visible, alpha: cur?.alpha ?? 0.75 }
    },
    setSurfaceAlpha(id, alpha) {
      const cur = this.surfaceOptions.perGamut[id]
      this.surfaceOptions.perGamut[id] = { visible: cur?.visible ?? true, alpha }
    },
  },

  persist: true,
})
