import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { LandingPage } from '@/pages/LandingPage'
import { StatusPage } from '@/pages/StatusPage'
import { SkillsPage } from '@/pages/SkillsPage'
import { SignalsPage } from '@/pages/SignalsPage'
import { TodayPage } from '@/pages/TodayPage'
import { WrapPage } from '@/pages/WrapPage'
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
      { path: 'status', element: <StatusPage /> },
      { path: 'skills', element: <SkillsPage /> },
      { path: 'signals', element: <SignalsPage /> },
      { path: 'today', element: <TodayPage /> },
      { path: 'wrap', element: <WrapPage /> },
      { path: 'todos', element: <TodosPage /> },
      { path: 'jira', element: <JirasPage /> },
      { path: 'meetings', element: <MeetingsPage /> },
      { path: 'webex', element: <WebexPage /> },
    ],
  },
])
