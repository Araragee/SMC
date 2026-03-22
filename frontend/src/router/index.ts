import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'

// AuthLayout is small — eagerly load it. Everything else is lazy-loaded for code splitting.
import AuthLayout from '../layouts/AuthLayout.vue'
import AdminLayout from '../layouts/AdminLayout.vue'
import TeacherLayout from '../layouts/TeacherLayout.vue'
import StudentLayout from '../layouts/StudentLayout.vue'

// Views are lazy-loaded so Vite can code-split each dashboard into its own chunk.
// NOTE: Layouts must NOT be lazy-loaded — Vue's <component :is="layout"> cannot
// resolve a raw Promise. Only use () => import() for route view components.

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { layout: AuthLayout },
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('../views/admin/Dashboard.vue'),
    meta: { layout: AdminLayout, requiresAuth: true, roles: ['admin'], transition: 'slide-up' },
  },
  {
    path: '/teacher',
    name: 'TeacherDashboard',
    component: () => import('../views/teacher/Dashboard.vue'),
    meta: { layout: TeacherLayout, requiresAuth: true, roles: ['teacher', 'admin'], transition: 'slide-up' },
  },
  {
    path: '/student',
    name: 'StudentDashboard',
    component: () => import('../views/student/Dashboard.vue'),
    meta: { layout: StudentLayout, requiresAuth: true, roles: ['student', 'teacher', 'admin'], transition: 'slide-up' },
  },
  // Catch-all fallback
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/')
  } else if (to.meta.requiresAuth && to.meta.roles) {
    const roles = to.meta.roles as string[]
    if (authStore.userRole && !roles.includes(authStore.userRole.toLowerCase())) {
      useToastStore().warning('Access denied', 'You do not have permission to view that page.')
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
