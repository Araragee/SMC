import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

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
    meta: { layout: AdminLayout }
  },
  {
    path: '/teacher',
    name: 'TeacherDashboard',
    component: TeacherDashboard,
    meta: { layout: TeacherLayout }
  },
  {
    path: '/student',
    name: 'StudentDashboard',
    component: StudentDashboard,
    meta: { layout: StudentLayout }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
