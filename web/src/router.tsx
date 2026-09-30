import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { LandingPage } from '@/pages/LandingPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { LedgerPage } from '@/pages/LedgerPage'
import { ProposalsPage } from '@/pages/ProposalsPage'
import { SkillsPage } from '@/pages/SkillsPage'
import { SignalsPage } from '@/pages/SignalsPage'
import { TodayPage } from '@/pages/TodayPage'
import { WrapPage } from '@/pages/WrapPage'
import { StandupPage } from '@/pages/StandupPage'
import { TodosPage } from '@/pages/TodosPage'
import { JirasPage } from '@/pages/JirasPage'
import { MeetingsPage } from '@/pages/MeetingsPage'
import { WebexPage } from '@/pages/WebexPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: 'reports', element: <ReportsPage /> },
      { path: 'ledger', element: <LedgerPage /> },
      { path: 'proposals', element: <ProposalsPage /> },
      { path: 'skills', element: <SkillsPage /> },
      { path: 'signals', element: <SignalsPage /> },
      { path: 'today', element: <TodayPage /> },
      { path: 'wrap', element: <WrapPage /> },
      { path: 'standup', element: <StandupPage /> },
      { path: 'todos', element: <TodosPage /> },
      { path: 'jira', element: <JirasPage /> },
      { path: 'meetings', element: <MeetingsPage /> },
      { path: 'webex', element: <WebexPage /> },
    ],
  },
])
