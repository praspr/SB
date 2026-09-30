import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { LandingPage } from '@/pages/LandingPage'
import { StatusPage } from '@/pages/StatusPage'
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
      { path: 'todos', element: <TodosPage /> },
      { path: 'jira', element: <JirasPage /> },
      { path: 'meetings', element: <MeetingsPage /> },
      { path: 'webex', element: <WebexPage /> },
    ],
  },
])
