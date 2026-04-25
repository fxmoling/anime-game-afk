<template>
  <div class="logs-view">
    <div class="logs-header">
      <span class="logs-icon">📋</span>
      <h2>运行日志</h2>
      <div class="logs-actions">
        <button class="btn btn-secondary btn-sm" @click="refresh">🔄 刷新</button>
        <button class="btn btn-secondary btn-sm" @click="clear">🗑 清空</button>
      </div>
    </div>
    <div class="logs-container" ref="logsContainer">
      <div v-if="logs.length === 0" class="logs-empty">
        暂无日志
      </div>
      <div v-else class="logs-content">
        <div
          v-for="(line, idx) in logs"
          :key="idx"
          class="log-line"
          :class="getLogLevel(line)"
        >{{ line }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { orchApi } from '../composables/useOrchestrator'

const logs = ref([])
const logsContainer = ref(null)
let interval = null

async function refresh() {
  const data = await orchApi.getRecentLogs(500)
  if (data && Array.isArray(data)) {
    logs.value = data
    await nextTick()
    scrollToBottom()
  }
}

function clear() {
  logs.value = []
}

function scrollToBottom() {
  if (logsContainer.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
  }
}

function getLogLevel(line) {
  if (line.includes('ERROR') || line.includes('CRITICAL')) return 'log-error'
  if (line.includes('WARNING')) return 'log-warn'
  if (line.includes('SUCCESS')) return 'log-success'
  if (line.includes('DEBUG')) return 'log-debug'
  return ''
}

onMounted(() => {
  refresh()
  interval = setInterval(refresh, 3000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<style scoped>
.logs-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.logs-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.logs-icon {
  font-size: 18px;
}

.logs-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: #e0e0e8;
  flex: 1;
}

.logs-actions {
  display: flex;
  gap: 6px;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

.logs-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.logs-empty {
  text-align: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.2);
  font-size: 14px;
}

.log-line {
  color: rgba(255, 255, 255, 0.55);
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line.log-error {
  color: #ef5350;
}

.log-line.log-warn {
  color: #ffa726;
}

.log-line.log-success {
  color: #66bb6a;
}

.log-line.log-debug {
  color: rgba(255, 255, 255, 0.25);
}
</style>
