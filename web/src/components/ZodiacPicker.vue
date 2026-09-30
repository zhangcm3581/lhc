<script setup>
import { ZODIACS } from '../lib/zodiac.js'

defineProps({ benming: String })
const model = defineModel()
</script>

<template>
  <div class="picker">
    <button v-for="z in ZODIACS" :key="z" class="chip" :class="{ on: model === z, bm: z === benming }" @click="model = z">
      {{ z }}
    </button>
  </div>
</template>

<style scoped>
.picker { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; }
.chip { position: relative; padding: 7px 0; text-align: center; font-size: 15px; }
/* 本命：右上角橙色小点 */
.chip.bm::after {
  content: ''; position: absolute; top: 5px; right: 6px; width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
}
</style>
