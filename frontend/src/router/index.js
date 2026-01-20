import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import TransactionsView from '../views/TransactionsView.vue'
import AssetsView from '../views/AssetsView.vue'
import SettingsView from '../views/SettingsView.vue'

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
      path: '/assets',
      name: 'assets',
      component: AssetsView
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView
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
