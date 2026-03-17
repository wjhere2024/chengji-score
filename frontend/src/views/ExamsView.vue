<template>
  <div class="page-grid">
    <section class="panel" style="padding: 20px;">
      <div class="panel-head">
        <div>
          <h3 class="panel-title">考试管理</h3>
          <div class="soft-note">创建考试后可按年级分配科目，并直接进入成绩录入。</div>
        </div>
        <el-button type="primary" @click="openCreate">新增考试</el-button>
      </div>

      <div class="hero-grid" style="margin-bottom: 18px;">
        <div class="metric-card">
          <div class="metric-label">考试数量</div>
          <div class="metric-value">{{ exams.length }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">已发布</div>
          <div class="metric-value">{{ exams.filter((item) => item.is_published).length }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">活跃考试</div>
          <div class="metric-value">{{ exams.filter((item) => item.is_active).length }}</div>
        </div>
      </div>

      <el-table :data="exams" border stripe>
        <el-table-column prop="name" label="考试名称" min-width="180" />
        <el-table-column prop="exam_type_display" label="类型" width="120" />
        <el-table-column prop="academic_year" label="学年" width="120" />
        <el-table-column prop="semester" label="学期" width="120" />
        <el-table-column prop="exam_date" label="日期" width="120" />
        <el-table-column label="发布" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_published ? 'success' : 'info'">{{ row.is_published ? "已发布" : "未发布" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="科目" min-width="220">
          <template #default="{ row }">
            {{ (row.subjects_info || []).map((item) => item.name).join(" / ") }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="success" @click="togglePublish(row)">{{ row.is_published ? "撤回" : "发布" }}</el-button>
            <el-button link type="danger" @click="removeExam(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑考试' : '新增考试'" width="640px">
      <el-form :model="form" label-width="96px">
        <el-form-item label="考试名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="考试类型">
          <el-select v-model="form.exam_type" style="width: 100%">
            <el-option label="月考" value="monthly" />
            <el-option label="期中考试" value="midterm" />
            <el-option label="期末考试" value="final" />
            <el-option label="测验" value="quiz" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="学年"><el-input v-model="form.academic_year" /></el-form-item>
        <el-form-item label="学期"><el-input v-model="form.semester" /></el-form-item>
        <el-form-item label="考试日期"><el-date-picker v-model="form.exam_date" value-format="YYYY-MM-DD" type="date" style="width: 100%" /></el-form-item>
        <el-form-item label="适用年级">
          <el-checkbox-group v-model="form.applicable_grades">
            <el-checkbox v-for="grade in [1,2,3,4,5,6]" :key="grade" :label="grade">{{ grade }} 年级</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="考试科目">
          <el-checkbox-group v-model="form.subjects">
            <el-checkbox v-for="item in subjects" :key="item.id" :label="item.id">{{ item.name }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitExam">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue"
import { ElMessageBox } from "element-plus"
import { examAPI, subjectAPI } from "@/api"

const exams = ref([])
const subjects = ref([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)

const form = reactive({
  name: "",
  exam_type: "midterm",
  academic_year: "2024-2025",
  semester: "第一学期",
  exam_date: "",
  applicable_grades: [1],
  subjects: [],
  description: "",
  is_published: false,
  is_active: true,
})

function resetForm() {
  editingId.value = null
  Object.assign(form, {
    name: "",
    exam_type: "midterm",
    academic_year: "2024-2025",
    semester: "第一学期",
    exam_date: "",
    applicable_grades: [1],
    subjects: subjects.value.slice(0, 2).map((item) => item.id),
    description: "",
    is_published: false,
    is_active: true,
  })
}

async function loadSubjects() {
  const data = await subjectAPI.list()
  subjects.value = data.results || data
}

async function loadExams() {
  const data = await examAPI.list()
  exams.value = data.results || data
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    ...row,
    subjects: (row.subjects_info || []).map((item) => item.id),
  })
  dialogVisible.value = true
}

async function submitExam() {
  submitting.value = true
  try {
    if (editingId.value) {
      await examAPI.update(editingId.value, form)
    } else {
      await examAPI.create(form)
    }
    dialogVisible.value = false
    await loadExams()
  } finally {
    submitting.value = false
  }
}

async function togglePublish(row) {
  if (row.is_published) {
    await examAPI.unpublish(row.id)
  } else {
    await examAPI.publish(row.id)
  }
  await loadExams()
}

async function removeExam(row) {
  await ElMessageBox.confirm(`确定删除考试 ${row.name} 吗？`, "提示", { type: "warning" })
  await examAPI.remove(row.id)
  await loadExams()
}

onMounted(async () => {
  await loadSubjects()
  await loadExams()
  resetForm()
})
</script>
