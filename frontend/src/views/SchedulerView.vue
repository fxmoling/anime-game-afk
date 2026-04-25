<template>
  <div class="scheduler-view">
    <!-- Header -->
    <div class="sched-header">
      <div class="sched-header-left">
        <span class="sched-icon">📅</span>
        <h2>调度计划</h2>
      </div>
      <div class="sched-header-right">
        <button class="btn btn-secondary btn-sm" @click="addSchedule">+ 新建</button>
      </div>
    </div>

    <!-- Schedule selector -->
    <div class="schedule-bar" v-if="orchState.schedules.length > 1">
      <label>计划</label>
      <select v-model="currentScheduleId">
        <option v-for="s in orchState.schedules" :key="s.id" :value="s.id">
          {{ s.name || '未命名计划' }}
        </option>
      </select>
      <button class="btn-icon" title="删除此计划" @click="deleteSchedule">🗑</button>
    </div>

    <!-- Schedule name -->
    <div class="schedule-name-row">
      <label>名称</label>
      <input
        type="text"
        v-model="schedule.name"
        placeholder="我的调度计划"
        class="sched-input"
        @blur="markDirty"
      >
    </div>

    <!-- Timer config -->
    <div class="timer-section">
      <div class="timer-row">
        <span class="timer-icon">⏰</span>
        <label>定时</label>
        <div class="timer-presets">
          <button
            v-for="preset in timerPresets"
            :key="preset.value"
            class="preset-btn"
            :class="{ active: timerPreset === preset.value }"
            @click="setTimerPreset(preset.value)"
          >{{ preset.label }}</button>
        </div>
      </div>

      <!-- Custom timer -->
      <div v-if="timerPreset === 'custom'" class="timer-custom">
        <div class="time-pick">
          <label>时间</label>
          <input type="time" v-model="schedule.time" class="sched-input time-input" @change="markDirty">
        </div>
        <div class="day-pick">
          <label>重复</label>
          <div class="day-checkboxes">
            <label
              v-for="day in dayOptions"
              :key="day.value"
              class="day-chip"
              :class="{ active: schedule.days.includes(day.value) }"
            >
              <input type="checkbox" :value="day.value" v-model="schedule.days" @change="markDirty">
              {{ day.label }}
            </label>
          </div>
        </div>
      </div>

      <!-- Enable toggle -->
      <div class="timer-enable">
        <label>启用调度</label>
        <label class="toggle-switch">
          <input type="checkbox" v-model="schedule.enabled" @change="markDirty">
          <span class="toggle-slider"></span>
        </label>
      </div>
    </div>

    <!-- Steps -->
    <div class="steps-section">
      <div
        v-for="(step, stepIdx) in schedule.steps"
        :key="stepIdx"
        class="step-block"
        :class="{
          'step-running': isStepRunning(stepIdx),
          'step-done': isStepDone(stepIdx),
        }"
      >
        <div class="step-header">
          <span class="step-label">步骤 {{ stepIdx + 1 }}</span>
          <span class="step-hint" v-if="step.tools.length > 1">— 同时运行</span>
          <span class="step-hint" v-else-if="step.tools.length === 1">— 单独运行</span>
          <div class="step-actions">
            <button
              v-if="schedule.steps.length > 1"
              class="btn-icon btn-icon-sm"
              title="删除步骤"
              @click="removeStep(stepIdx)"
            >✕</button>
          </div>
        </div>

        <div class="step-cards">
          <!-- Tool cards -->
          <div
            v-for="(toolRef, toolIdx) in step.tools"
            :key="toolRef.tool_id"
            class="tool-card"
            :style="{ '--card-color': getToolMeta(toolRef.tool_id).color }"
            :class="{
              expanded: expandedCard === `${stepIdx}-${toolIdx}`,
              'card-running': getToolRunState(stepIdx, toolRef.tool_id) === 'running',
              'card-done': getToolRunState(stepIdx, toolRef.tool_id) === 'done',
              'card-failed': getToolRunState(stepIdx, toolRef.tool_id) === 'failed',
              'card-waiting': getToolRunState(stepIdx, toolRef.tool_id) === 'waiting',
            }"
          >
            <div class="card-main" @click="toggleExpand(stepIdx, toolIdx)">
              <span class="card-emoji">{{ getToolMeta(toolRef.tool_id).emoji }}</span>
              <div class="card-info">
                <span class="card-name">{{ getToolDisplayName(toolRef.tool_id) }}</span>
                <span class="card-game">{{ getToolMeta(toolRef.tool_id).game }}</span>
              </div>
              <span class="card-status">{{ getStatusBadge(stepIdx, toolRef.tool_id) }}</span>
              <button
                class="card-remove"
                title="移除"
                @click.stop="removeTool(stepIdx, toolIdx)"
              >✕</button>
            </div>

            <!-- Expanded config -->
            <div v-if="expandedCard === `${stepIdx}-${toolIdx}`" class="card-config">
              <div class="config-row">
                <label>超时 (分钟)</label>
                <input
                  type="number"
                  v-model.number="toolRef.timeout_min"
                  min="1"
                  max="180"
                  class="sched-input narrow"
                  @change="markDirty"
                >
              </div>
              <div v-if="toolRef.tool_id === 'okww'" class="config-row">
                <label>任务索引</label>
                <input
                  type="number"
                  v-model.number="toolRef.task_index"
                  min="0"
                  class="sched-input narrow"
                  @change="markDirty"
                >
              </div>
              <div v-if="toolRef.tool_id === 'bettergi'" class="config-row">
                <label>配置名称</label>
                <input
                  type="text"
                  v-model="toolRef.config_name"
                  placeholder="default"
                  class="sched-input"
                  @change="markDirty"
                >
              </div>
            </div>
          </div>

          <!-- Add tool button -->
          <button class="add-tool-btn" @click="openToolPicker(stepIdx)">
            <span class="add-icon">+</span>
            <span class="add-label">添加工具</span>
          </button>
        </div>

        <!-- Arrow connector -->
        <div v-if="stepIdx < schedule.steps.length - 1" class="step-connector">
          <div class="connector-line"></div>
          <div class="connector-arrow">▼</div>
        </div>
      </div>

      <!-- Add step button -->
      <button class="add-step-btn" @click="addStep">
        <span>+ 添加步骤</span>
      </button>
    </div>

    <!-- Post-action -->
    <div class="post-section">
      <span class="post-label">完成后:</span>
      <label class="radio-opt" v-for="opt in postActions" :key="opt.value">
        <input type="radio" :value="opt.value" v-model="schedule.post_action" @change="markDirty">
        <span class="radio-dot"></span>
        <span>{{ opt.label }}</span>
      </label>
    </div>

    <!-- Action bar -->
    <div class="action-bar">
      <button
        class="btn btn-primary"
        :disabled="isRunning || schedule.steps.length === 0"
        @click="runNow"
      >
        <span v-if="!isRunning">▶ 立即运行</span>
        <span v-else>⏹ 停止</span>
      </button>
      <div class="action-spacer"></div>
      <span v-if="saveHint" class="save-hint">{{ saveHint }}</span>
      <button
        class="btn btn-secondary"
        :disabled="!isDirty"
        @click="save"
      >💾 保存</button>
    </div>

    <!-- Tool picker modal -->
    <ToolPicker
      v-if="showToolPicker"
      :tools="orchState.tools"
      :exclude="pickerExclude"
      @select="onToolSelected"
      @close="showToolPicker = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import {
  orchState,
  orchApi,
  getToolMeta,
  loadTools,
  loadSchedules,
  saveSchedule as apiSaveSchedule,
  removeSchedule as apiRemoveSchedule,
  pollRunStatus,
} from '../composables/useOrchestrator'
import ToolPicker from '../components/ToolPicker.vue'

// --- Local state ---

const currentScheduleId = ref(null)
const isDirty = ref(false)
const saveHint = ref('')
const expandedCard = ref(null)
const showToolPicker = ref(false)
const pickerStepIdx = ref(0)
let statusInterval = null

const defaultSchedule = () => ({
  id: null,
  name: '',
  enabled: false,
  time: '04:00',
  days: ['everyday'],
  steps: [{ tools: [] }],
  post_action: 'nothing',
})

const schedule = reactive(defaultSchedule())

// --- Timer presets ---

const timerPresets = [
  { value: 'daily04', label: '每天 04:00' },
  { value: 'daily06', label: '每天 06:00' },
  { value: 'every12h', label: '每 12 小时' },
  { value: 'custom', label: '自定义' },
]

const timerPreset = ref('daily04')

const dayOptions = [
  { value: 'everyday', label: '每天' },
  { value: 'weekdays', label: '工作日' },
  { value: 'weekends', label: '周末' },
  { value: 'mon', label: '一' },
  { value: 'tue', label: '二' },
  { value: 'wed', label: '三' },
  { value: 'thu', label: '四' },
  { value: 'fri', label: '五' },
  { value: 'sat', label: '六' },
  { value: 'sun', label: '日' },
]

const postActions = [
  { value: 'nothing', label: '什么都不做' },
  { value: 'close_games', label: '关闭游戏' },
  { value: 'shutdown', label: '关机' },
]

// --- Computed ---

const isRunning = computed(() => {
  return orchState.runStatus && orchState.runStatus.running
})

const pickerExclude = computed(() => {
  if (pickerStepIdx.value == null || !schedule.steps[pickerStepIdx.value]) return []
  return schedule.steps[pickerStepIdx.value].tools.map(t => t.tool_id)
})

// --- Init ---

onMounted(async () => {
  await loadTools()
  await loadSchedules()

  if (orchState.schedules.length > 0) {
    currentScheduleId.value = orchState.schedules[0].id
    loadScheduleIntoForm(orchState.schedules[0])
  }

  statusInterval = setInterval(pollRunStatus, 2000)
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})

// Watch schedule selector
watch(currentScheduleId, (newId) => {
  const found = orchState.schedules.find(s => s.id === newId)
  if (found) {
    loadScheduleIntoForm(found)
  }
})

// --- Schedule form management ---

function loadScheduleIntoForm(s) {
  schedule.id = s.id || null
  schedule.name = s.name || ''
  schedule.enabled = s.enabled || false
  schedule.time = s.time || '04:00'
  schedule.days = s.days ? [...s.days] : ['everyday']
  schedule.steps = s.steps && s.steps.length > 0
    ? s.steps.map(step => ({
        tools: step.tools ? step.tools.map(t => ({ ...t })) : [],
      }))
    : [{ tools: [] }]
  schedule.post_action = s.post_action || 'nothing'
  detectTimerPreset()
  isDirty.value = false
  expandedCard.value = null
}

function detectTimerPreset() {
  const t = schedule.time
  const d = schedule.days
  const isEveryday = d.length === 1 && d[0] === 'everyday'
  if (isEveryday && t === '04:00') timerPreset.value = 'daily04'
  else if (isEveryday && t === '06:00') timerPreset.value = 'daily06'
  else timerPreset.value = 'custom'
}

function setTimerPreset(preset) {
  timerPreset.value = preset
  if (preset === 'daily04') {
    schedule.time = '04:00'
    schedule.days = ['everyday']
  } else if (preset === 'daily06') {
    schedule.time = '06:00'
    schedule.days = ['everyday']
  } else if (preset === 'every12h') {
    schedule.time = '04:00'
    schedule.days = ['everyday']
  }
  markDirty()
}

function markDirty() {
  isDirty.value = true
}

// --- Step management ---

function addStep() {
  schedule.steps.push({ tools: [] })
  markDirty()
}

function removeStep(idx) {
  schedule.steps.splice(idx, 1)
  if (schedule.steps.length === 0) {
    schedule.steps.push({ tools: [] })
  }
  markDirty()
}

// --- Tool management ---

function openToolPicker(stepIdx) {
  pickerStepIdx.value = stepIdx
  showToolPicker.value = true
}

function onToolSelected(toolId) {
  const step = schedule.steps[pickerStepIdx.value]
  if (step) {
    step.tools.push({
      tool_id: toolId,
      timeout_min: 30,
      task_index: 0,
      config_name: '',
    })
    markDirty()
  }
  showToolPicker.value = false
}

function removeTool(stepIdx, toolIdx) {
  schedule.steps[stepIdx].tools.splice(toolIdx, 1)
  expandedCard.value = null
  markDirty()
}

function toggleExpand(stepIdx, toolIdx) {
  const key = `${stepIdx}-${toolIdx}`
  expandedCard.value = expandedCard.value === key ? null : key
}

function getToolDisplayName(toolId) {
  const tool = orchState.tools.find(t => t.tool_id === toolId)
  return tool ? (tool.display_name || toolId) : toolId
}

// --- Run status helpers ---

function getToolRunState(stepIdx, toolId) {
  if (!orchState.runStatus || !orchState.runStatus.running) return 'idle'
  const status = orchState.runStatus
  if (!status.step_statuses) return 'idle'
  const stepStatus = status.step_statuses[stepIdx]
  if (!stepStatus) return 'idle'
  const toolStatus = stepStatus[toolId]
  return toolStatus || 'idle'
}

function isStepRunning(stepIdx) {
  if (!orchState.runStatus || !orchState.runStatus.running) return false
  return orchState.runStatus.current_step === stepIdx
}

function isStepDone(stepIdx) {
  if (!orchState.runStatus || !orchState.runStatus.running) return false
  return orchState.runStatus.current_step > stepIdx
}

function getStatusBadge(stepIdx, toolId) {
  const state = getToolRunState(stepIdx, toolId)
  switch (state) {
    case 'running': return '🔄'
    case 'done': return '✅'
    case 'failed': return '❌'
    case 'waiting': return '⏳'
    default: return '✅'
  }
}

// --- Schedule CRUD ---

function addSchedule() {
  const newSched = defaultSchedule()
  newSched.name = `计划 ${orchState.schedules.length + 1}`
  Object.assign(schedule, newSched)
  currentScheduleId.value = null
  isDirty.value = true
}

async function deleteSchedule() {
  if (!currentScheduleId.value) return
  if (!confirm('确定删除此计划？')) return
  await apiRemoveSchedule(currentScheduleId.value)
  if (orchState.schedules.length > 0) {
    currentScheduleId.value = orchState.schedules[0].id
    loadScheduleIntoForm(orchState.schedules[0])
  } else {
    Object.assign(schedule, defaultSchedule())
    currentScheduleId.value = null
  }
}

async function save() {
  const data = {
    id: schedule.id,
    name: schedule.name || '未命名计划',
    enabled: schedule.enabled,
    time: schedule.time,
    days: [...schedule.days],
    steps: schedule.steps.map(step => ({
      tools: step.tools.map(t => ({
        tool_id: t.tool_id,
        timeout_min: t.timeout_min,
        task_index: t.task_index,
        config_name: t.config_name,
      })),
    })),
    post_action: schedule.post_action,
  }

  if (timerPreset.value === 'every12h') {
    data.interval_hours = 12
  }

  const result = await apiSaveSchedule(data)
  if (result && result.ok) {
    if (result.id) {
      schedule.id = result.id
      currentScheduleId.value = result.id
    }
    isDirty.value = false
    saveHint.value = '✔ 已保存'
    setTimeout(() => { saveHint.value = '' }, 2000)
  }
}

async function runNow() {
  if (isRunning.value) {
    await orchApi.stop()
    return
  }

  // Always save first to persist current UI state
  await save()

  // Now run the persisted schedule
  if (schedule.id) {
    const result = await orchApi.runNow(schedule.id)
    if (result && !result.ok) {
      console.error('Run failed:', result.error)
    }
  }
}
</script>

<style scoped>
.scheduler-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 0 0 20px;
}

/* Header */
.sched-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.sched-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sched-icon {
  font-size: 18px;
}

.sched-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: #e0e0e8;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

/* Schedule selector */
.schedule-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.schedule-bar label {
  color: rgba(255, 255, 255, 0.35);
  font-size: 12px;
  flex-shrink: 0;
}

.schedule-bar select {
  flex: 1;
  max-width: 300px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.05);
  color: #c8c8d0;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
}

.schedule-bar select:focus {
  outline: none;
  border-color: rgba(102, 126, 234, 0.5);
}

/* Schedule name */
.schedule-name-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.schedule-name-row label {
  color: rgba(255, 255, 255, 0.35);
  font-size: 12px;
  flex-shrink: 0;
  width: 40px;
}

/* Shared input */
.sched-input {
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.05);
  color: #e0e0e0;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  font-size: 13px;
  flex: 1;
  max-width: 300px;
}

.sched-input:focus {
  outline: none;
  border-color: rgba(102, 126, 234, 0.5);
}

.sched-input.narrow {
  max-width: 80px;
  flex: 0;
}

.sched-input.time-input {
  max-width: 120px;
  flex: 0;
  color-scheme: dark;
}

/* Icon button */
.btn-icon {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.25);
  font-size: 14px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: all 0.15s;
}

.btn-icon:hover {
  color: #f44336;
  background: rgba(244, 67, 54, 0.1);
}

.btn-icon-sm {
  font-size: 12px;
  padding: 2px 4px;
}

/* Timer section */
.timer-section {
  padding: 14px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.timer-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.timer-icon {
  font-size: 15px;
}

.timer-row > label {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  flex-shrink: 0;
}

.timer-presets {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.preset-btn {
  padding: 4px 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.preset-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.75);
}

.preset-btn.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
  border-color: rgba(102, 126, 234, 0.4);
  color: #b8c4ff;
}

.timer-custom {
  display: flex;
  gap: 20px;
  padding: 10px 0 4px 25px;
  flex-wrap: wrap;
}

.time-pick,
.day-pick {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-pick label,
.day-pick label:first-child {
  color: rgba(255, 255, 255, 0.35);
  font-size: 12px;
  flex-shrink: 0;
}

.day-checkboxes {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.day-chip {
  padding: 3px 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.45);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}

.day-chip input {
  display: none;
}

.day-chip.active {
  background: rgba(102, 126, 234, 0.15);
  border-color: rgba(102, 126, 234, 0.35);
  color: #b8c4ff;
}

.timer-enable {
  display: flex;
  align-items: center;
  gap: 10px;
}

.timer-enable > label:first-child {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
}

/* Toggle switch (matches SettingsView) */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px !important;
  height: 22px;
  flex-shrink: 0;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background: #333;
  border-radius: 22px;
  transition: 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background: #999;
  border-radius: 50%;
  transition: 0.2s;
}

.toggle-switch input:checked + .toggle-slider {
  background: #2196f3;
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
  background: white;
}

/* Steps section */
.steps-section {
  padding: 14px 20px;
  flex: 1;
}

.step-block {
  position: relative;
  margin-bottom: 4px;
}

.step-block.step-running {
  border-left: 2px solid #667eea;
  padding-left: 10px;
  margin-left: -12px;
}

.step-block.step-done {
  opacity: 0.6;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.step-label {
  font-size: 13px;
  font-weight: 600;
  color: #c0c0d0;
}

.step-hint {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.25);
}

.step-actions {
  margin-left: auto;
}

.step-cards {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: flex-start;
}

/* Tool card */
.tool-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  min-width: 150px;
  max-width: 220px;
  transition: all 0.2s;
  overflow: hidden;
}

.tool-card:hover {
  border-color: color-mix(in srgb, var(--card-color, #667eea) 40%, transparent);
  background: rgba(255, 255, 255, 0.05);
}

.tool-card.expanded {
  border-color: color-mix(in srgb, var(--card-color, #667eea) 50%, transparent);
}

.tool-card.card-running {
  border-color: rgba(102, 126, 234, 0.5);
  box-shadow: 0 0 16px rgba(102, 126, 234, 0.15);
  animation: pulse-glow 2s ease-in-out infinite;
}

.tool-card.card-done {
  border-color: rgba(76, 175, 80, 0.4);
}

.tool-card.card-failed {
  border-color: rgba(244, 67, 54, 0.4);
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 8px rgba(102, 126, 234, 0.1); }
  50% { box-shadow: 0 0 20px rgba(102, 126, 234, 0.25); }
}

.card-main {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  cursor: pointer;
}

.card-emoji {
  font-size: 22px;
  flex-shrink: 0;
}

.card-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.card-name {
  font-size: 13px;
  font-weight: 600;
  color: #d8d8e0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-game {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
}

.card-status {
  font-size: 14px;
  flex-shrink: 0;
}

.card-remove {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.15);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all 0.15s;
  flex-shrink: 0;
}

.card-remove:hover {
  color: #f44336;
  background: rgba(244, 67, 54, 0.1);
}

/* Card expanded config */
.card-config {
  padding: 8px 14px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-row label {
  color: rgba(255, 255, 255, 0.35);
  font-size: 11px;
  flex-shrink: 0;
  min-width: 70px;
}

/* Add tool button */
.add-tool-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 100px;
  min-height: 70px;
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  background: transparent;
  color: rgba(255, 255, 255, 0.2);
  cursor: pointer;
  transition: all 0.15s;
}

.add-tool-btn:hover {
  border-color: rgba(102, 126, 234, 0.3);
  color: rgba(255, 255, 255, 0.5);
  background: rgba(102, 126, 234, 0.05);
}

.add-icon {
  font-size: 20px;
  font-weight: 300;
}

.add-label {
  font-size: 10px;
}

/* Step connector */
.step-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 0;
  margin-left: 30px;
}

.connector-line {
  width: 1px;
  height: 12px;
  background: rgba(255, 255, 255, 0.1);
}

.connector-arrow {
  color: rgba(255, 255, 255, 0.15);
  font-size: 10px;
  line-height: 1;
}

/* Add step button */
.add-step-btn {
  display: block;
  width: 100%;
  padding: 10px;
  margin-top: 8px;
  border: 1px dashed rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: transparent;
  color: rgba(255, 255, 255, 0.25);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  text-align: center;
}

.add-step-btn:hover {
  border-color: rgba(102, 126, 234, 0.3);
  color: rgba(255, 255, 255, 0.5);
  background: rgba(102, 126, 234, 0.05);
}

/* Post-action */
.post-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  flex-wrap: wrap;
}

.post-label {
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
  flex-shrink: 0;
}

.radio-opt {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  user-select: none;
}

.radio-opt input {
  display: none;
}

.radio-dot {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  position: relative;
  flex-shrink: 0;
  transition: all 0.15s;
}

.radio-opt input:checked ~ .radio-dot {
  border-color: #667eea;
}

.radio-opt input:checked ~ .radio-dot::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 6px;
  height: 6px;
  background: #667eea;
  border-radius: 50%;
}

.radio-opt input:checked ~ span:last-child {
  color: #c0c8f0;
}

/* Action bar */
.action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(8, 6, 26, 0.5);
  backdrop-filter: blur(8px);
  position: sticky;
  bottom: 0;
}

.action-spacer {
  flex: 1;
}

.save-hint {
  color: #4caf50;
  font-size: 13px;
  animation: fadeHint 2s forwards;
}

@keyframes fadeHint {
  0%, 70% { opacity: 1; }
  100% { opacity: 0; }
}
</style>
