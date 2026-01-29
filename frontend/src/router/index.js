import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import Login from "../views/Login.vue";
import Register from "../views/Register.vue";
import Dashboard from "../views/Dashboard.vue";
import MainLayout from "../layouts/MainLayout.vue";

// Lazy load new views
const RecordList = () => import("../views/record/RecordList.vue");
const RecordDetail = () => import("../views/record/RecordDetail.vue");
const ModelList = () => import("../views/model/ModelList.vue");
const AnalysisPCA = () => import("../views/analysis/AnalysisPCA.vue");

const routes = [
  {
    path: "/login",
    name: "Login",
    component: Login,
  },
  {
    path: "/register",
    name: "Register",
    component: Register,
  },
  {
    path: "/",
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        redirect: "/dashboard",
      },
      {
        path: "dashboard",
        name: "Dashboard",
        component: Dashboard,
      },
      {
        path: "records",
        name: "RecordList",
        component: RecordList,
      },
      {
        path: "records/:id",
        name: "RecordDetail",
        component: RecordDetail,
      },
      {
        path: "models",
        name: "ModelList",
        component: ModelList,
      },
      {
        path: "analysis",
        name: "AnalysisPCA",
        component: AnalysisPCA,
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();

  // 如果目标路由需要认证且用户未登录
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next("/login");
  } else {
    next();
  }
});

export default router;
