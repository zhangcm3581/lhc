<script setup>
// 分段选择器
defineProps({ options: Array, block: Boolean })
const model = defineModel()
</script>

<template>
  <div class="seg" :class="{ block }" role="radiogroup">
    <button
      v-for="o in options"
      :key="o.value"
      role="radio"
      :aria-checked="model === o.value"
      :class="{ on: model === o.value }"
      @click="model = o.value"
    >
      {{ o.label }}<span v-if="o.sub" class="sub">{{ o.sub }}</span>
    </button>
  </div>
</template>

<style scoped>
.seg { display: inline-flex; background: var(--line); border-radius: 9px; padding: 3px; gap: 2px; }
button {
  border: 0; background: none; padding: 5px 14px; border-radius: 7px; cursor: pointer;
  font-size: 14px; line-height: 20px; color: var(--ink-2); white-space: nowrap;
}
button.on { background: var(--surface); color: var(--accent); font-weight: 600; box-shadow: 0 1px 3px rgba(29, 33, 41, 0.12); }
.sub { font-weight: 400; font-size: 12px; margin-left: 5px; opacity: 0.7; }
.seg.block { display: flex; width: 100%; }
.seg.block button { flex: 1; padding-left: 4px; padding-right: 4px; }
.seg.block button { padding-top: 7px; padding-bottom: 7px; }
@media (max-width: 480px) {
  .seg:not(.block) .sub { display: none; }
  .seg:not(.block) button { padding: 5px 12px; }
}
</style>
