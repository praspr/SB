export const NOTIFY_PROMPT_DISMISSED_KEY = 'sb-notify-prompt-dismissed'

export function canNotify(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window
}

export function permissionStatus(): NotificationPermission | 'unavailable' {
  if (!canNotify()) return 'unavailable'
  return window.Notification.permission
}

export async function requestPermission(): Promise<NotificationPermission | 'unavailable'> {
  if (!canNotify()) return 'unavailable'
  return window.Notification.requestPermission()
}
