import { defineStore } from 'pinia'

// Default per-gamut surface options — used when a gamut has no stored state.
function pgDefaults() {
  return {
    visible:    true,
    alpha:      0.75,
    wireframe:  false,
    chroma:     1.0,   // a*/b* scale before Lab→RGB (0=grey, 1=natural, >1=saturated)
    lightness:  null,  // L* override before Lab→RGB; null = use actual per-vertex L*
    edgeColour: null,  // fixed wireframe edge colour (#rrggbb); null = Lab-derived
  }
}

// Merge a partial patch onto stored (or default) per-gamut state.
function patchPg(state, id, patch) {
  state.surfaceOptions.perGamut[id] = { ...pgDefaults(), ...state.surfaceOptions.perGamut[id], ...patch }
}

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
    analysisOptions: {
      dutIds: [],
      refIds: [],
    },
    surfaceOptions: {
      perGamut: {},            // id → { visible, alpha, wireframe, chroma, lightness, edgeColour }
      perspectiveBlend: 1,     // 0 = isometric, 1 = perspective
      cameraElev: 12,          // degrees above horizontal plane (−90…90)
      cameraAzim: 9,           // degrees around L* axis, from +a* (−180…180)
      colourSpace: 'srgb',     // 'srgb' | 'display-p3' — hook for wide-gamut rendering
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

    setSurfaceVisible(id, visible)       { patchPg(this, id, { visible }) },
    setSurfaceAlpha(id, alpha)           { patchPg(this, id, { alpha }) },
    setSurfaceWireframe(id, wireframe)   { patchPg(this, id, { wireframe }) },
    setSurfaceChroma(id, chroma)         { patchPg(this, id, { chroma }) },
    setSurfaceLightness(id, lightness)   { patchPg(this, id, { lightness }) },
    setSurfaceEdgeColour(id, edgeColour) { patchPg(this, id, { edgeColour }) },

    setSurfacePerspective(blend) {
      this.surfaceOptions.perspectiveBlend = Math.max(0, Math.min(1, blend))
    },
    setCameraAngle(elev, azim) {
      this.surfaceOptions.cameraElev = Math.round(Math.max(-90, Math.min(90, elev)))
      this.surfaceOptions.cameraAzim = Math.round(azim)
    },

    // Analysis selection — independent of render selection
    setAnalysisDut(id, val) {
      if (val && !this.analysisOptions.dutIds.includes(id)) {
        this.analysisOptions.dutIds.push(id)
      } else if (!val) {
        this.analysisOptions.dutIds = this.analysisOptions.dutIds.filter(x => x !== id)
      }
    },
    setAnalysisRef(id, val) {
      if (val && !this.analysisOptions.refIds.includes(id)) {
        this.analysisOptions.refIds.push(id)
      } else if (!val) {
        this.analysisOptions.refIds = this.analysisOptions.refIds.filter(x => x !== id)
      }
    },
    initAnalysisGamut(id) {
      this.setAnalysisDut(id, true)
      this.setAnalysisRef(id, true)
    },
    removeAnalysisGamut(id) {
      this.analysisOptions.dutIds = this.analysisOptions.dutIds.filter(x => x !== id)
      this.analysisOptions.refIds = this.analysisOptions.refIds.filter(x => x !== id)
    },
  },

  // analysisOptions is intentionally excluded — gamut IDs change on every server
  // restart so persisting them is meaningless; fresh state is always correct.
  persist: {
    pick: ['activeView', 'exportOptions', 'ringsOptions', 'ringsRenderCounter', 'surfaceOptions'],
  },
})
