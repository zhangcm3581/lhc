<script setup>
import { computed } from 'vue'
import { colorOf, pad } from '../lib/zodiac.js'

const props = defineProps({ n: Number, size: { type: String, default: 'md' } })
const color = computed(() => colorOf(props.n))
</script>

<template>
  <span class="ball" :class="[color, size]">{{ pad(n) }}</span>
</template>

<style scoped>
.ball {
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%; color: #fff; font-weight: 700; font-family: var(--font-digits); font-variant-numeric: tabular-nums;
  box-shadow: inset 0 -2px 0 rgba(0, 0, 0, 0.12);
  width: 34px; height: 34px; font-size: 15px; flex: none;
}
.ball.sm { width: 26px; height: 26px; font-size: 12px; }
.ball.lg { width: 40px; height: 40px; font-size: 17px; }
.red { background: var(--ball-red); }
.blue { background: var(--ball-blue); }
.green { background: var(--ball-green); }
</style>
