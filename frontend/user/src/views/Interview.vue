<template>
  <div class="interview-container">
    <div v-if="!interviewStarted" class="interview-start">
      <el-card>
        <template #header>
          <span>开始模拟面试</span>
        </template>
        <el-form :model="form" label-position="top">
          <el-form-item label="简历（可选，用于针对性出题）">
            <div class="resume-selector">
              <el-select v-model="form.resume_id" placeholder="选择已上传的简历" clearable style="flex: 1;">
                <el-option
                  v-for="r in resumes"
                  :key="r.id"
                  :label="getResumeLabel(r)"
                  :value="r.id"
                >
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>{{ getResumeFilename(r.file_path) }}</span>
                    <el-tag size="small" :type="r.has_review ? 'success' : 'info'" style="margin-left: 8px;">
                      {{ r.has_review ? '已审查' : '未审查' }}
                    </el-tag>
                  </div>
                </el-option>
              </el-select>
              <el-upload
                :show-file-list="false"
                :before-upload="handleUploadResume"
                accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.gif"
              >
                <el-button type="primary" plain :loading="uploading">
                  上传新简历
                </el-button>
              </el-upload>
            </div>
            <div v-if="newResumeId" class="upload-success">
              <el-tag type="success">新简历已上传</el-tag>
            </div>
          </el-form-item>
          <el-form-item label="重点关注领域（可选）">
            <el-select v-model="form.focus_areas" multiple placeholder="选择关注领域" style="width: 100%">
              <el-option label="Java" value="java" />
              <el-option label="Python" value="python" />
              <el-option label="前端" value="frontend" />
              <el-option label="数据库" value="database" />
              <el-option label="系统设计" value="system_design" />
            </el-select>
          </el-form-item>
          <el-button type="primary" @click="startInterview" :loading="loading" style="width: 100%">
            开始面试
          </el-button>
        </el-form>
      </el-card>

      <el-card v-if="interviewHistory.length > 0" style="margin-top: 20px">
        <template #header>
          <span>历史面试记录</span>
        </template>
        <el-table :data="interviewHistory" style="width: 100%">
          <el-table-column type="index" label="序号" width="80" />
          <el-table-column label="综合评分" width="100">
            <template #default="{ row }">
              <el-tag :type="getScoreType(row.overall_score)">{{ row.overall_score }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="技术/表达" width="120">
            <template #default="{ row }">
              {{ row.tech_score }} / {{ row.expression_score }}
            </template>
          </el-table-column>
          <el-table-column label="时间">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button type="primary" link @click="viewHistoryDetail(row.id)">查看</el-button>
              <el-button type="danger" link @click="deleteInterviewReport(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <div v-else class="interview-chat">
      <div class="stage-indicator">
        <el-steps :active="stageIndex" align-center>
          <el-step title="自我介绍" />
          <el-step title="技术问题" />
          <el-step title="项目经验" />
          <el-step title="面试报告" />
        </el-steps>
      </div>
      <div class="chat-messages" ref="messagesRef">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message-item', msg.role === 'user' ? 'message-user' : 'message-assistant']"
        >
          <div class="message-avatar">{{ msg.role === 'user' ? '👤' : '🎯' }}</div>
          <div class="message-content">
            <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
      </div>
      <div class="chat-input" v-if="currentStage !== 'REPORT'">
        <el-input
          v-model="inputText"
          placeholder="输入你的回答..."
          @keydown.enter="sendResponse"
          :disabled="loading"
          size="large"
        >
          <template #append>
            <el-button @click="sendResponse" :loading="loading" type="primary">发送</el-button>
          </template>
        </el-input>
      </div>
      <div class="report-section" v-if="currentStage === 'REPORT'">
        <div v-if="!reportData && !streamingReport" style="text-align: center; padding: 60px;">
          <el-empty description="面试已结束">
            <el-button type="primary" size="large" @click="generateReport" :loading="generatingReport">
              生成面试报告
            </el-button>
          </el-empty>
        </div>
        <div v-else-if="streamingReport" style="padding: 20px;">
          <el-progress :percentage="reportProgress" :format="() => '生成中...'" style="margin-bottom: 20px;" />
          <div ref="radarRef" style="height: 400px"></div>
          <div class="report-content streaming" v-html="renderMarkdown(streamingContent)"></div>
        </div>
        <div v-else class="report-container">
          <div class="score-cards">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-card shadow="hover" class="score-card">
                  <el-statistic title="综合评分" :value="reportData?.overall_score || 0">
                    <template #suffix>
                      <span class="score-suffix">分</span>
                    </template>
                  </el-statistic>
                  <el-progress 
                    :percentage="reportData?.overall_score || 0" 
                    :color="getProgressColor(reportData?.overall_score)"
                    :show-text="false"
                    style="margin-top: 10px;"
                  />
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card shadow="hover" class="score-card">
                  <el-statistic title="技术深度" :value="reportData?.tech_score || 0">
                    <template #suffix>
                      <span class="score-suffix">分</span>
                    </template>
                  </el-statistic>
                  <el-progress 
                    :percentage="reportData?.tech_score || 0" 
                    :color="getProgressColor(reportData?.tech_score)"
                    :show-text="false"
                    style="margin-top: 10px;"
                  />
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card shadow="hover" class="score-card">
                  <el-statistic title="表达能力" :value="reportData?.expression_score || 0">
                    <template #suffix>
                      <span class="score-suffix">分</span>
                    </template>
                  </el-statistic>
                  <el-progress 
                    :percentage="reportData?.expression_score || 0" 
                    :color="getProgressColor(reportData?.expression_score)"
                    :show-text="false"
                    style="margin-top: 10px;"
                  />
                </el-card>
              </el-col>
            </el-row>
          </div>

          <el-card class="radar-card">
            <template #header><span>能力雷达图</span></template>
            <div ref="radarRef" style="height: 350px"></div>
          </el-card>

          <el-card class="comment-card">
            <template #header><span>总体评价</span></template>
            <p class="overall-comment">{{ reportData?.overall_comment }}</p>
          </el-card>

          <el-row :gutter="16" style="margin-top: 16px;">
            <el-col :span="12">
              <el-card class="analysis-card strength-card">
                <template #header>
                  <span class="card-title">
                    <el-icon><CircleCheck /></el-icon> 优势
                  </span>
                </template>
                <ul v-if="reportData?.strengths?.length">
                  <li v-for="(s, i) in reportData.strengths" :key="i">{{ s }}</li>
                </ul>
                <el-empty v-else description="暂无" :image-size="60" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="analysis-card weakness-card">
                <template #header>
                  <span class="card-title">
                    <el-icon><Warning /></el-icon> 不足
                  </span>
                </template>
                <ul v-if="reportData?.weaknesses?.length">
                  <li v-for="(w, i) in reportData.weaknesses" :key="i">{{ w }}</li>
                </ul>
                <el-empty v-else description="暂无" :image-size="60" />
              </el-card>
            </el-col>
          </el-row>

          <el-card class="suggestions-card" style="margin-top: 16px;">
            <template #header>
              <span class="card-title">
                <el-icon><Promotion /></el-icon> 改进建议
              </span>
            </template>
            <ol v-if="reportData?.suggestions?.length" class="suggestions-list">
              <li v-for="(s, i) in reportData.suggestions" :key="i">{{ s }}</li>
            </ol>
            <el-empty v-else description="暂无" :image-size="60" />
          </el-card>

          <el-card class="feedback-card" style="margin-top: 16px;">
            <template #header>
              <span class="card-title">
                <el-icon><Document /></el-icon> 详细反馈
              </span>
            </template>
            <div class="report-content" v-html="renderMarkdown(reportData?.detailed_feedback || '')"></div>
          </el-card>

          <div style="text-align: center; margin-top: 24px;">
            <el-button type="primary" size="large" @click="resetInterview">
              开始新面试
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showHistoryDetail" title="面试详情" width="800px" class="history-dialog">
      <div v-if="historyDetail" class="history-detail">
        <div class="score-cards" style="margin-bottom: 16px;">
          <el-row :gutter="16">
            <el-col :span="8">
              <el-card shadow="hover" class="score-card">
                <el-statistic title="综合评分" :value="historyDetail.overall_score || 0">
                  <template #suffix><span class="score-suffix">分</span></template>
                </el-statistic>
                <el-progress 
                  :percentage="historyDetail.overall_score || 0" 
                  :color="getProgressColor(historyDetail.overall_score)"
                  :show-text="false"
                  style="margin-top: 10px;"
                />
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="score-card">
                <el-statistic title="技术深度" :value="historyDetail.tech_score || 0">
                  <template #suffix><span class="score-suffix">分</span></template>
                </el-statistic>
                <el-progress 
                  :percentage="historyDetail.tech_score || 0" 
                  :color="getProgressColor(historyDetail.tech_score)"
                  :show-text="false"
                  style="margin-top: 10px;"
                />
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="score-card">
                <el-statistic title="表达能力" :value="historyDetail.expression_score || 0">
                  <template #suffix><span class="score-suffix">分</span></template>
                </el-statistic>
                <el-progress 
                  :percentage="historyDetail.expression_score || 0" 
                  :color="getProgressColor(historyDetail.expression_score)"
                  :show-text="false"
                  style="margin-top: 10px;"
                />
              </el-card>
            </el-col>
          </el-row>
        </div>
        <el-card style="margin-bottom: 16px;">
          <template #header><span>能力雷达图</span></template>
          <div ref="historyRadarRef" style="height: 300px"></div>
        </el-card>
        <el-row :gutter="16" style="margin-bottom: 16px;">
          <el-col :span="12">
            <el-card class="analysis-card strength-card">
              <template #header>
                <span class="card-title"><el-icon><CircleCheck /></el-icon> 优势</span>
              </template>
              <ul v-if="historyDetail.strengths?.length">
                <li v-for="(s, i) in historyDetail.strengths" :key="i">{{ s }}</li>
              </ul>
              <el-empty v-else description="暂无" :image-size="50" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card class="analysis-card weakness-card">
              <template #header>
                <span class="card-title"><el-icon><Warning /></el-icon> 不足</span>
              </template>
              <ul v-if="historyDetail.weaknesses?.length">
                <li v-for="(w, i) in historyDetail.weaknesses" :key="i">{{ w }}</li>
              </ul>
              <el-empty v-else description="暂无" :image-size="50" />
            </el-card>
          </el-col>
        </el-row>
        <el-card class="suggestions-card" style="margin-bottom: 16px;">
          <template #header>
            <span class="card-title"><el-icon><Promotion /></el-icon> 改进建议</span>
          </template>
          <ol v-if="historyDetail.suggestions?.length" class="suggestions-list">
            <li v-for="(s, i) in historyDetail.suggestions" :key="i">{{ s }}</li>
          </ol>
          <el-empty v-else description="暂无" :image-size="50" />
        </el-card>
        <el-card v-if="historyDetail.overall_comment" style="margin-bottom: 16px;">
          <template #header>
            <span class="card-title"><el-icon><ChatDotRound /></el-icon> 总体评价</span>
          </template>
          <p class="overall-comment">{{ historyDetail.overall_comment }}</p>
        </el-card>
        <el-card v-if="historyDetail.detailed_feedback">
          <template #header>
            <span class="card-title"><el-icon><Document /></el-icon> 详细反馈</span>
          </template>
          <div class="report-content" v-html="renderMarkdown(historyDetail.detailed_feedback)"></div>
        </el-card>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import api from '../utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Warning, Promotion, Document, ChatDotRound } from '@element-plus/icons-vue'
import { marked } from 'marked'
import * as echarts from 'echarts'

const loading = ref(false)
const interviewStarted = ref(false)
const conversationId = ref(null)
const currentStage = ref('INTRO')
const messages = ref([])
const inputText = ref('')
const messagesRef = ref(null)
const reportData = ref(null)
const radarRef = ref(null)
const resumes = ref([])
const interviewHistory = ref([])
const showHistoryDetail = ref(false)
const historyDetail = ref(null)
const historyRadarRef = ref(null)
const streamingReport = ref(false)
const streamingContent = ref('')
const reportProgress = ref(0)
const generatingReport = ref(false)
const uploading = ref(false)
const newResumeId = ref(null)

const form = ref({
  resume_id: null,
  focus_areas: [],
})

const stageIndex = computed(() => {
  const map = { INTRO: 0, TECH: 1, PROJECT: 2, REPORT: 3 }
  return map[currentStage.value] || 0
})

function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function getResumeFilename(filePath) {
  if (!filePath) return '未知文件'
  const parts = filePath.split('/')
  return parts[parts.length - 1] || filePath
}

function getResumeLabel(r) {
  const filename = getResumeFilename(r.file_path)
  const date = formatDate(r.created_at)
  return `${filename} (${date})`
}

function getScoreType(score) {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

function getProgressColor(score) {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

function formatReport(report) {
  if (!report) return ''
  let text = `## 总体评价\n${report.overall_comment || ''}\n\n`
  if (report.strengths && report.strengths.length) {
    text += `## 优势\n`
    report.strengths.forEach(s => text += `- ${s}\n`)
    text += '\n'
  }
  if (report.weaknesses && report.weaknesses.length) {
    text += `## 不足\n`
    report.weaknesses.forEach(w => text += `- ${w}\n`)
    text += '\n'
  }
  if (report.suggestions && report.suggestions.length) {
    text += `## 改进建议\n`
    report.suggestions.forEach(s => text += `- ${s}\n`)
    text += '\n'
  }
  if (report.detailed_feedback) {
    text += `## 详细反馈\n${report.detailed_feedback}\n`
  }
  return text
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

async function loadResumes() {
  try {
    const res = await api.get('/resume/list')
    resumes.value = Array.isArray(res) ? res : (res.data || [])
  } catch (e) {
    console.error('加载简历列表失败', e)
  }
}

async function handleUploadResume(file) {
  uploading.value = true
  newResumeId.value = null

  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await api.post('/resume/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (res.data?.resume_id) {
      form.value.resume_id = res.data.resume_id
      newResumeId.value = res.data.resume_id
      await loadResumes()
      ElMessage.success('简历上传成功')
    }
  } catch (e) {
    ElMessage.error('简历上传失败')
  } finally {
    uploading.value = false
  }

  return false
}

async function loadInterviewHistory() {
  try {
    const res = await api.get('/interview/history')
    interviewHistory.value = res.data || res || []
  } catch (e) {
    console.error('加载面试历史失败', e)
  }
}

async function startInterview() {
  loading.value = true
  try {
    const res = await api.post('/interview/start', form.value)
    const responseData = res.data || res
    conversationId.value = responseData.conversation_id
    currentStage.value = responseData.stage
    messages.value.push({ role: 'assistant', content: responseData.message })
    interviewStarted.value = true
    scrollToBottom()
  } catch (e) {
    console.error('启动面试失败:', e)
    ElMessage.error('启动面试失败')
  } finally {
    loading.value = false
  }
}

async function sendResponse() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await api.post('/interview/respond', {
      conversation_id: conversationId.value,
      message: text,
    })
    
    const responseData = res.data || res
    currentStage.value = responseData.stage
    messages.value.push({ role: 'assistant', content: responseData.message })

    if (responseData.stage === 'REPORT' && responseData.report && responseData.report.radar_data) {
      reportData.value = responseData.report
      nextTick(() => renderRadar(responseData.report.radar_data))
    }
    scrollToBottom()
  } catch (e) {
    console.error('发送失败:', e)
    ElMessage.error('发送失败')
  } finally {
    loading.value = false
  }
}

function renderRadar(data) {
  if (!radarRef.value || !data) return
  const chart = echarts.init(radarRef.value)
  chart.setOption({
    radar: {
      indicator: data.indicators.map((name) => ({ name, max: 100 })),
    },
    series: [
      {
        type: 'radar',
        data: [{ value: data.values, name: '面试评估', areaStyle: { opacity: 0.3 } }],
      },
    ],
  })
}

function renderHistoryRadar(data) {
  if (!historyRadarRef.value || !data) return
  const chart = echarts.init(historyRadarRef.value)
  chart.setOption({
    radar: {
      indicator: data.indicators.map((name) => ({ name, max: 100 })),
    },
    series: [
      {
        type: 'radar',
        data: [{ value: data.values, name: '面试评估', areaStyle: { opacity: 0.3 } }],
      },
    ],
  })
}

async function viewHistoryDetail(reportId) {
  try {
    const res = await api.get(`/interview/history/${reportId}`)
    const detail = res.data || res
    historyDetail.value = detail
    showHistoryDetail.value = true
    if (detail.radar_data) {
      nextTick(() => renderHistoryRadar(detail.radar_data))
    }
  } catch (e) {
    console.error('加载面试详情失败:', e)
    ElMessage.error('加载面试详情失败')
  }
}

async function deleteInterviewReport(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除该面试记录吗？`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await api.delete(`/interview/history/${row.id}`)
    ElMessage.success('删除成功')
    loadInterviewHistory()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function resetInterview() {
  interviewStarted.value = false
  conversationId.value = null
  currentStage.value = 'INTRO'
  messages.value = []
  reportData.value = null
  streamingReport.value = false
  streamingContent.value = ''
  reportProgress.value = 0
  newResumeId.value = null
  form.value = {
    resume_id: null,
    focus_areas: [],
  }
  loadInterviewHistory()
}

async function generateReport() {
  generatingReport.value = true
  streamingReport.value = true
  streamingContent.value = ''
  reportProgress.value = 0

  try {
    const token = localStorage.getItem('token')
    const response = await fetch(`/api/v1/interview/report/stream`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'text/event-stream',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ conversation_id: conversationId.value }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.content) {
              streamingContent.value += data.content
              reportProgress.value = Math.min(90, reportProgress.value + 2)
            }
            if (data.done) {
              reportProgress.value = 100
              if (data.report) {
                reportData.value = data.report
                nextTick(() => renderRadar(data.report.radar_data))
              }
              streamingReport.value = false
            }
          } catch (e) {
            console.error('Parse error', e)
          }
        }
      }
    }
  } catch (e) {
    ElMessage.error('生成报告失败')
    streamingReport.value = false
  } finally {
    generatingReport.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadResumes(), loadInterviewHistory()])
})
</script>

<style scoped>
.interview-container {
  max-width: 900px;
  margin: 0 auto;
}
.interview-start {
  padding: 20px;
}
.resume-selector {
  display: flex;
  gap: 12px;
  align-items: center;
}
.upload-success {
  margin-top: 8px;
}
.interview-chat {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}
.stage-indicator {
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.message-item {
  display: flex;
  margin-bottom: 16px;
  gap: 12px;
}
.message-user {
  flex-direction: row-reverse;
}
.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.message-content {
  max-width: 70%;
}
.message-text {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
}
.message-user .message-text {
  background: #409eff;
  color: #fff;
  border-top-right-radius: 4px;
}
.message-assistant .message-text {
  background: #f4f4f5;
  color: #303133;
  border-top-left-radius: 4px;
}
.chat-input {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
}
.report-section {
  padding: 20px;
  overflow-y: auto;
}
.report-container {
  max-width: 100%;
}
.score-cards {
  margin-bottom: 16px;
}
.score-card {
  text-align: center;
}
.score-card :deep(.el-statistic__content) {
  font-size: 32px;
}
.score-suffix {
  font-size: 16px;
  color: #909399;
}
.radar-card {
  margin-bottom: 16px;
}
.comment-card {
  margin-bottom: 16px;
}
.overall-comment {
  font-size: 15px;
  line-height: 1.8;
  color: #606266;
  margin: 0;
}
.analysis-card {
  min-height: 150px;
}
.analysis-card ul {
  padding-left: 20px;
  margin: 0;
}
.analysis-card li {
  margin: 8px 0;
  line-height: 1.6;
  color: #606266;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}
.strength-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%);
}
.weakness-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #fef0f0 0%, #fde2e2 100%);
}
.suggestions-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #fdf6ec 0%, #faecd8 100%);
}
.suggestions-list {
  padding-left: 20px;
  margin: 0;
}
.suggestions-list li {
  margin: 10px 0;
  line-height: 1.6;
  color: #606266;
}
.feedback-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #ecf5ff 0%, #d9ecff 100%);
}
.report-content {
  line-height: 1.8;
  font-size: 14px;
}
.report-content :deep(p) {
  margin: 10px 0;
}
.report-content :deep(ul), .report-content :deep(ol) {
  padding-left: 20px;
}
.report-content :deep(li) {
  margin: 6px 0;
}
.history-detail {
  padding: 10px;
}
.history-dialog :deep(.el-dialog__body) {
  max-height: 70vh;
  overflow-y: auto;
}
</style>
