<template>
  <div class="page-grid">
    <section class="panel" style="padding: 20px;">
      <div class="panel-head">
        <div>
          <h3 class="panel-title">成绩管理</h3>
          <div class="soft-note">查看已录入成绩，支持筛选、修改、删除与统计。</div>
        </div>
      </div>

      <div class="toolbar" style="margin-bottom: 18px;">
        <div class="toolbar-filters">
          <el-select v-model="filters.exam" clearable placeholder="考试" style="width: 220px">
            <el-option v-for="item in exams" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-select v-model="filters.classId" clearable placeholder="班级" style="width: 180px">
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-select v-model="filters.subject" clearable placeholder="科目" style="width: 180px">
            <el-option v-for="item in subjects" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-button type="primary" @click="loadScores">查询</el-button>
        </div>
      </div>

      <div v-if="stats" class="hero-grid" style="margin-bottom: 18px;">
        <div class="metric-card">
          <div class="metric-label">成绩条数</div>
          <div class="metric-value">{{ stats.total_count }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">平均分</div>
          <div class="metric-value">{{ Number(stats.average_score || 0).toFixed(1) }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">及格率</div>
          <div class="metric-value">{{ stats.pass_rate || 0 }}%</div>
        </div>
      </div>

      <el-table :data="scores" border stripe>
        <el-table-column prop="student_name" label="学生" width="120" />
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="class_name" label="班级" width="140" />
        <el-table-column prop="exam_name" label="考试" min-width="180" />
        <el-table-column prop="subject_name" label="科目" width="120" />
        <el-table-column prop="score" label="成绩" width="110" />
        <el-table-column prop="created_by_name" label="录入人" width="120" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="removeScore(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" title="编辑成绩" width="420px">
      <el-form :model="form" label-width="86px">
        <el-form-item label="学生"><el-input :model-value="form.student_name" disabled /></el-form-item>
        <el-form-item label="考试"><el-input :model-value="form.exam_name" disabled /></el-form-item>
        <el-form-item label="科目"><el-input :model-value="form.subject_name" disabled /></el-form-item>
        <el-form-item label="成绩"><el-input-number v-model="form.score" :min="0" :max="150" :precision="1" style="width: 100%" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue"
import { ElMessageBox } from "element-plus"
import { classAPI, examAPI, scoreAPI, subjectAPI } from "@/api"

const exams = ref([])
const classes = ref([])
const subjects = ref([])
const scores = ref([])
const stats = ref(null)
const dialogVisible = ref(false)
const submitting = ref(false)

const filters = reactive({ exam: "", classId: "", subject: "" })
const form = reactive({})

async function loadBase() {
  const [examData, classData, subjectData] = await Promise.all([examAPI.list(), classAPI.list(), subjectAPI.list()])
  exams.value = examData.results || examData
  classes.value = classData.results || classData
  subjects.value = subjectData.results || subjectData
}

async function loadScores() {
  const params = {
    exam: filters.exam || undefined,
    subject: filters.subject || undefined,
    "student__class_obj": filters.classId || undefined,
  }
  const data = await scoreAPI.list(params)
  scores.value = data.results || data
  stats.value = await scoreAPI.statistics({
    exam_id: filters.exam || "",
    subject_id: filters.subject || "",
    class_id: filters.classId || "",
  })
}

function openEdit(row) {
  Object.assign(form, row)
  dialogVisible.value = true
}

async function submitEdit() {
  submitting.value = true
  try {
    await scoreAPI.update(form.id, {
      student: form.student,
      exam: form.exam,
      subject: form.subject,
      score: form.score,
      notes: form.notes || "",
    })
    dialogVisible.value = false
    await loadScores()
  } finally {
    submitting.value = false
  }
}

async function removeScore(row) {
  await ElMessageBox.confirm(`确定删除 ${row.student_name} 的 ${row.subject_name} 成绩吗？`, "提示", { type: "warning" })
  await scoreAPI.remove(row.id)
  await loadScores()
}

onMounted(async () => {
  await loadBase()
  await loadScores()
})
</script>
