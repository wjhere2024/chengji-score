<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-mark">Teacher Access</div>
      <h1 class="login-title">成绩管理</h1>
      <p class="login-subtitle">独立版教师入口。登录后可导入学生名单、创建考试并录入成绩。</p>

      <el-form :model="form" @submit.prevent="handleSubmit">
        <el-form-item>
          <el-input v-model="form.username" size="large" placeholder="用户名" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" size="large" type="password" show-password placeholder="密码" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="handleSubmit">
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue"
import { useRouter } from "vue-router"
import { useUserStore } from "@/stores/user"

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ username: "", password: "" })

async function handleSubmit() {
  loading.value = true
  try {
    await userStore.login(form)
    router.push("/students")
  } finally {
    loading.value = false
  }
}
</script>
