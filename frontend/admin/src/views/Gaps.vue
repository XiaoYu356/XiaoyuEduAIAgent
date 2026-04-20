<template>
  <div class="gaps-container">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>知识缺口管理</span>
          <div style="display: flex; gap: 12px; align-items: center">
            <el-select v-model="kbFilter" placeholder="全部知识库" clearable @change="loadGaps" style="width: 200px">
              <el-option v-for="kb in knowledgeBases" :key="kb.id" :label="kb.name" :value="kb.id" />
            </el-select>
            <el-radio-group v-model="statusFilter" @change="loadGaps">
              <el-radio-button value="open">待处理</el-radio-button>
              <el-radio-button value="resolved">已补录</el-radio-button>
              <el-radio-button value="ignored">已忽略</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>
      <el-table :data="gaps" stripe>
        <el-table-column label="序号" width="80">
          <template #default="{ $index }">
            {{ $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="question" label="问题" min-width="300" />
        <el-table-column prop="kb_name" label="知识库" width="150">
          <template #default="{ row }">
            {{ row.kb_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <template v-if="row.status === 'open'">
              <el-button size="small" type="primary" @click="showResolveDialog(row)">
                补录
              </el-button>
              <el-button size="small" @click="showIgnoreDialog(row)">
                忽略
              </el-button>
            </template>
            <template v-else>
              <el-button size="small" @click="showDetailDialog(row)">
                查看
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="resolveDialogVisible" title="补录知识" width="500px">
      <el-form :model="resolveForm" label-position="top">
        <el-form-item label="问题">
          <el-input :model-value="resolveForm.question" disabled type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="答案">
          <el-input v-model="resolveForm.answer" type="textarea" :rows="6" placeholder="请输入答案" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="resolveGap" :loading="resolveLoading">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ignoreDialogVisible" title="忽略知识缺口" width="500px">
      <el-form :model="ignoreForm" label-position="top">
        <el-form-item label="问题">
          <el-input :model-value="ignoreForm.question" disabled type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="忽略原因（可选）">
          <el-input v-model="ignoreForm.reason" type="textarea" :rows="3" placeholder="请输入忽略原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ignoreDialogVisible = false">取消</el-button>
        <el-button type="warning" @click="ignoreGap" :loading="ignoreLoading">确认忽略</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialogVisible" title="详情" width="500px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="问题">{{ detailForm.question }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(detailForm.status)">{{ statusLabel(detailForm.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="答案/原因">{{ detailForm.answer || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detailForm.created_at }}</el-descriptions-item>
        <el-descriptions-item v-if="detailForm.resolved_at" label="处理时间">{{ detailForm.resolved_at }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../utils/api'
import { ElMessage } from 'element-plus'

const gaps = ref([])
const knowledgeBases = ref([])
const statusFilter = ref('open')
const kbFilter = ref(null)
const resolveDialogVisible = ref(false)
const resolveLoading = ref(false)
const resolveForm = ref({ id: null, question: '', answer: '' })
const ignoreDialogVisible = ref(false)
const ignoreLoading = ref(false)
const ignoreForm = ref({ id: null, question: '', reason: '' })
const detailDialogVisible = ref(false)
const detailForm = ref({})

async function loadKnowledgeBases() {
  try {
    const res = await api.get('/knowledge')
    knowledgeBases.value = res.data || []
  } catch {
    console.error('加载知识库列表失败')
  }
}

async function loadGaps() {
  try {
    const params = { status: statusFilter.value }
    if (kbFilter.value) {
      params.kb_id = kbFilter.value
    }
    const res = await api.get('/knowledge/gaps', { params })
    gaps.value = res.data || []
  } catch {
    ElMessage.error('加载知识缺口失败')
  }
}

function statusTagType(status) {
  const map = { open: 'danger', in_progress: 'warning', resolved: 'success', ignored: 'info' }
  return map[status] || 'info'
}

function statusLabel(status) {
  const map = { open: '待处理', in_progress: '处理中', resolved: '已补录', ignored: '已忽略' }
  return map[status] || status
}

function showResolveDialog(gap) {
  resolveForm.value = { id: gap.id, question: gap.question, answer: gap.answer || '' }
  resolveDialogVisible.value = true
}

function showIgnoreDialog(gap) {
  ignoreForm.value = { id: gap.id, question: gap.question, reason: '' }
  ignoreDialogVisible.value = true
}

function showDetailDialog(gap) {
  detailForm.value = gap
  detailDialogVisible.value = true
}

async function resolveGap() {
  if (!resolveForm.value.answer.trim()) {
    ElMessage.warning('请输入答案')
    return
  }
  resolveLoading.value = true
  try {
    await api.put(`/knowledge/gaps/${resolveForm.value.id}/resolve`, {
      answer: resolveForm.value.answer,
    })
    resolveDialogVisible.value = false
    gaps.value = gaps.value.filter(g => g.id !== resolveForm.value.id)
    ElMessage.success('补录成功')
  } catch (e) {
    ElMessage.error(e.message || '补录失败')
  } finally {
    resolveLoading.value = false
  }
}

async function ignoreGap() {
  ignoreLoading.value = true
  try {
    await api.put(`/knowledge/gaps/${ignoreForm.value.id}/ignore`, {
      reason: ignoreForm.value.reason,
    })
    ignoreDialogVisible.value = false
    gaps.value = gaps.value.filter(g => g.id !== ignoreForm.value.id)
    ElMessage.success('已忽略')
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    ignoreLoading.value = false
  }
}

onMounted(() => {
  loadKnowledgeBases()
  loadGaps()
})
</script>

<style scoped>
.gaps-container {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
