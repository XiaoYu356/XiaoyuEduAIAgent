<template>
  <el-container class="layout-container">
    <div class="mobile-header" v-if="isMobile">
      <el-button text @click="drawerVisible = true" class="mobile-menu-btn">
        <el-icon :size="22"><Menu /></el-icon>
      </el-button>
      <div class="mobile-logo">
        <span class="logo-icon">🐟</span>
        <span class="logo-text">小鱼教育AI</span>
      </div>
      <el-dropdown trigger="click">
        <el-button text>
          <el-icon :size="20"><UserFilled /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>{{ userStore.userInfo?.username }}</el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">
              <el-icon><SwitchButton /></el-icon> 退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <el-drawer v-model="drawerVisible" direction="ltr" :size="240" :show-close="false" v-if="isMobile">
      <template #header>
        <div class="sidebar-logo">
          <span class="logo-icon">🐟</span>
          <span class="logo-text">小鱼教育AI</span>
        </div>
      </template>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
        @select="drawerVisible = false"
      >
        <el-menu-item index="/home">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
        <el-menu-item index="/resume">
          <el-icon><Document /></el-icon>
          <span>简历审查</span>
        </el-menu-item>
        <el-menu-item index="/interview">
          <el-icon><Microphone /></el-icon>
          <span>模拟面试</span>
        </el-menu-item>
        <el-menu-item index="/code">
          <el-icon><Monitor /></el-icon>
          <span>代码检查</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>

    <el-aside v-if="!isMobile" width="240px" class="sidebar">
      <div class="sidebar-logo">
        <span class="logo-icon">🐟</span>
        <span class="logo-text">小鱼教育AI</span>
      </div>
      <div class="sidebar-divider"></div>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/home">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
        <el-menu-item index="/resume">
          <el-icon><Document /></el-icon>
          <span>简历审查</span>
        </el-menu-item>
        <el-menu-item index="/interview">
          <el-icon><Microphone /></el-icon>
          <span>模拟面试</span>
        </el-menu-item>
        <el-menu-item index="/code">
          <el-icon><Monitor /></el-icon>
          <span>代码检查</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <div class="user-info" @click="handleLogout">
          <div class="user-avatar">{{ userStore.userInfo?.username?.charAt(0)?.toUpperCase() }}</div>
          <div class="user-detail">
            <div class="user-name">{{ userStore.userInfo?.username }}</div>
            <div class="user-action">退出登录</div>
          </div>
          <el-icon class="logout-icon"><SwitchButton /></el-icon>
        </div>
      </div>
    </el-aside>

    <el-container>
      <el-header v-if="!isMobile" class="header" height="56px">
        <div class="header-left">
          <h2 class="page-title">{{ currentTitle }}</h2>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ChatDotRound, Document, Microphone, Monitor, Menu, SwitchButton, UserFilled, HomeFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const drawerVisible = ref(false)
const isMobile = ref(false)

const activeMenu = computed(() => route.path)

const titleMap = {
  '/home': '首页',
  '/chat': '智能问答',
  '/resume': '简历审查',
  '/interview': '模拟面试',
  '/code': '代码检查',
}

const currentTitle = computed(() => titleMap[route.path] || '小鱼教育AI')

function checkMobile() {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  if (!userStore.userInfo) {
    userStore.fetchUserInfo()
  }
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background: var(--color-bg-sidebar);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: none;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 24px;
}

.logo-icon {
  font-size: 28px;
  line-height: 1;
}

.logo-text {
  font-size: 17px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
}

.sidebar-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin: 0 16px;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  background: transparent;
  padding: 8px 12px;
}

.sidebar-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.55);
  border-radius: var(--radius-sm);
  margin-bottom: 4px;
  height: 44px;
  line-height: 44px;
  font-size: 14px;
  transition: all var(--transition-fast);
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.85);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--color-primary);
  color: #fff;
  box-shadow: 0 2px 8px rgba(79, 110, 247, 0.4);
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  font-size: 18px;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.06);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-detail {
  flex: 1;
  min-width: 0;
}

.user-name {
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  font-weight: 500;
}

.user-action {
  color: rgba(255, 255, 255, 0.35);
  font-size: 11px;
  margin-top: 1px;
}

.logout-icon {
  color: rgba(255, 255, 255, 0.25);
  font-size: 14px;
}

.header {
  display: flex;
  align-items: center;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border-light);
  padding: 0 28px;
}

.page-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.main-content {
  background: var(--color-bg-page);
  overflow-y: auto;
  padding: 24px;
}

.mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border-light);
  flex-shrink: 0;
}

.mobile-menu-btn {
  color: var(--color-text-regular) !important;
}

.mobile-logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-logo .logo-icon {
  font-size: 22px;
}

.mobile-logo .logo-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
}

:deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

:deep(.el-drawer__body) {
  padding: 0;
  background: var(--color-bg-sidebar);
}

@media (max-width: 768px) {
  .main-content {
    padding: 16px;
  }
}
</style>
