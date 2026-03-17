import { defineStore } from "pinia"
import { authAPI, userAPI } from "@/api"

export const useUserStore = defineStore("user", {
  state: () => ({
    token: localStorage.getItem("access_token") || "",
    refreshToken: localStorage.getItem("refresh_token") || "",
    userInfo: null,
  }),
  getters: {
    isAdmin: (state) => ["admin", "super_admin"].includes(state.userInfo?.current_role || state.userInfo?.role),
    userName: (state) => state.userInfo?.real_name || state.userInfo?.username || "",
    schoolName: (state) => state.userInfo?.school_name || "成绩管理台",
  },
  actions: {
    async login(payload) {
      const data = await authAPI.login(payload)
      this.token = data.access
      this.refreshToken = data.refresh
      localStorage.setItem("access_token", data.access)
      localStorage.setItem("refresh_token", data.refresh)
      await this.fetchMe()
    },
    async fetchMe() {
      this.userInfo = await userAPI.me()
      return this.userInfo
    },
    logout() {
      this.token = ""
      this.refreshToken = ""
      this.userInfo = null
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
    },
  },
})
