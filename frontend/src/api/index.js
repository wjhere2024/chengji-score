import request from "@/utils/request"

export const authAPI = {
  login: (data) => request.post("/auth/login/", data, { skipAuth: true }),
}

export const userAPI = {
  me: () => request.get("/users/me/"),
}

export const classAPI = {
  list: (params) => request.get("/classes/", { params }),
  my: () => request.get("/classes/my_classes/"),
  create: (data) => request.post("/classes/", data),
  update: (id, data) => request.put(`/classes/${id}/`, data),
  remove: (id) => request.delete(`/classes/${id}/`),
}

export const studentAPI = {
  list: (params) => request.get("/students/", { params }),
  create: (data) => request.post("/students/", data),
  update: (id, data) => request.put(`/students/${id}/`, data),
  remove: (id) => request.delete(`/students/${id}/`),
  importExcel: (formData) => request.post("/students/import_students/", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  exportExcel: () => request.get("/students/export_students/", { responseType: "blob" }),
  downloadTemplate: () => request.get("/students/download_template/", { responseType: "blob" }),
}

export const subjectAPI = {
  list: (params) => request.get("/subjects/", { params }),
}

export const examAPI = {
  list: (params) => request.get("/exams/", { params }),
  create: (data) => request.post("/exams/", data),
  update: (id, data) => request.put(`/exams/${id}/`, data),
  remove: (id) => request.delete(`/exams/${id}/`),
  publish: (id) => request.post(`/exams/${id}/publish/`),
  unpublish: (id) => request.post(`/exams/${id}/unpublish/`),
  gradeSubjects: (id, grade) => request.get(`/exams/${id}/grade_subjects/`, { params: { grade } }),
}

export const scoreAPI = {
  list: (params) => request.get("/scores/", { params }),
  create: (data) => request.post("/scores/", data),
  update: (id, data) => request.put(`/scores/${id}/`, data),
  remove: (id) => request.delete(`/scores/${id}/`),
  statistics: (params) => request.get("/scores/statistics/", { params }),
  downloadTemplate: (params) => request.get("/scores/download_template/", { params, responseType: "blob" }),
  importScores: (formData) => request.post("/scores/import_scores/", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  importWorkbook: (formData) => request.post("/scores/import_workbook/", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  parseTextScores: (data) => request.post("/scores/parse_text_scores/", data),
  importTextScores: (data) => request.post("/scores/import_text_scores/", data),
}
