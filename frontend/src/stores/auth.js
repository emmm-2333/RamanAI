import { defineStore } from "pinia";
import axios from "axios";

// 配置 Axios 默认 URL (指向 Django 后端)
const API_URL = "http://127.0.0.1:8000/api/v1/auth/";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    // 从 localStorage 初始化 token 和用户信息
    accessToken: localStorage.getItem("access_token") || null,
    refreshToken: localStorage.getItem("refresh_token") || null,
    user: JSON.parse(localStorage.getItem("user_info")) || null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },

  actions: {
    /**
     * 登录动作
     * @param {string} username
     * @param {string} password
     */
    async login(username, password) {
      try {
        const response = await axios.post(API_URL + "login/", {
          username,
          password,
        });

        const { access, refresh } = response.data;
        this.accessToken = access;
        this.refreshToken = refresh;

        // 保存到 LocalStorage
        localStorage.setItem("access_token", access);
        localStorage.setItem("refresh_token", refresh);

        // 获取用户信息
        await this.fetchUser();

        return true;
      } catch (error) {
        console.error("Login failed:", error);
        if (error.response && error.response.data) {
          throw error.response.data;
        }
        throw error;
      }
    },

    /**
     * 获取当前用户信息
     */
    async fetchUser() {
      if (!this.accessToken) return;

      try {
        const response = await axios.get(API_URL + "me/", {
          headers: { Authorization: `Bearer ${this.accessToken}` },
        });
        this.user = response.data;
        localStorage.setItem("user_info", JSON.stringify(this.user));
      } catch (error) {
        console.error("Fetch user failed:", error);
        // 如果 Token 失效 (401)，自动登出并跳转
        if (error.response && error.response.status === 401) {
          this.logout();
          window.location.href = '/login';
        }
      }
    },

    /**
     * 注册动作
     */
    async register(username, password, email) {
      try {
        await axios.post(API_URL + "register/", {
          username,
          password,
          email,
        });
        return true;
      } catch (error) {
        console.error("Registration failed:", error);
        if (error.response && error.response.data) {
          throw error.response.data;
        }
        throw error;
      }
    },

    /**
     * 登出
     */
    logout() {
      this.accessToken = null;
      this.refreshToken = null;
      this.user = null;
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user_info");
    },
  },
});
