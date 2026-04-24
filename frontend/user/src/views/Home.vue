<template>
  <div class="home-page">
    <div class="header">
      <h1>🐟 小鱼教育AI智能助手</h1>
      <p class="subtitle">智能问答 · 代码检查 · 模拟面试 · 简历审查</p>
    </div>

    <div class="modules-grid">
      <div class="module-card" @click="navigateTo('/chat')">
        <div class="module-icon">💬</div>
        <h2 class="module-title">智能问答</h2>
        <p class="module-desc">基于知识库的智能问答系统，支持RAG检索增强生成</p>
        <div class="module-features">
          <span class="feature-tag">混合检索</span>
          <span class="feature-tag">HyDE技术</span>
          <span class="feature-tag">流式响应</span>
        </div>
      </div>

      <div class="module-card" @click="navigateTo('/code')">
        <div class="module-icon">💻</div>
        <h2 class="module-title">代码检查</h2>
        <p class="module-desc">智能代码审查，识别语法、逻辑、复杂度问题</p>
        <div class="module-features">
          <span class="feature-tag">沙箱执行</span>
          <span class="feature-tag">多维分析</span>
          <span class="feature-tag">错误标签</span>
        </div>
      </div>

      <div class="module-card" @click="navigateTo('/interview')">
        <div class="module-icon">🎯</div>
        <h2 class="module-title">模拟面试</h2>
        <p class="module-desc">四阶段模拟面试，动态出题，双轨评估</p>
        <div class="module-features">
          <span class="feature-tag">动态出题</span>
          <span class="feature-tag">薄弱点追踪</span>
          <span class="feature-tag">能力雷达</span>
        </div>
      </div>

      <div class="module-card" @click="navigateTo('/resume')">
        <div class="module-icon">📄</div>
        <h2 class="module-title">简历审查</h2>
        <p class="module-desc">六维度全面评估，提供具体修改建议</p>
        <div class="module-features">
          <span class="feature-tag">并行评估</span>
          <span class="feature-tag">优先级建议</span>
          <span class="feature-tag">雷达图</span>
        </div>
      </div>
    </div>

    <div class="footer">
      <p>Powered by LangChain + LangGraph + Milvus</p>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function navigateTo(path) {
  router.push(path)
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.header {
  text-align: center;
  margin-bottom: 60px;
  animation: fadeInDown 0.8s ease-out;
}

.header h1 {
  font-size: 48px;
  color: white;
  margin: 0 0 16px 0;
  font-weight: 700;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
}

.subtitle {
  font-size: 20px;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
  font-weight: 300;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  max-width: 1400px;
  width: 100%;
  margin-bottom: 60px;
}

.module-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  animation: fadeInUp 0.8s ease-out;
  animation-fill-mode: both;
}

.module-card:nth-child(1) {
  animation-delay: 0.1s;
}

.module-card:nth-child(2) {
  animation-delay: 0.2s;
}

.module-card:nth-child(3) {
  animation-delay: 0.3s;
}

.module-card:nth-child(4) {
  animation-delay: 0.4s;
}

.module-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
}

.module-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.module-title {
  font-size: 20px;
  color: #333;
  margin: 0 0 12px 0;
  font-weight: 600;
}

.module-desc {
  font-size: 14px;
  color: #666;
  margin: 0 0 20px 0;
  line-height: 1.6;
}

.module-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feature-tag {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.footer {
  text-align: center;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  margin-top: auto;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1200px) {
  .modules-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
  
  .module-card {
    padding: 20px;
  }
  
  .module-icon {
    font-size: 36px;
  }
  
  .module-title {
    font-size: 18px;
  }
}

@media (max-width: 768px) {
  .header h1 {
    font-size: 32px;
  }

  .subtitle {
    font-size: 16px;
  }

  .modules-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .module-card {
    padding: 24px;
  }

  .module-title {
    font-size: 20px;
  }
}
</style>
