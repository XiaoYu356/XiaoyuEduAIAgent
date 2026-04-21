<template>
  <div class="login-container">
    <div class="login-bg">
      <div class="bg-shape shape-1"></div>
      <div class="bg-shape shape-2"></div>
      <div class="bg-shape shape-3"></div>
    </div>
    <div class="login-card-wrapper">
      <div class="login-brand">
        <span class="brand-icon">🐟</span>
        <h1 class="brand-title">小鱼教育AI助手</h1>
        <p class="brand-subtitle">智能学习 · 高效成长</p>
      </div>
      <el-card class="login-card">
        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="登录" name="login">
            <el-form :model="loginForm" @submit.prevent="handleLogin" label-position="top">
              <el-form-item>
                <el-input v-model="loginForm.username" placeholder="用户名" size="large" prefix-icon="User" />
              </el-form-item>
              <el-form-item>
                <el-input v-model="loginForm.password" type="password" placeholder="密码" show-password size="large" prefix-icon="Lock" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleLogin" :loading="loading" style="width: 100%" size="large">
                  登 录
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
          <el-tab-pane label="注册" name="register">
            <el-form :model="registerForm" @submit.prevent="handleRegister" label-position="top">
              <el-form-item>
                <el-input v-model="registerForm.username" placeholder="用户名" size="large" prefix-icon="User" />
              </el-form-item>
              <el-form-item>
                <el-input v-model="registerForm.email" placeholder="邮箱" size="large" prefix-icon="Message" />
              </el-form-item>
              <el-form-item>
                <el-input v-model="registerForm.password" type="password" placeholder="密码" show-password size="large" prefix-icon="Lock" />
              </el-form-item>
              <el-form-item>
                <el-input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" show-password size="large" prefix-icon="Lock" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleRegister" :loading="loading" style="width: 100%" size="large">
                  注 册
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const activeTab = ref('login')

const loginForm = ref({ username: '', password: '' })
const registerForm = ref({ username: '', email: '', password: '', confirmPassword: '' })

async function handleLogin() {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(loginForm.value.username, loginForm.value.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    const msg = e.message || ''
    if (msg.includes('禁用')) {
      ElMessage.error('该账户已被禁用，请联系管理员')
    } else if (msg.includes('用户名或密码')) {
      ElMessage.error('用户名或密码错误')
    } else {
      ElMessage.error(msg || '登录失败')
    }
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!registerForm.value.username || !registerForm.value.email || !registerForm.value.password) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    ElMessage.warning('两次密码输入不一致')
    return
  }
  if (registerForm.value.password.length < 6) {
    ElMessage.warning('密码长度至少6位')
    return
  }
  loading.value = true
  try {
    await userStore.register(
      registerForm.value.username,
      registerForm.value.email,
      registerForm.value.password
    )
    ElMessage.success('注册成功，已自动登录')
    router.push('/')
  } catch (e) {
    const msg = e.message || ''
    if (msg.includes('用户名已存在')) {
      ElMessage.error('用户名已被使用')
    } else if (msg.includes('邮箱已存在')) {
      ElMessage.error('邮箱已被注册')
    } else {
      ElMessage.error(msg || '注册失败')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(160deg, #0f172a 0%, #1e293b 40%, #334155 100%);
}

.login-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}

.shape-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(79, 110, 247, 0.4), transparent 70%);
  top: -200px;
  right: -100px;
  animation: float1 20s ease-in-out infinite;
}

.shape-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(123, 147, 250, 0.3), transparent 70%);
  bottom: -150px;
  left: -100px;
  animation: float2 25s ease-in-out infinite;
}

.shape-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(52, 211, 153, 0.2), transparent 70%);
  top: 50%;
  left: 50%;
  animation: float3 15s ease-in-out infinite;
}

@keyframes float1 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-40px, 30px); }
}

@keyframes float2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -40px); }
}

@keyframes float3 {
  0%, 100% { transform: translate(-50%, -50%); }
  50% { transform: translate(-50%, -50%) translate(20px, -20px); }
}

.login-card-wrapper {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
}

.login-brand {
  text-align: center;
}

.brand-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
  filter: drop-shadow(0 4px 12px rgba(79, 110, 247, 0.3));
}

.brand-title {
  color: #fff;
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  letter-spacing: 1px;
}

.brand-subtitle {
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  margin-top: 8px;
  letter-spacing: 2px;
}

.login-card {
  width: 400px;
  border-radius: var(--radius-lg) !important;
  backdrop-filter: blur(20px);
  background: rgba(255, 255, 255, 0.95) !important;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.25) !important;
}

.login-tabs {
  margin-top: 4px;
}

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: var(--color-border-light);
}

.login-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
}

.login-tabs :deep(.el-form-item) {
  margin-bottom: 20px;
}

@media (max-width: 480px) {
  .login-card {
    width: calc(100vw - 32px);
    margin: 0 16px;
  }
  .brand-title {
    font-size: 22px;
  }
}
</style>
