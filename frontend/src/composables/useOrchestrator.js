/**
 * Orchestrator-specific API calls and reactive state.
 */
import { reactive } from 'vue'
import { apiCall } from './useApi'

// --- API ---

export const orchApi = {
  getTools: () => apiCall('orch_get_tools'),
  saveTool: (tool) => apiCall('orch_save_tool', tool),
  removeTool: (toolId) => apiCall('orch_remove_tool', toolId),
  scanTools: () => apiCall('orch_scan_tools'),

  getSchedules: () => apiCall('orch_get_schedules'),
  saveSchedule: (schedule) => apiCall('orch_save_schedule', schedule),
  removeSchedule: (scheduleId) => apiCall('orch_remove_schedule', scheduleId),

  runNow: (scheduleId) => apiCall('orch_run_now', scheduleId),
  runPlan: (plan) => apiCall('orch_run_plan', plan),
  stop: () => apiCall('orch_stop'),
  getRunStatus: () => apiCall('orch_get_run_status'),
  getRecentLogs: (count) => apiCall('get_recent_logs', count),
}

// --- State ---

export const orchState = reactive({
  tools: [],
  schedules: [],
  runStatus: null,
  editing: null,
})

// --- Tool metadata ---

export const TOOL_META = {
  maa:      { emoji: '🎯', game: '明日方舟', color: '#4fc3f7' },
  m9a:      { emoji: '🕐', game: '重返未来1999', color: '#ce93d8' },
  okww:     { emoji: '🌊', game: '鸣潮', color: '#81d4fa' },
  bettergi: { emoji: '🎮', game: '原神', color: '#a5d6a7' },
  zzz:      { emoji: '⚡', game: '绝区零', color: '#fff176' },
  aether:   { emoji: '👁', game: '深空之眼', color: '#b39ddb' },
}

export function getToolMeta(toolId) {
  return TOOL_META[toolId] || { emoji: '🔧', game: toolId, color: '#90a4ae' }
}

// --- Actions ---

export async function loadTools() {
  const data = await orchApi.getTools()
  if (data && Array.isArray(data)) {
    orchState.tools = data
  }
}

export async function loadSchedules() {
  const data = await orchApi.getSchedules()
  if (data && Array.isArray(data)) {
    orchState.schedules = data
  }
}

export async function saveSchedule(schedule) {
  const result = await orchApi.saveSchedule(schedule)
  if (result && result.ok) {
    await loadSchedules()
  }
  return result
}

export async function removeSchedule(scheduleId) {
  const result = await orchApi.removeSchedule(scheduleId)
  if (result && result.ok) {
    await loadSchedules()
  }
  return result
}

export async function pollRunStatus() {
  const status = await orchApi.getRunStatus()
  if (status) {
    orchState.runStatus = status
  }
}
