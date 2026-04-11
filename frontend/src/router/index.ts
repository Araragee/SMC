import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@stores/auth'
import Login from '@views/Login.vue'
import PlaceholderView from '@components/PlaceholderView.vue'

// Role-based layouts
const AdminLayout = () => import('@layouts/AdminLayout.vue')
const StudentLayout = () => import('@layouts/StudentLayout.vue')
const TeacherLayout = () => import('@layouts/TeacherLayout.vue')

// Dashboards
const AdminDashboard = () => import('@views/admin/Dashboard.vue')
const StudentDashboard = () => import('@views/student/Dashboard.vue')
const StudentSchedule = () => import('@views/student/Schedule.vue')
const StudentHomework = () => import('@views/student/Homework.vue')
const StudentPayments = () => import('@views/student/Payments.vue')
const TeacherDashboard = () => import('@views/teacher/Dashboard.vue')

// Admin Views
const AdminUsers = () => import('@views/admin/Users.vue')
const AdminStudentRecords = () => import('@views/admin/StudentRecords.vue')
const AdminStudents = () => import('@views/admin/Students.vue')
const AdminTeachers = () => import('@views/admin/Teachers.vue')

// Teacher Views
const TeacherStudents = () => import('@views/teacher/Students.vue')
const TeacherInstruments = () => import('@views/teacher/Instruments.vue')
const TeacherPayments = () => import('@views/teacher/Payments.vue')

// Schedule views
const AdminSchedule = () => import('@views/admin/Schedule.vue')
const TeacherSchedule = () => import('@views/teacher/Schedule.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: () => import('@layouts/AuthLayout.vue'),
      children: [
        {
          path: '',
          name: 'login',
          component: Login,
          meta: { requiresAuth: false }
        }
      ]
    },
    // Admin Routes
    {
      path: '/admin',
      component: AdminLayout,
      meta: { requiresAuth: true, roles: ['admin'] },
      children: [
        { path: '', name: 'admin-dashboard', component: AdminDashboard },
        { path: 'schedule', name: 'admin-schedule', component: AdminSchedule },
        { path: 'users', name: 'admin-users', component: AdminUsers },
        { path: 'students', name: 'admin-students', component: AdminStudents },
        { path: 'teachers', name: 'admin-teachers', component: AdminTeachers },
        { path: 'students/:id/records', name: 'admin-student-records', component: AdminStudentRecords },
        { path: ':module', component: PlaceholderView }
      ]
    },
    // Teacher Routes
    {
      path: '/teacher',
      component: TeacherLayout,
      meta: { requiresAuth: true, roles: ['teacher'] },
      children: [
        { path: '', name: 'teacher-dashboard', component: TeacherDashboard },
        { path: 'schedule', name: 'teacher-schedule', component: TeacherSchedule },
        { path: 'students', name: 'teacher-students', component: TeacherStudents },
        { path: 'instruments', name: 'teacher-instruments', component: TeacherInstruments },
        { path: 'payments', name: 'teacher-payments', component: TeacherPayments },
        { path: ':module', component: PlaceholderView }
      ]
    },
    // Student Routes
    {
      path: '/student',
      component: StudentLayout,
      meta: { requiresAuth: true, roles: ['student'] },
      children: [
        { path: '', name: 'student-dashboard', component: StudentDashboard },
        { path: 'schedule', name: 'student-schedule', component: StudentSchedule },
        { path: 'homework', name: 'student-homework', component: StudentHomework },
        { path: 'payments', name: 'student-payments', component: StudentPayments },
        { path: ':module', component: PlaceholderView }
      ]
    },
    // General redirection
    {
      path: '/',
      redirect: () => {
        const auth = useAuthStore()
        if (!auth.isAuthenticated) return '/login'
        return `/${auth.userRole}`
      }
    }
  ]
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
  } else if (to.meta.roles && auth.userRole && !(to.meta.roles as string[]).includes(auth.userRole)) {
    next(`/${auth.userRole}`)
  } else if (to.path === '/login' && auth.isAuthenticated) {
    next(`/${auth.userRole}`)
  } else {
    next()
  }
})

export default router
