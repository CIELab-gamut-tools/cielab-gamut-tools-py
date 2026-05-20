import { defineStore } from 'pinia'
import { listGamuts, getCylmap, getSurface, getVolume, deleteGamut } from '../api.js'

export const useGamutStore = defineStore('gamuts', {
  state: () => ({
    // Map from id → gamut entry
    gamuts: {},
  }),

  getters: {
    list: (state) => Object.values(state.gamuts),
  },

  actions: {
    async fetchList() {
      const items = await listGamuts()
      for (const item of items) {
        if (!this.gamuts[item.id]) {
          this.gamuts[item.id] = {
            id: item.id,
            name: item.name,
            label: item.name,
            source: item.source,
            volume: item.volume ?? null,
            colour: item.colour,
            protected: item.protected,
            // Lazy-loaded on demand:
            cylmap: null,   // { lSteps, hSteps, counts, chroma, offsets }
            surface: null,  // { vertices, faces }
          }
        } else {
          // Refresh volume if it has been computed server-side since last fetch
          if (item.volume !== null) {
            this.gamuts[item.id].volume = item.volume
          }
        }
      }
    },

    add(item) {
      this.gamuts[item.id] = {
        id: item.id,
        name: item.name,
        label: item.name,
        source: item.source,
        volume: item.volume ?? null,
        colour: item.colour,
        protected: item.protected ?? false,
        cylmap: null,
        surface: null,
      }
    },

    remove(id) {
      delete this.gamuts[id]
    },

    setLabel(id, label) {
      if (this.gamuts[id]) this.gamuts[id].label = label
    },

    async ensureCylmap(id) {
      if (!this.gamuts[id]) return null
      if (!this.gamuts[id].cylmap) {
        this.gamuts[id].cylmap = await getCylmap(id)
      }
      return this.gamuts[id].cylmap
    },

    async ensureSurface(id) {
      if (!this.gamuts[id]) return null
      if (!this.gamuts[id].surface) {
        this.gamuts[id].surface = await getSurface(id)
      }
      return this.gamuts[id].surface
    },

    async deleteEntry(id) {
      await deleteGamut(id)
      delete this.gamuts[id]
    },

    async ensureVolume(id) {
      if (!this.gamuts[id]) return null
      if (this.gamuts[id].volume === null) {
        const { volume } = await getVolume(id)
        this.gamuts[id].volume = volume
      }
      return this.gamuts[id].volume
    },
  },
})
