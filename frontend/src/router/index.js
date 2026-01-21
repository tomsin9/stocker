import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import TransactionsView from '../views/TransactionsView.vue'
import SettingsView from '../views/SettingsView.vue'
import MonthlyTrackingView from '../views/MonthlyTrackingView.vue'
import ErrorView from '../views/ErrorView.vue'
import NotFoundView from '../views/NotFoundView.vue'
import ServerErrorView from '../views/ServerErrorView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: TransactionsView
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView
    },
    {
      path: '/monthly-tracking',
      name: 'monthly-tracking',
      component: MonthlyTrackingView
    },
    {
      path: '/error/:code?',
      name: 'error',
      component: ErrorView,
      props: true
    },
    {
      path: '/404',
      name: 'not-found',
      component: NotFoundView
    },
    {
      path: '/500',
      name: 'server-error',
      component: ServerErrorView
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'catch-all',
      component: NotFoundView
    }
  ]
});

// 路由守衛：沒 Token 且不在登入頁，就踢去登入
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token');
  if (to.path !== '/login' && !token) {
    next({ name: 'login' });
  } else {
    next();
  }
});

export default router;
