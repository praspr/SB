import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { ReportViewer } from '@/components/reports/ReportViewer'

vi.mock('@/lib/webex-post', () => ({
  listWebexSpaces: () => Promise.resolve([]),
  webexPostMessage: () => Promise.resolve({ posted: true, space_id: 's1', message_type: 'text' }),
}))

function renderViewer(props: Partial<React.ComponentProps<typeof ReportViewer>> = {}) {
  const client = new QueryClient()
  return renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <ReportViewer
        report={{ markdown: '# Daily report\n\n- did a thing [ledger:1]', citations: [1] }}
        entries={[]}
        {...props}
      />
    </QueryClientProvider>
  )
}

describe('ReportViewer', () => {
  it('always shows the Post to Webex button', () => {
    const html = renderViewer({ template: 'daily' })
    expect(html).toContain('Post to Webex')
  })

  it('shows the Email draft button only for the wrap template', () => {
    const wrapHtml = renderViewer({ template: 'wrap' })
    expect(wrapHtml).toContain('Email draft')

    const dailyHtml = renderViewer({ template: 'daily' })
    expect(dailyHtml).not.toContain('Email draft')
  })

  it('renders nothing extra when there is no report yet', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <ReportViewer report={null} />
      </QueryClientProvider>
    )
    expect(html).toContain('Pick a template and hit Run.')
    expect(html).not.toContain('Post to Webex')
  })
})
