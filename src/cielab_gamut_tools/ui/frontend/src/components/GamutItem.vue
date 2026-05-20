<template>
  <div class="gi" :class="{ 'gi--dut': isDut, 'gi--ref': isRef }">
    <span class="gi__swatch" :style="{ background: gamut.colour }" />

    <span v-if="!editing" class="gi__label" :title="gamut.label" @dblclick="startEdit">
      {{ gamut.label }}
    </span>
    <input v-else ref="editEl" class="gi__edit" v-model="draft"
           @blur="commit" @keydown.enter="commit" @keydown.escape.stop="cancel" />

    <span class="gi__vol">{{ volText }}</span>

    <button class="gi__btn" :class="{ 'gi__btn--on': isDut }" title="Set as DUT" @click="toggleDut">D</button>
    <button class="gi__btn" :class="{ 'gi__btn--on': isRef }" title="Toggle reference" @click="selection.toggleReference(gamut.id)">R</button>
    <button v-if="!gamut.protected" class="gi__btn gi__btn--del" title="Remove" @click="remove">
      <i class="pi pi-times" />
    </button>
    <span v-else class="gi__btn-placeholder" />
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useGamutStore } from '../stores/gamutStore.js'
import { useSelectionStore } from '../stores/selectionStore.js'

const props = defineProps({ gamut: { type: Object, required: true } })

const gamuts = useGamutStore()
const selection = useSelectionStore()

const editing = ref(false)
const draft = ref('')
const editEl = ref(null)

const isDut = computed(() => selection.dutId === props.gamut.id)
const isRef = computed(() => selection.referenceIds.includes(props.gamut.id))

const volText = computed(() => {
  if (props.gamut.volume === null) return '—'
  return Math.round(props.gamut.volume).toLocaleString()
})

function startEdit() {
  draft.value = props.gamut.label
  editing.value = true
  nextTick(() => editEl.value?.select())
}

function commit() {
  const trimmed = draft.value.trim()
  if (trimmed) gamuts.setLabel(props.gamut.id, trimmed)
  editing.value = false
}

function cancel() {
  editing.value = false
}

function toggleDut() {
  selection.setDut(isDut.value ? null : props.gamut.id)
}

async function remove() {
  selection.removeGamut(props.gamut.id)
  await gamuts.deleteEntry(props.gamut.id)
}
</script>

<style scoped>
.gi {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 8px;
  border-bottom: 1px solid var(--p-surface-100);
  min-width: 0;
}

.gi:hover {
  background: var(--p-surface-100);
}

.gi--dut {
  background: color-mix(in srgb, var(--p-primary-100) 40%, transparent);
}

.gi__swatch {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.gi__label {
  flex: 1;
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
  min-width: 0;
}

.gi__edit {
  flex: 1;
  font-size: 0.8rem;
  border: 1px solid var(--p-primary-400);
  border-radius: 3px;
  padding: 1px 4px;
  outline: none;
  min-width: 0;
}

.gi__vol {
  flex-shrink: 0;
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
  width: 44px;
  text-align: right;
}

.gi__btn {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border: 1px solid var(--p-surface-300);
  border-radius: 3px;
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: 0.65rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  line-height: 1;
}

.gi__btn:hover {
  border-color: var(--p-primary-400);
  color: var(--p-primary-500);
}

.gi__btn--on {
  background: var(--p-primary-500);
  border-color: var(--p-primary-500);
  color: #fff;
}

.gi__btn--del:hover {
  border-color: var(--p-red-400);
  color: var(--p-red-500);
}

.gi__btn-placeholder {
  flex-shrink: 0;
  width: 18px;
}
</style>
