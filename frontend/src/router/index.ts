import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@stores/auth'
import Login from '@views/Login.vue'
import NotFoundView from '@components/NotFoundView.vue'

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
const AdminRoster = () => import('@views/admin/Roster.vue')
const AdminTeachers = () => import('@views/admin/Teachers.vue')
import { SHOP_ENABLED } from '@typescript/constants'

const AdminInstruments = () => import('@views/admin/Instruments.vue')
const AdminPayments = () => import('@views/admin/Payments.vue')
const AdminActivityLog = () => import('@views/admin/ActivityLog.vue')

// Teacher Views
const TeacherStudents = () => import('@views/teacher/Students.vue')
const TeacherInstruments = () => import('@views/teacher/Instruments.vue')
const TeacherPayments = () => import('@views/teacher/Payments.vue')
const TeacherShop = () => import('@views/teacher/Shop.vue')

// Schedule views
const AdminSchedule = () => import('@views/admin/Schedule.vue')
const TeacherSchedule = () => import('@views/teacher/Schedule.vue')

// Student Views
const StudentShop = () => import('@views/student/Shop.vue')

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
          meta: { requiresAuth: false },
        },
      ],
    },
    {
      // Phase 2 password-reset flow: both pages re-use AuthLayout so they
      // share the marketing/background chrome but skip the auth gate.
      path: '/forgot-password',
      component: () => import('@layouts/AuthLayout.vue'),
      children: [
        {
          path: '',
          name: 'forgot-password',
          component: () => import('@views/ForgotPassword.vue'),
          meta: { requiresAuth: false },
        },
      ],
    },
    {
      path: '/reset-password',
      component: () => import('@layouts/AuthLayout.vue'),
      children: [
        {
          path: '',
          name: 'reset-password',
          component: () => import('@views/ResetPassword.vue'),
          meta: { requiresAuth: false },
        },
      ],
    },
    {
      path: '/change-password',
      component: () => import('@layouts/AuthLayout.vue'),
      children: [
        {
          path: '',
          name: 'change-password',
          component: () => import('@views/ChangePassword.vue'),
          meta: { requiresAuth: true },
        },
      ],
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
        { path: 'roster', name: 'admin-roster', component: AdminRoster },
        { path: 'teachers', name: 'admin-teachers', component: AdminTeachers },
        {
          path: 'instruments',
          name: 'admin-instruments',
          component: AdminInstruments,
          meta: { shop: true },
        },
        { path: 'payments', name: 'admin-payments', component: AdminPayments },
        { path: 'activity-log', name: 'admin-activity-log', component: AdminActivityLog },
        {
          path: 'students/:id/records',
          name: 'admin-student-records',
          component: AdminStudentRecords,
        },
        { path: ':module', component: NotFoundView },
      ],
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
        { path: 'shop', name: 'teacher-shop', component: TeacherShop, meta: { shop: true } },
        { path: ':module', component: NotFoundView },
      ],
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
        { path: 'shop', name: 'student-shop', component: StudentShop, meta: { shop: true } },
        { path: ':module', component: NotFoundView },
      ],
    },
    // General redirection
    {
      path: '/',
      redirect: () => {
        const auth = useAuthStore()
        if (!auth.isAuthenticated) return '/login'
        return `/${auth.userRole}`
      },
    },
    {
      path: '/:pathMatch(.*)*',
      component: NotFoundView,
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  // Phase 2: if the user has the must_change_password flag set, they
  // cannot navigate anywhere except /change-password (or out via the
  // public auth flows). This catches the default-admin first-login and
  // any admin-initiated forced reset.
  if (
    auth.isAuthenticated &&
    auth.user?.mustChangePassword &&
    to.path !== '/change-password' &&
    to.path !== '/login' &&
    to.path !== '/forgot-password' &&
    to.path !== '/reset-password'
  ) {
    return next('/change-password')
  }

  // The store is closed (SHOP_ENABLED). Hiding the nav entry does not stop
  // anyone typing the URL, so turn the routes away too.
  if (!SHOP_ENABLED && to.meta.shop) {
    return next(auth.userRole ? `/${auth.userRole}` : '/login')
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
  } else if (
    to.meta.roles &&
    auth.userRole &&
    !(to.meta.roles as string[]).includes(auth.userRole)
  ) {
    next(`/${auth.userRole}`)
  } else if (to.path === '/login' && auth.isAuthenticated) {
    next(`/${auth.userRole}`)
  } else {
    next()
  }
})

export default router
