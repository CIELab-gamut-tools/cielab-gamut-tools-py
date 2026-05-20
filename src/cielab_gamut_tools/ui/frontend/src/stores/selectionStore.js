import { defineStore } from 'pinia'

export const useSelectionStore = defineStore('selection', {
  state: () => ({
    dutId: null,
    referenceIds: [],
  }),

  actions: {
    setDut(id) {
      this.dutId = id
    },

    addReference(id) {
      if (!this.referenceIds.includes(id)) {
        this.referenceIds.push(id)
      }
    },

    removeReference(id) {
      this.referenceIds = this.referenceIds.filter((r) => r !== id)
    },

    toggleReference(id) {
      if (this.referenceIds.includes(id)) {
        this.removeReference(id)
      } else {
        this.addReference(id)
      }
    },

    clear() {
      this.dutId = null
      this.referenceIds = []
    },

    removeGamut(id) {
      if (this.dutId === id) this.dutId = null
      this.removeReference(id)
    },
  },
})
