/**
 * Notifications API Client
 * Part 12 — In-App Notifications for BidVerify AI
 */

import { api } from "@/lib/api";
import {
  NotificationFilterParams,
  NotificationItem,
  NotificationListResponse,
  NotificationMarkReadResponse,
  UnreadCountResponse,
} from "@/types/notification";

export const notificationApi = {
  /**
   * Retrieves paginated list of notifications with optional filters.
   */
  async getNotifications(
    params?: NotificationFilterParams,
    token?: string
  ): Promise<NotificationListResponse> {
    return api.get<NotificationListResponse>("/api/v1/notifications", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Fast unread count query for navbar badge polling.
   */
  async getUnreadCount(token?: string): Promise<UnreadCountResponse> {
    return api.get<UnreadCountResponse>("/api/v1/notifications/unread-count", {
      token,
    });
  },

  /**
   * Marks a specific notification as read.
   */
  async markAsRead(notificationId: string, token?: string): Promise<NotificationItem> {
    return api.post<NotificationItem>(`/api/v1/notifications/${notificationId}/read`, {}, {
      token,
    });
  },

  /**
   * Marks a specific notification as unread.
   */
  async markAsUnread(notificationId: string, token?: string): Promise<NotificationItem> {
    return api.post<NotificationItem>(`/api/v1/notifications/${notificationId}/unread`, {}, {
      token,
    });
  },

  /**
   * Marks all unread notifications as read.
   */
  async markAllAsRead(token?: string): Promise<NotificationMarkReadResponse> {
    return api.post<NotificationMarkReadResponse>("/api/v1/notifications/mark-all-read", {}, {
      token,
    });
  },
};
