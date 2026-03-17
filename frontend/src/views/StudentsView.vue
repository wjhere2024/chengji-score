<template>
  <div class="page-grid">
    <section class="panel" style="padding: 20px;">
      <div class="panel-head">
        <div>
          <h3 class="panel-title">学生管理</h3>
          <div class="soft-note">支持班级筛选、Excel 导入、模板下载与名单导出。</div>
        </div>
        <div class="toolbar">
          <div class="toolbar-filters">
            <el-select v-model="filters.class_obj" clearable placeholder="选择班级" style="width: 180px">
              <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
            <el-input v-model="filters.search" clearable placeholder="姓名 / 学号" style="width: 220px" />
            <el-button type="primary" @click="loadStudents">查询</el-button>
          </div>
          <div class="toolbar-filters">
            <el-button @click="downloadTemplate">下载模板</el-button>
            <el-button @click="exportStudents">导出名单</el-button>
            <el-button type="success" plain @click="importVisible = true">Excel 导入</el-button>
            <el-button type="primary" @click="openCreate">新增学生</el-button>
          </div>
        </div>
      </div>

      <el-table :data="students" border stripe>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="gender_display" label="性别" width="90" />
        <el-table-column prop="class_name" label="班级" width="140" />
        <el-table-column prop="parent_name" label="家长" width="120" />
        <el-table-column prop="phone" label="联系电话" width="140" />
        <el-table-column prop="admission_year" label="入学年份" width="110" />
        <el-table-column prop="notes" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="removeStudent(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑学生' : '新增学生'" width="560px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="学号"><el-input v-model="form.student_id" placeholder="可留空自动生成" /></el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.gender">
            <el-radio value="male">男</el-radio>
            <el-radio value="female">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="form.class_obj" style="width: 100%">
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="入学年份"><el-input-number v-model="form.admission_year" :min="2000" :max="2100" style="width: 100%" /></el-form-item>
        <el-form-item label="家长"><el-input v-model="form.parent_name" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitStudent">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="导入学生名单" width="520px">
      <el-form label-width="92px">
        <el-form-item label="默认班级">
          <el-select v-model="importForm.class_id" clearable style="width: 100%">
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Excel 文件">
          <el-upload :auto-upload="false" :limit="1" :on-change="handleImportFile" :show-file-list="true" accept=".xlsx,.xls,.csv">
            <el-button type="primary" plain>选择文件</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue"
import { ElMessageBox } from "element-plus"
import { classAPI, studentAPI } from "@/api"
import { saveBlob } from "@/utils/file"

const classes = ref([])
const students = ref([])
const dialogVisible = ref(false)
const importVisible = ref(false)
const importing = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const importFile = ref(null)

const filters = reactive({ class_obj: "", search: "" })
const form = reactive({ student_id: "", name: "", gender: "male", class_obj: "", admission_year: new Date().getFullYear(), parent_name: "", phone: "", notes: "", is_active: true })
const importForm = reactive({ class_id: "" })

function resetForm() {
  editingId.value = null
  Object.assign(form, { student_id: "", name: "", gender: "male", class_obj: classes.value[0]?.id || "", admission_year: new Date().getFullYear(), parent_name: "", phone: "", notes: "", is_active: true })
}

async function loadClasses() {
  const data = await classAPI.list()
  classes.value = data.results || data
  if (!form.class_obj && classes.value.length) form.class_obj = classes.value[0].id
}

async function loadStudents() {
  const data = await studentAPI.list(filters)
  students.value = data.results || data
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, { ...row })
  dialogVisible.value = true
}

async function submitStudent() {
  submitting.value = true
  try {
    if (editingId.value) {
      await studentAPI.update(editingId.value, form)
    } else {
      await studentAPI.create(form)
    }
    dialogVisible.value = false
    await loadStudents()
  } finally {
    submitting.value = false
  }
}

async function removeStudent(row) {
  await ElMessageBox.confirm(`确定删除 ${row.name} 吗？`, "提示", { type: "warning" })
  await studentAPI.remove(row.id)
  await loadStudents()
}

function handleImportFile(file) {
  importFile.value = file.raw
}

async function submitImport() {
  if (!importFile.value) return
  importing.value = true
  try {
    const formData = new FormData()
    formData.append("file", importFile.value)
    if (importForm.class_id) formData.append("class_id", importForm.class_id)
    await studentAPI.importExcel(formData)
    importVisible.value = false
    importFile.value = null
    await loadStudents()
  } finally {
    importing.value = false
  }
}

async function downloadTemplate() {
  const blob = await studentAPI.downloadTemplate()
  saveBlob(blob, "student_import_template.xlsx")
}

async function exportStudents() {
  const blob = await studentAPI.exportExcel()
  saveBlob(blob, "students.xlsx")
}

onMounted(async () => {
  await loadClasses()
  await loadStudents()
})
</script>
