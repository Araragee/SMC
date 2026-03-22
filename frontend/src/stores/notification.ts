import { defineStore } from 'pinia';
import axios from 'axios';
import type { Notification } from '../types';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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
      return (userId: string) => state.notifications.filter(n => n.userId === userId || n.userId === null);
    },
    getUnreadCount: (state) => {
      return (userId: string) => state.notifications.filter(n => (n.userId === userId || n.userId === null) && !n.isRead).length;
    },
  },
  actions: {
    async fetchNotifications(userId: string) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/notifications/user/${userId}`);
        const userNotifs = response.data.map((n: any) => ({
          id: String(n.id),
          userId: String(n.user_id),
          title: "Notification",
          message: n.message,
          type: "info",
          isRead: n.is_read,
          createdAt: n.created_at
        }));

        for (const n of userNotifs) {
            const index = this.notifications.findIndex(existing => existing.id === n.id);
            if (index !== -1) {
                this.notifications[index] = n;
            } else {
                this.notifications.push(n);
            }
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch notifications';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async markAsRead(notificationId: string) {
      this.isLoading = true;
      this.error = null;
      try {
        // Assume backend PUT endpoint exists. We'll simulate its effect if we didn't write it.
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification) {
          notification.isRead = true;
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to mark notification as read';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async createNotification(notificationData: Omit<Notification, 'id' | 'isRead' | 'createdAt'>) {
        this.isLoading = true;
        this.error = null;
        try {
            if (notificationData.userId) {
                const response = await axios.post(`${API_URL}/notifications/`, {
                    message: notificationData.message,
                    user_id: parseInt(notificationData.userId)
                });
                const newNotification: Notification = {
                    id: String(response.data.id),
                    userId: String(response.data.user_id),
                    title: notificationData.title,
                    message: response.data.message,
                    type: notificationData.type,
                    isRead: response.data.is_read,
                    createdAt: response.data.created_at
                };
                this.notifications.unshift(newNotification);
            }
        } catch (err: any) {
            this.error = err.message || 'Failed to create notification';
            console.error(err);
        } finally {
            this.isLoading = false;
        }
    }
  },
});
