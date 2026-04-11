import { defineStore } from 'pinia';
import axios from 'axios';
import { useAuthStore } from '@stores/auth';
import type { Notification } from '@types';

import { API_URL } from '@typescript/constants'

const authHeaders = function() {
  const auth = useAuthStore();
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {};
}

interface NotificationState {
  notifications: Notification[];
  isLoading: boolean;
  error: string | null;
}

export const useNotificationStore = defineStore('notification', {
  state: (): NotificationState => ({
    notifications: [],
    isLoading: false,
    error: null,
  }),
  getters: {
    getNotificationsByUserId: (state) => {
      return (userId: number) => state.notifications.filter(n => n.userId === userId || n.userId === null);
    },
    unreadNotifications: (state): Notification[] =>
      state.notifications.filter(n => !n.isRead),
    unreadCount: (state): number =>
      state.notifications.filter(n => !n.isRead).length,
    getUnreadCount: (state) => {
      return (userId: number) => state.notifications.filter(n => (n.userId === userId || n.userId === null) && !n.isRead).length;
    },
  },
  actions: {
    async fetchNotifications(userId: number) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/notifications/user/${userId}`, { headers: authHeaders() });
        const userNotifs: Notification[] = response.data.map((n: any) => ({
          id: Number(n.id),
          userId: Number(n.user_id),
          title: 'Notification',
          message: n.message,
          link: n.link,
          type: 'info' as const,
          isRead: n.is_read,
          createdAt: n.created_at,
        }));
        // Replace all notifications for this user
        this.notifications = userNotifs;
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch notifications';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async markAsRead(notificationId: number) {
      try {
        await axios.patch(`${API_URL}/notifications/${notificationId}/read`, {}, { headers: authHeaders() });
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification) notification.isRead = true;
      } catch (err: any) {
        console.error('Failed to mark notification as read:', err);
      }
    },

    async markAllAsRead(userId: number) {
      try {
        await axios.patch(`${API_URL}/notifications/user/${userId}/read-all`, {}, { headers: authHeaders() });
        this.notifications.forEach(n => { n.isRead = true; });
      } catch (err: any) {
        console.error('Failed to mark all as read:', err);
      }
    },

    async createNotification(notificationData: Omit<Notification, 'id' | 'isRead' | 'createdAt'>) {
      this.isLoading = true;
      this.error = null;
      try {
        if (notificationData.userId) {
          const response = await axios.post(`${API_URL}/notifications/`, {
            message: notificationData.message,
            user_id: Number(notificationData.userId),
            link: notificationData.link,
          });
          const newNotification: Notification = {
            id: Number(response.data.id),
            userId: Number(response.data.user_id),
            title: notificationData.title,
            message: response.data.message,
            link: response.data.link,
            type: notificationData.type,
            isRead: response.data.is_read,
            createdAt: response.data.created_at,
          };
          this.notifications.unshift(newNotification);
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to create notification';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },
  },
});
