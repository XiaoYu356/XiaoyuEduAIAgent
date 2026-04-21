<template>
  <router-view />
</template>

<script setup>
</script>

<style>
:root {
  --color-primary: #4f6ef7;
  --color-primary-light: #7b93fa;
  --color-primary-dark: #3a54d4;
  --color-primary-bg: rgba(79, 110, 247, 0.06);
  --color-success: #34d399;
  --color-warning: #fbbf24;
  --color-danger: #f87171;
  --color-info: #94a3b8;

  --color-bg-page: #f0f2f5;
  --color-bg-card: #ffffff;
  --color-bg-sidebar: #1a1c2e;
  --color-bg-hover: rgba(79, 110, 247, 0.08);

  --color-text-primary: #1e293b;
  --color-text-regular: #475569;
  --color-text-secondary: #94a3b8;
  --color-text-placeholder: #cbd5e1;

  --color-border: #e2e8f0;
  --color-border-light: #f1f5f9;

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.08);
  --shadow-xl: 0 16px 48px rgba(0, 0, 0, 0.12);

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;

  --font-sans: 'Inter', 'PingFang SC', 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  --transition-fast: 0.15s ease;
  --transition-normal: 0.25s ease;
  --transition-slow: 0.4s ease;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--color-text-primary);
  background: var(--color-bg-page);
}

::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #c8cdd4;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #a0a8b4;
}

.el-card {
  border: none !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-sm) !important;
  transition: box-shadow var(--transition-normal) !important;
}
.el-card:hover {
  box-shadow: var(--shadow-md) !important;
}
.el-card__header {
  border-bottom: 1px solid var(--color-border-light) !important;
  padding: 16px 20px !important;
}

.el-button--primary {
  background: var(--color-primary) !important;
  border-color: var(--color-primary) !important;
}
.el-button--primary:hover {
  background: var(--color-primary-light) !important;
  border-color: var(--color-primary-light) !important;
}

.el-input__wrapper {
  border-radius: var(--radius-sm) !important;
}

.el-tag {
  border-radius: 6px !important;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-fast);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active {
  transition: all var(--transition-normal);
}
.slide-up-leave-active {
  transition: all var(--transition-fast);
}
.slide-up-enter-from {
  transform: translateY(12px);
  opacity: 0;
}
.slide-up-leave-to {
  transform: translateY(-8px);
  opacity: 0;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@keyframes shimmer {
  0% { background-position: -200px 0; }
  100% { background-position: calc(200px + 100%) 0; }
}

@media (max-width: 768px) {
  html { font-size: 14px; }
}
</style>
