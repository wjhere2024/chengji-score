<template>
  <div class="page-grid">
    <section class="panel" style="padding: 20px;">
      <div class="panel-head">
        <div>
          <h3 class="panel-title">班级管理</h3>
          <div class="soft-note">先创建班级，再导入学生名单。班级会自动生成邀请码和学生人数统计。</div>
        </div>
        <el-button type="primary" @click="openCreate">新增班级</el-button>
      </div>

      <div class="hero-grid" style="margin-bottom: 18px;">
        <div class="metric-card">
          <div class="metric-label">班级总数</div>
          <div class="metric-value">{{ classes.length }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">启用班级</div>
          <div class="metric-value">{{ classes.filter((item) => item.is_active).length }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">总学生数</div>
          <div class="metric-value">{{ classes.reduce((sum, item) => sum + (item.student_count || 0), 0) }}</div>
        </div>
      </div>

      <el-table :data="classes" border stripe>
        <el-table-column prop="name" label="班级名称" min-width="160" />
        <el-table-column prop="grade_display" label="年级" width="120" />
        <el-table-column prop="class_number" label="班号" width="90" />
        <el-table-column prop="student_count" label="学生数" width="100" />
        <el-table-column prop="classroom" label="教室" width="120" />
        <el-table-column prop="student_invite_code" label="邀请码" width="120" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="resetInvite(row)">重置码</el-button>
            <el-button link type="danger" @click="removeClass(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑班级' : '新增班级'" width="520px">
      <el-form :model="form" label-width="88px">
        <el-form-item label="班级名称"><el-input v-model="form.name" placeholder="可留空自动生成" /></el-form-item>
        <el-form-item label="年级">
          <el-select v-model="form.grade" style="width: 100%">
            <el-option v-for="grade in grades" :key="grade.value" :label="grade.label" :value="grade.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="班号"><el-input-number v-model="form.class_number" :min="1" :max="99" style="width: 100%" /></el-form-item>
        <el-form-item label="教室"><el-input v-model="form.classroom" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitClass">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue"
import { ElMessageBox } from "element-plus"
import { classAPI } from "@/api"
import request from "@/utils/request"

const classes = ref([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const grades = [
  { value: 1, label: "一年级" },
  { value: 2, label: "二年级" },
  { value: 3, label: "三年级" },
  { value: 4, label: "四年级" },
  { value: 5, label: "五年级" },
  { value: 6, label: "六年级" },
]

const form = reactive({
  name: "",
  grade: 1,
  class_number: 1,
  classroom: "",
  description: "",
  is_active: true,
})

function resetForm() {
  editingId.value = null
  Object.assign(form, {
    name: "",
    grade: 1,
    class_number: 1,
    classroom: "",
    description: "",
    is_active: true,
  })
}

async function loadClasses() {
  const data = await classAPI.list()
  classes.value = data.results || data
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    grade: row.grade,
    class_number: row.class_number,
    classroom: row.classroom,
    description: row.description,
    is_active: row.is_active,
  })
  dialogVisible.value = true
}

async function submitClass() {
  submitting.value = true
  try {
    if (editingId.value) {
      await classAPI.update(editingId.value, form)
    } else {
      await classAPI.create(form)
    }
    dialogVisible.value = false
    await loadClasses()
  } finally {
    submitting.value = false
  }
}

async function resetInvite(row) {
  await request.post(`/classes/${row.id}/reset_student_invite_code/`)
  await loadClasses()
}

async function removeClass(row) {
  await ElMessageBox.confirm(`确定删除班级 ${row.name} 吗？`, "提示", { type: "warning" })
  await classAPI.remove(row.id)
  await loadClasses()
}

onMounted(loadClasses)
</script>
