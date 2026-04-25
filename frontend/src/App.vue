<template>
  <div class="app-shell">
    <Sidebar :active="activePage" @navigate="activePage = $event" />
    <main class="main-content">
      <SchedulerView v-if="activePage === 'scheduler'" />
      <LogsView v-else-if="activePage === 'logs'" />
      <SettingsView v-else-if="activePage === 'settings'" />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import SchedulerView from './views/SchedulerView.vue'
import LogsView from './views/LogsView.vue'
import SettingsView from './views/SettingsView.vue'

const activePage = ref('scheduler')
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0a0820;
  color: #d0d0d8;
  overflow: hidden;
}

.app-shell {
  display: flex;
  height: 100%;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Shared button styles */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.06);
  color: #b0b0c0;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: #d0d0e0;
}

.btn-secondary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}
</style>
