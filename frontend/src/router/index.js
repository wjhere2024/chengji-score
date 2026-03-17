import { createRouter, createWebHistory } from "vue-router"
import { useUserStore } from "@/stores/user"

const routes = [
  { path: "/login", name: "login", component: () => import("@/views/LoginView.vue"), meta: { public: true } },
  {
    path: "/",
    component: () => import("@/layouts/AppShell.vue"),
    children: [
      { path: "", redirect: "/students" },
      { path: "/classes", name: "classes", component: () => import("@/views/ClassesView.vue"), meta: { title: "班级管理" } },
      { path: "/students", name: "students", component: () => import("@/views/StudentsView.vue"), meta: { title: "学生管理" } },
      { path: "/exams", name: "exams", component: () => import("@/views/ExamsView.vue"), meta: { title: "考试管理" } },
      { path: "/score-entry", name: "score-entry", component: () => import("@/views/ScoreEntryView.vue"), meta: { title: "成绩录入" } },
      { path: "/scores", name: "scores", component: () => import("@/views/ScoresView.vue"), meta: { title: "成绩管理" } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  if (to.meta.public) {
    return true
  }

  if (!userStore.token) {
    return "/login"
  }

  if (!userStore.userInfo) {
    try {
      await userStore.fetchMe()
    } catch {
      return "/login"
    }
  }

  return true
})

export default router
