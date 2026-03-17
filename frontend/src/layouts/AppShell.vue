<template>
  <div class="shell">
    <aside class="shell-aside">
      <div class="brand-block">
        <p class="brand-kicker">Score System</p>
        <h1 class="brand-title">成绩管理台</h1>
        <p class="brand-desc">保留教师登录、学生导入、考试管理、成绩录入与成绩查询。</p>
      </div>

      <nav class="menu-list">
        <RouterLink class="menu-item" to="/classes"><el-icon><School /></el-icon><span>班级管理</span></RouterLink>
        <RouterLink class="menu-item" to="/students"><el-icon><UserFilled /></el-icon><span>学生管理</span></RouterLink>
        <RouterLink class="menu-item" to="/exams"><el-icon><Tickets /></el-icon><span>考试管理</span></RouterLink>
        <RouterLink class="menu-item" to="/score-entry"><el-icon><EditPen /></el-icon><span>成绩录入</span></RouterLink>
        <RouterLink class="menu-item" to="/scores"><el-icon><Histogram /></el-icon><span>成绩管理</span></RouterLink>
      </nav>
    </aside>

    <main class="shell-main">
      <header class="topbar">
        <div class="topbar-card" style="flex: 1;">
          <h2 class="topbar-title">{{ route.meta.title || "成绩管理台" }}</h2>
          <p class="topbar-meta">{{ userStore.schoolName }} / {{ userStore.userName }}</p>
        </div>
        <div class="topbar-card">
          <el-button type="danger" plain @click="handleLogout">退出登录</el-button>
        </div>
      </header>

      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter, useRoute } from "vue-router"
import { useUserStore } from "@/stores/user"

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

function handleLogout() {
  userStore.logout()
  router.push("/login")
}
</script>
