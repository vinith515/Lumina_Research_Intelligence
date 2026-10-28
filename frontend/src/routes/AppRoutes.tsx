import { Routes, Route, Navigate } from 'react-router-dom'
import { WorkspaceLayout } from '../layouts/WorkspaceLayout'
import { LandingPage } from '../pages/LandingPage'
import { AuthPage } from '../pages/AuthPage'
import { DashboardPage } from '../pages/DashboardPage'
import { LibraryPage } from '../pages/LibraryPage'
import { UploadPage } from '../pages/UploadPage'
import { ChatPage } from '../pages/ChatPage'
import { HistoryPage } from '../pages/HistoryPage'
import { ErrorPage, PaperDetailPage, ProfilePage } from '../pages/ResearchToolsPages'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<AuthPage />} />
      <Route path="/signup" element={<AuthPage />} />
      <Route path="/forgot-password" element={<AuthPage />} />
      <Route path="/reset-password" element={<AuthPage />} />
      <Route path="/500" element={<ErrorPage code="500" />} />
      <Route path="/network-error" element={<ErrorPage code="network" />} />
      <Route path="/404" element={<ErrorPage code="404" />} />

      <Route path="/app" element={<WorkspaceLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="papers/:paperId" element={<PaperDetailPage />} />

        {/* Redirect removed demo routes cleanly to relevant active features */}
        <Route path="collections" element={<Navigate to="/app/library" replace />} />
        <Route path="search" element={<Navigate to="/app/chat" replace />} />
        <Route path="analytics" element={<Navigate to="/app" replace />} />
        <Route path="settings" element={<Navigate to="/app/profile" replace />} />
        <Route path="admin" element={<Navigate to="/app" replace />} />
      </Route>

      <Route path="*" element={<ErrorPage code="404" />} />
    </Routes>
  )
}
