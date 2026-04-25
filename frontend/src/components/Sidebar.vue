<template>
  <nav class="sidebar">
    <div class="sidebar-brand">
      <span class="brand-icon">🎮</span>
      <span class="brand-text">调度器</span>
    </div>
    <div class="sidebar-nav">
      <button
        v-for="item in navItems"
        :key="item.id"
        class="nav-item"
        :class="{ active: active === item.id }"
        @click="$emit('navigate', item.id)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>

<script setup>
defineProps({
  active: { type: String, default: 'scheduler' },
})

defineEmits(['navigate'])

const navItems = [
  { id: 'scheduler', icon: '📅', label: '调度' },
  { id: 'logs', icon: '📋', label: '日志' },
  { id: 'settings', icon: '⚙️', label: '设置' },
]
</script>

<style scoped>
.sidebar {
  width: 64px;
  background: linear-gradient(180deg, #0e0b28 0%, #12102a 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  width: 100%;
}

.brand-icon {
  font-size: 22px;
}

.brand-text {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.3);
  letter-spacing: 1px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  padding: 0 8px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 4px;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
  color: rgba(255, 255, 255, 0.35);
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.6);
}

.nav-item.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
  color: #b8c4ff;
}

.nav-icon {
  font-size: 18px;
}

.nav-label {
  font-size: 10px;
  font-weight: 500;
}
</style>
