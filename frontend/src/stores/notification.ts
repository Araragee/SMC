import { defineStore } from 'pinia';
import { Notification } from '../types';
import { mockNotifications } from '../mock';

interface NotificationState {
  notifications: Notification[];
  isLoading: boolean;
  error: string | null;
}

export const useNotificationStore = defineStore('notification', {
  state: (): NotificationState => ({
    notifications: [...mockNotifications],
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
    async fetchNotifications() {
      this.isLoading = true;
      try {
        await new Promise(resolve => setTimeout(resolve, 500));
        this.notifications = [...mockNotifications];
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch notifications';
      } finally {
        this.isLoading = false;
      }
    },

    async markAsRead(notificationId: string) {
      this.isLoading = true;
      try {
        await new Promise(resolve => setTimeout(resolve, 200));
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification) {
          notification.isRead = true;
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to mark notification as read';
      } finally {
        this.isLoading = false;
      }
    },

    async createNotification(notificationData: Omit<Notification, 'id' | 'isRead' | 'createdAt'>) {
        this.isLoading = true;
        try {
            await new Promise(resolve => setTimeout(resolve, 300));
            const newNotification: Notification = {
                ...notificationData,
                id: `notification-${Date.now()}`,
                isRead: false,
                createdAt: new Date().toISOString()
            };
            this.notifications.unshift(newNotification);
        } catch (err: any) {
            this.error = err.message || 'Failed to create notification';
        } finally {
            this.isLoading = false;
        }
    }
  },
});
