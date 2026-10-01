import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { SettingsPopover } from '@/components/layout/SettingsPopover'

vi.mock('@/components/ui/popover', () => ({
  Popover: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  PopoverTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  PopoverContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TabsList: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TabsTrigger: ({ children, value, className }: { children: React.ReactNode; value?: string; className?: string }) => <button type="button" data-value={value} className={className}>{children}</button>,
  TabsContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/lib/ledger', () => ({
  ledgerProjects: () => Promise.resolve([]),
  ledgerRegisterProject: () => Promise.resolve({}),
  ledgerSessions: () => Promise.resolve([]),
}))

vi.mock('@/lib/schedules', () => ({
  addScheduledRitual: () => Promise.resolve({}),
  deleteScheduledRitual: () => Promise.resolve({}),
  listScheduledRituals: () => Promise.resolve([]),
}))

vi.mock('@/lib/settings-checks', () => ({
  SETTING_CHECKS: [{ id: 'webex', label: 'Webex', fn: () => Promise.resolve({ name: 'webex', label: 'Webex', status: 'ok' }) }],
}))

vi.mock('@/lib/status', () => ({
  fetchCoreStatus: () => Promise.resolve({ version: '1.0.0', database: { ready: true, schema_version: 1 }, counts: { tools: 1, prompts: 2, resources: 3 } }),
}))

vi.mock('@/lib/store', () => ({
  useUiStore: (selector: (state: any) => unknown) => selector({
    settingsOpen: true,
    setSettingsOpen: () => undefined,
    settingsTab: 'connections',
    setSettingsTab: () => undefined,
  }),
}))

describe('settings popover', () => {
  it('renders the new top-level tab order with More collapsed by default', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <SettingsPopover>
          <button type="button">Open</button>
        </SettingsPopover>
      </QueryClientProvider>,
    )

    expect(html.indexOf('Connections')).toBeLessThan(html.indexOf('Schedules'))
    expect(html.indexOf('Schedules')).toBeLessThan(html.indexOf('Projects'))
    expect(html).toContain('More')
    expect(html).not.toContain('Sessions</button>')
    expect(html).not.toContain('Diagnostics</button>')
  })

  it('renders Sessions and Diagnostics when More starts expanded', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <SettingsPopover defaultMoreOpen>
          <button type="button">Open</button>
        </SettingsPopover>
      </QueryClientProvider>,
    )

    expect(html).toContain('Sessions</button>')
    expect(html).toContain('Diagnostics</button>')
  })
})
