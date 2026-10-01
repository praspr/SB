import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { SkeletonRow } from '@/components/shared/SkeletonRow'
import { LandingPage } from '@/pages/LandingPage'
import { AttentionPage } from '@/pages/AttentionPage'
import { SkillsPage } from '@/pages/SkillsPage'
import { TodosPage } from '@/pages/TodosPage'
import { JirasPage } from '@/pages/JirasPage'
import { MeetingsPage } from '@/pages/MeetingsPage'
import { WebexPage } from '@/pages/WebexPage'

const GoalsPage = lazy(() => import('@/pages/GoalsPage').then((module) => ({ default: module.GoalsPage })))
const ReportsPage = lazy(() => import('@/pages/ReportsPage').then((module) => ({ default: module.ReportsPage })))
const LedgerPage = lazy(() => import('@/pages/LedgerPage').then((module) => ({ default: module.LedgerPage })))
const ProposalsPage = lazy(() => import('@/pages/ProposalsPage').then((module) => ({ default: module.ProposalsPage })))

function lazyRoute(element: ReactNode) {
  return <Suspense fallback={<SkeletonRow lines={4} />}>{element}</Suspense>
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: 'attention', element: <AttentionPage /> },
      { path: 'goals', element: lazyRoute(<GoalsPage />) },
      { path: 'reports', element: lazyRoute(<ReportsPage />) },
      { path: 'ledger', element: lazyRoute(<LedgerPage />) },
      { path: 'proposals', element: lazyRoute(<ProposalsPage />) },
      { path: 'skills', element: <SkillsPage /> },
      { path: 'signals', element: lazyRoute(<LedgerPage />) },
      { path: 'todos', element: <TodosPage /> },
      { path: 'jira', element: <JirasPage /> },
      { path: 'meetings', element: <MeetingsPage /> },
      { path: 'webex', element: <WebexPage /> },
    ],
  },
])
