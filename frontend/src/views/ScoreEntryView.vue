<template>
  <div class="page-grid">
    <section class="panel" style="padding: 20px;">
      <div class="panel-head">
        <div>
          <h3 class="panel-title">成绩录入</h3>
          <div class="soft-note">先选择考试、班级和科目，再逐个录入、导入 Excel，或直接粘贴语音转写文本。</div>
        </div>
        <div class="toolbar-filters">
          <el-button @click="downloadTemplate">下载模板</el-button>
          <el-button type="success" plain @click="importVisible = true">Excel 导入</el-button>
          <el-button type="warning" plain @click="openTextImport">文本批量录入</el-button>
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

    <el-dialog v-model="importVisible" title="Excel 导入成绩" width="560px">
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

    <el-dialog v-model="textImportVisible" title="文本批量录入" width="780px">
      <el-form label-width="90px">
        <el-form-item label="录入说明">
          <div class="soft-note">
            每行一条，推荐格式：`贾宝玉 95`、`jb y 95` 不建议；拼音匹配支持完整拼音或首字母，如 `jiabaoyu 95`、`jby 95`。
          </div>
        </el-form-item>
        <el-form-item label="批量文本">
          <el-input
            v-model="textImportForm.text"
            type="textarea"
            :rows="10"
            placeholder="示例：&#10;贾宝玉 95&#10;林黛玉 98&#10;薛宝钗 九十二"
          />
        </el-form-item>
      </el-form>

      <div v-if="textParseErrors.length" class="text-import-errors">
        <div class="soft-note" style="margin-bottom: 8px;">以下内容未成功匹配：</div>
        <div v-for="item in textParseErrors" :key="item" class="error-line">{{ item }}</div>
      </div>

      <el-table v-if="textParseRecords.length" :data="textParseRecords" border stripe style="margin-top: 14px;">
        <el-table-column prop="line_no" label="#" width="60" />
        <el-table-column prop="raw_line" label="原始文本" min-width="180" />
        <el-table-column prop="student_name" label="匹配学生" width="120" />
        <el-table-column prop="class_name" label="班级" width="120" />
        <el-table-column label="成绩" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.score" :min="0" :max="150" :precision="1" style="width: 100px" />
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <el-button @click="textImportVisible = false">关闭</el-button>
        <el-button type="primary" plain :loading="parsingText" @click="parseTextImport">解析文本</el-button>
        <el-button type="success" :disabled="!textParseRecords.length" :loading="submittingText" @click="submitTextImport">
          导入解析结果
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue"
import { ElMessage } from "element-plus"
import { classAPI, examAPI, scoreAPI, studentAPI } from "@/api"
import { saveBlob } from "@/utils/file"

const exams = ref([])
const classes = ref([])
const subjects = ref([])
const students = ref([])
const scores = ref([])
const stats = ref(null)
const importVisible = ref(false)
const textImportVisible = ref(false)
const importing = ref(false)
const parsingText = ref(false)
const submittingText = ref(false)
const importFile = ref(null)
const textParseRecords = ref([])
const textParseErrors = ref([])

const filters = reactive({ examId: "", classId: "", subjectId: "" })
const textImportForm = reactive({ text: "" })

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

function openTextImport() {
  if (!filters.examId || !filters.subjectId || !filters.classId) {
    ElMessage.warning("请先选择考试、班级和科目")
    return
  }
  textImportVisible.value = true
}

async function parseTextImport() {
  if (!textImportForm.text.trim()) {
    ElMessage.warning("请先输入批量文本")
    return
  }
  parsingText.value = true
  try {
    const result = await scoreAPI.parseTextScores({
      text: textImportForm.text,
      exam_id: filters.examId,
      subject_id: filters.subjectId,
      class_id: filters.classId,
    })
    textParseRecords.value = (result.records || []).map((item) => ({
      ...item,
      score: Number(item.score),
    }))
    textParseErrors.value = result.errors || []
    if (!textParseRecords.value.length) {
      ElMessage.warning("没有解析出可导入的成绩")
    }
  } finally {
    parsingText.value = false
  }
}

async function submitTextImport() {
  if (!textParseRecords.value.length) return
  submittingText.value = true
  try {
    const result = await scoreAPI.importTextScores({
      exam_id: filters.examId,
      subject_id: filters.subjectId,
      records: textParseRecords.value.map((item) => ({
        student_id: item.student_id,
        score: item.score,
        notes: "文本批量导入",
      })),
    })
    if (result.errors?.length) {
      textParseErrors.value = result.errors
    } else {
      textParseErrors.value = []
    }
    ElMessage.success(`已导入 ${result.success_count || 0} 条成绩`)
    await loadStudents()
  } finally {
    submittingText.value = false
  }
}

onMounted(loadBase)
</script>

<style scoped>
.text-import-errors {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(191, 64, 64, 0.08);
}

.error-line {
  color: #8d2a2a;
  font-size: 13px;
  line-height: 1.6;
}
</style>
