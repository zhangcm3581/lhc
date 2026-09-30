<script setup>
// 一期开奖：6 个平码 + 特码，号码下面标生肖
import Ball from './Ball.vue'

defineProps({ draw: Object, size: { type: String, default: 'md' }, highlight: String, spread: Boolean })
</script>

<template>
  <div class="draw" :class="[size, { spread }]">
    <template v-for="(n, i) in draw.nums" :key="i">
      <span v-if="i === 6" class="plus">+</span>
      <span class="cell">
        <Ball :n="n" :size="size" />
        <span class="z" :class="{ hl: draw.zodiacs[i] === highlight }">{{ draw.zodiacs[i] }}</span>
      </span>
    </template>
  </div>
</template>

<style scoped>
.draw { display: flex; align-items: flex-start; gap: 6px; }
.draw.spread { justify-content: space-between; gap: 0; max-width: 440px; }
.cell { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.z { font-size: 14px; color: var(--ink-2); }
.sm .z { font-size: 12px; }
.lg .z { font-size: 15px; }
.z.hl { color: var(--accent); font-weight: 600; }
.plus { color: var(--muted); font-size: 18px; line-height: 34px; padding: 0 2px; }
.sm .plus { line-height: 26px; font-size: 14px; }
.lg .plus { line-height: 40px; }
</style>
