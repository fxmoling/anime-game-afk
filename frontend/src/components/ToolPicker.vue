<template>
  <Teleport to="body">
    <div class="picker-overlay" @click.self="$emit('close')">
      <div class="picker-modal">
        <div class="picker-header">
          <span class="picker-title">选择工具</span>
          <button class="picker-close" @click="$emit('close')">✕</button>
        </div>
        <div class="picker-grid">
          <button
            v-for="tool in availableTools"
            :key="tool.tool_id"
            class="tool-btn"
            :class="{ disabled: isExcluded(tool.tool_id) }"
            :style="{ '--tool-color': getMeta(tool.tool_id).color }"
            :disabled="isExcluded(tool.tool_id)"
            @click="onSelect(tool.tool_id)"
          >
            <span class="tool-emoji">{{ getMeta(tool.tool_id).emoji }}</span>
            <span class="tool-name">{{ tool.display_name || tool.tool_id }}</span>
            <span class="tool-game">{{ getMeta(tool.tool_id).game }}</span>
          </button>
        </div>
        <div v-if="availableTools.length === 0" class="picker-empty">
          暂无可用工具，请先在设置中配置
        </div>
        <div class="picker-footer">
          <button class="btn btn-secondary" @click="$emit('close')">取消</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { getToolMeta } from '../composables/useOrchestrator'

const props = defineProps({
  tools: { type: Array, default: () => [] },
  exclude: { type: Array, default: () => [] },
})

const emit = defineEmits(['select', 'close'])

const availableTools = computed(() => props.tools)

function getMeta(toolId) {
  return getToolMeta(toolId)
}

function isExcluded(toolId) {
  return props.exclude.includes(toolId)
}

function onSelect(toolId) {
  if (!isExcluded(toolId)) {
    emit('select', toolId)
  }
}
</script>

<style scoped>
.picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.picker-modal {
  background: linear-gradient(135deg, #12102a 0%, #1a1545 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 20px 24px;
  min-width: 340px;
  max-width: 480px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
}

.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.picker-title {
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e8;
}

.picker-close {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.3);
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.15s;
}

.picker-close:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.picker-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.tool-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
  color: #e0e0e0;
}

.tool-btn:hover:not(.disabled) {
  background: rgba(255, 255, 255, 0.07);
  border-color: var(--tool-color, rgba(255, 255, 255, 0.15));
  box-shadow: 0 0 12px color-mix(in srgb, var(--tool-color, #667eea) 20%, transparent);
  transform: translateY(-1px);
}

.tool-btn.disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.tool-emoji {
  font-size: 24px;
}

.tool-name {
  font-size: 12px;
  font-weight: 600;
  color: #d0d0d8;
}

.tool-game {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
}

.picker-empty {
  text-align: center;
  padding: 24px 0;
  color: rgba(255, 255, 255, 0.3);
  font-size: 13px;
}

.picker-footer {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>
