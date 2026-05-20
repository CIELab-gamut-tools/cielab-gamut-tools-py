import { ref } from 'vue'
import { uploadGamut } from '../api.js'

/**
 * Shared file-drop logic. Handles enter-counter (avoids child-element flicker),
 * upload, and error display. Caller supplies onUploaded(entry) to handle the result.
 */
export function useFileDrop(onUploaded) {
  const isDragging = ref(false)
  const isUploading = ref(false)
  const error = ref(null)
  let depth = 0
  let errorTimer = null

  function hasFiles(e) {
    return [...(e.dataTransfer?.items ?? [])].some(i => i.kind === 'file')
  }

  function onDragenter(e) {
    if (!hasFiles(e)) return
    e.preventDefault()
    if (depth === 0) isDragging.value = true
    depth++
  }

  function onDragover(e) {
    if (depth > 0) e.preventDefault()
  }

  function onDragleave() {
    if (depth <= 0) return
    depth--
    if (depth === 0) isDragging.value = false
  }

  async function onDrop(e) {
    e.preventDefault()
    depth = 0
    isDragging.value = false
    const file = e.dataTransfer?.files[0]
    if (!file) return
    isUploading.value = true
    error.value = null
    try {
      const entry = await uploadGamut(file)
      onUploaded(entry)
    } catch (err) {
      error.value = err.message
      if (errorTimer) clearTimeout(errorTimer)
      errorTimer = setTimeout(() => { error.value = null }, 4000)
    } finally {
      isUploading.value = false
    }
  }

  return {
    isDragging,
    isUploading,
    error,
    dropHandlers: { onDragenter, onDragover, onDragleave, onDrop },
  }
}
