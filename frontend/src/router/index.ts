import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import AuthLayout from '../layouts/AuthLayout.vue'
import AdminLayout from '../layouts/AdminLayout.vue'
import TeacherLayout from '../layouts/TeacherLayout.vue'
import StudentLayout from '../layouts/StudentLayout.vue'

import Login from '../views/Login.vue'
import AdminDashboard from '../views/admin/Dashboard.vue'
import TeacherDashboard from '../views/teacher/Dashboard.vue'
import StudentDashboard from '../views/student/Dashboard.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Login',
    component: Login,
    meta: { layout: AuthLayout }
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: AdminDashboard,
    meta: { layout: AdminLayout, requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/teacher',
    name: 'TeacherDashboard',
    component: TeacherDashboard,
    meta: { layout: TeacherLayout, requiresAuth: true, roles: ['teacher', 'admin'] }
  },
  {
    path: '/student',
    name: 'StudentDashboard',
    component: StudentDashboard,
    meta: { layout: StudentLayout, requiresAuth: true, roles: ['student', 'teacher', 'admin'] }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/')
  } else if (to.meta.requiresAuth && to.meta.roles) {
    const roles = to.meta.roles as string[]
    if (authStore.userRole && !roles.includes(authStore.userRole.toLowerCase())) {
        next(`/${authStore.userRole.toLowerCase()}`)
    } else {
        next()
    }
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    next(`/${authStore.userRole?.toLowerCase() || 'student'}`)
  } else {
    next()
  }
})

export default router
