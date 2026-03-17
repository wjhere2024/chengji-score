<template>
  <div class="page-grid">
    <section class="panel" style="padding: 20px;">
      <div class="panel-head">
        <div>
          <h3 class="panel-title">成绩录入</h3>
          <div class="soft-note">先选择考试、班级、科目，再逐个学生录入成绩。</div>
        </div>
        <div class="toolbar-filters">
          <el-button @click="downloadTemplate">下载模板</el-button>
          <el-button type="success" plain @click="importVisible = true">批量导入</el-button>
        </div>
      </div>

      <div class="toolbar" style="margin-bottom: 18px;">
        <div class="toolbar-filters">
          <el-select v-model="filters.examId" placeholder="考试" style="width: 220px" @change="onExamChange">
            <el-option v-for="item in exams" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-select v-model="filters.classId" placeholder="班级" style="width: 180px" @change="loadStudents">
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-select v-model="filters.subjectId" placeholder="科目" style="width: 180px" @change="loadStudents">
            <el-option v-for="item in subjects" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </div>
      </div>

      <div v-if="stats" class="stat-banner">
        共 {{ stats.total_count }} 条成绩，均分 {{ stats.average_score || 0 }}，及格率 {{ stats.pass_rate || 0 }}%，优秀率 {{ stats.excellent_rate || 0 }}%
      </div>

      <el-table :data="studentsWithScores" border stripe style="margin-top: 14px;">
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="class_name" label="班级" width="140" />
        <el-table-column label="成绩" width="180">
          <template #default="{ row }">
            <el-input-number v-model="row.score" :min="0" :max="150" :precision="1" style="width: 150px" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button type="primary" link @click="saveScore(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="importVisible" title="批量导入成绩" width="560px">
      <el-form label-width="90px">
        <el-form-item label="考试">
          <el-select v-model="filters.examId" style="width: 100%">
            <el-option v-for="item in exams" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="单科目">
          <el-select v-model="filters.subjectId" clearable style="width: 100%">
            <el-option v-for="item in subjects" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Excel 文件">
          <el-upload :auto-upload="false" :limit="1" accept=".xlsx,.xls,.csv" :on-change="handleImportFile">
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
import { computed, onMounted, reactive, ref } from "vue"
import { classAPI, examAPI, scoreAPI, studentAPI } from "@/api"
import { saveBlob } from "@/utils/file"

const exams = ref([])
const classes = ref([])
const subjects = ref([])
const students = ref([])
const scores = ref([])
const stats = ref(null)
const importVisible = ref(false)
const importing = ref(false)
const importFile = ref(null)

const filters = reactive({ examId: "", classId: "", subjectId: "" })

const studentsWithScores = computed(() => {
  return students.value.map((student) => {
    const current = scores.value.find((score) => score.student === student.id)
    return {
      ...student,
      scoreId: current?.id,
      score: current?.score ?? null,
    }
  })
})

async function loadBase() {
  const [examData, classData] = await Promise.all([examAPI.list(), classAPI.list()])
  exams.value = examData.results || examData
  classes.value = classData.results || classData
}

async function onExamChange() {
  filters.subjectId = ""
  if (!filters.examId) {
    subjects.value = []
    return
  }
  const grade = classes.value.find((item) => item.id === filters.classId)?.grade || ""
  subjects.value = await examAPI.gradeSubjects(filters.examId, grade)
  await loadStudents()
}

async function loadStudents() {
  if (!filters.classId) return
  const studentData = await studentAPI.list({ class_obj: filters.classId })
  students.value = studentData.results || studentData

  if (filters.examId && filters.subjectId) {
    const scoreData = await scoreAPI.list({ exam: filters.examId, subject: filters.subjectId, student__class_obj: filters.classId })
    scores.value = scoreData.results || scoreData
    stats.value = await scoreAPI.statistics({ exam_id: filters.examId, subject_id: filters.subjectId, class_id: filters.classId })
  } else {
    scores.value = []
    stats.value = null
  }
}

async function saveScore(row) {
  const payload = {
    student: row.id,
    exam: filters.examId,
    subject: filters.subjectId,
    score: row.score,
    notes: "",
  }
  if (row.scoreId) {
    await scoreAPI.update(row.scoreId, payload)
  } else {
    await scoreAPI.create(payload)
  }
  await loadStudents()
}

async function downloadTemplate() {
  const blob = await scoreAPI.downloadTemplate({ exam_id: filters.examId || "", type: filters.subjectId ? "single" : "multi" })
  saveBlob(blob, "score_import_template.xlsx")
}

function handleImportFile(file) {
  importFile.value = file.raw
}

async function submitImport() {
  if (!importFile.value || !filters.examId) return
  importing.value = true
  try {
    const formData = new FormData()
    formData.append("file", importFile.value)
    formData.append("exam_id", filters.examId)
    if (filters.subjectId) formData.append("subject_id", filters.subjectId)
    await scoreAPI.importScores(formData)
    importVisible.value = false
    importFile.value = null
    await loadStudents()
  } finally {
    importing.value = false
  }
}

onMounted(loadBase)
</script>
