<template>
  <Dialog v-model:visible="visible" header="About" modal :style="{ width: '38rem' }"
          :breakpoints="{ '600px': '95vw' }">
    <div v-if="info" class="about">
      <p class="about__lead">
        <strong>cielab-gamut-tools {{ info.version }}</strong><br>
        {{ info.description }}
      </p>

      <section>
        <h4>Standards Compliance</h4>
        <ul>
          <li v-for="s in info.standards" :key="s.title">
            {{ s.title }}<br>
            <span class="about__sub">{{ s.subtitle }}</span>
          </li>
        </ul>
      </section>

      <section>
        <h4>Citations</h4>
        <div v-for="c in info.citations" :key="c.doi" class="about__citation">
          <span class="about__topic">{{ c.topic }}</span><br>
          {{ c.authors }} ({{ c.year }}). "{{ c.title }}"
          <em>{{ c.journal }}</em>, {{ c.ref }}.
          <a :href="c.doi" target="_blank" rel="noopener">{{ c.doi }}</a>
        </div>
      </section>

      <section>
        <h4>Algorithm</h4>
        <p>{{ info.algorithm }}</p>
      </section>

      <section class="about__links">
        <a :href="info.repository" target="_blank" rel="noopener">Repository</a>
        &nbsp;·&nbsp;
        <a :href="info.documentation" target="_blank" rel="noopener">Documentation</a>
        &nbsp;·&nbsp;
        Licence: {{ info.licence }}
      </section>

      <section class="about__local">
        This is a locally-served web application running on your machine. All
        computation is performed by the Python server you started with
        <code>cgt ui</code>. Data never leaves your device.
      </section>
    </div>
    <div v-else class="about__loading">
      <ProgressSpinner style="width:2rem;height:2rem" />
    </div>
  </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import { getAbout } from '../api.js'

const visible = defineModel({ default: false })

const info = ref(null)

watch(visible, async (v) => {
  if (v && !info.value) {
    info.value = await getAbout().catch(() => null)
  }
})
</script>

<style scoped>
.about { display: flex; flex-direction: column; gap: 0.75rem; font-size: 0.875rem; }
.about__lead { margin: 0; line-height: 1.5; }
section { display: flex; flex-direction: column; gap: 0.25rem; }
h4 { margin: 0; font-size: 0.8125rem; text-transform: uppercase;
     letter-spacing: 0.04em; color: var(--p-text-muted-color); }
ul { margin: 0; padding-left: 1.2rem; display: flex; flex-direction: column; gap: 0.2rem; }
li { line-height: 1.4; }
.about__sub { color: var(--p-text-muted-color); }
.about__citation { line-height: 1.5; margin-bottom: 0.4rem; }
.about__topic { font-weight: 600; }
.about__links { flex-direction: row; gap: 0; }
.about__local {
  background: var(--p-surface-100);
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  color: var(--p-text-muted-color);
  font-size: 0.8125rem;
  line-height: 1.5;
}
a { color: var(--p-primary-color); }
code { font-size: 0.875em; background: var(--p-surface-200);
       padding: 0.1em 0.3em; border-radius: 0.25rem; }
.about__loading { display: flex; justify-content: center; padding: 2rem; }
</style>
