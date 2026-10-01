// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { canNotify, permissionStatus, requestPermission } from './notifications'

const originalNotification = window.Notification

describe('notifications helpers', () => {
  afterEach(() => {
    if (originalNotification) {
      Object.defineProperty(window, 'Notification', { value: originalNotification, configurable: true })
    } else {
      Reflect.deleteProperty(window, 'Notification')
    }
  })

  it('reports unavailable when Notification is missing', async () => {
    Reflect.deleteProperty(window, 'Notification')
    expect(canNotify()).toBe(false)
    expect(permissionStatus()).toBe('unavailable')
    await expect(requestPermission()).resolves.toBe('unavailable')
  })

  it('reads and requests browser notification permission', async () => {
    const request = vi.fn().mockResolvedValue('granted')
    Object.defineProperty(window, 'Notification', {
      configurable: true,
      value: { permission: 'default', requestPermission: request },
    })

    expect(canNotify()).toBe(true)
    expect(permissionStatus()).toBe('default')
    await expect(requestPermission()).resolves.toBe('granted')
    expect(request).toHaveBeenCalledTimes(1)
  })
})
