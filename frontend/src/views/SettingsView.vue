<template>
  <div class="settings-view">
    <div class="settings-header">
      <span class="settings-icon">⚙️</span>
      <h2>工具设置</h2>
      <button class="btn btn-secondary btn-sm" @click="scanTools">🔍 自动扫描</button>
    </div>

    <div class="tools-list">
      <div
        v-for="tool in tools"
        :key="tool.tool_id"
        class="tool-item"
        :style="{ '--tool-color': getMeta(tool.tool_id).color }"
      >
        <div class="tool-header">
          <span class="tool-emoji">{{ getMeta(tool.tool_id).emoji }}</span>
          <div class="tool-info">
            <span class="tool-name">{{ tool.display_name }}</span>
            <span class="tool-game">{{ getMeta(tool.tool_id).game }}</span>
          </div>
          <span
            class="tool-status"
            :class="{ configured: tool.exe_path }"
          >{{ tool.exe_path ? '✅' : '⚠️' }}</span>
        </div>
        <div class="tool-path-row">
          <label>路径</label>
          <input
            type="text"
            :value="tool.exe_path"
            @change="updatePath(tool.tool_id, $event.target.value)"
            placeholder="选择可执行文件路径..."
            class="path-input"
          >
        </div>
      </div>
    </div>

    <div v-if="scanResult" class="scan-result">
      <p>找到 {{ scanResult.length }} 个工具</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { orchApi, orchState, getToolMeta, loadTools } from '../composables/useOrchestrator'

const tools = ref([])
const scanResult = ref(null)

function getMeta(toolId) {
  return getToolMeta(toolId)
}

async function loadAllTools() {
  await loadTools()
  tools.value = [...orchState.tools]
}

async function updatePath(toolId, newPath) {
  const tool = tools.value.find(t => t.tool_id === toolId)
  if (tool) {
    tool.exe_path = newPath
    await orchApi.saveTool(tool)
  }
}

async function scanTools() {
  const found = await orchApi.scanTools()
  if (found && Array.isArray(found)) {
    scanResult.value = found
    for (const scanned of found) {
      await orchApi.saveTool(scanned)
    }
    await loadAllTools()
  }
}

onMounted(loadAllTools)
</script>

<style scoped>
.settings-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.settings-icon {
  font-size: 18px;
}

.settings-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: #e0e0e8;
  flex: 1;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

.tools-list {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 14px 16px;
  transition: all 0.15s;
}

.tool-item:hover {
  border-color: color-mix(in srgb, var(--tool-color, #667eea) 30%, transparent);
  background: rgba(255, 255, 255, 0.04);
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.tool-emoji {
  font-size: 22px;
  flex-shrink: 0;
}

.tool-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.tool-name {
  font-size: 13px;
  font-weight: 600;
  color: #d8d8e0;
}

.tool-game {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
}

.tool-status {
  font-size: 14px;
  flex-shrink: 0;
}

.tool-path-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-path-row label {
  color: rgba(255, 255, 255, 0.35);
  font-size: 12px;
  flex-shrink: 0;
}

.path-input {
  flex: 1;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.05);
  color: #e0e0e0;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  font-size: 12px;
  font-family: 'Cascadia Code', 'Consolas', monospace;
}

.path-input:focus {
  outline: none;
  border-color: rgba(102, 126, 234, 0.5);
}

.path-input::placeholder {
  color: rgba(255, 255, 255, 0.2);
}

.scan-result {
  padding: 12px 20px;
  color: #66bb6a;
  font-size: 13px;
}
</style>
