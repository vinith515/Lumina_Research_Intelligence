import { MotionConfig } from 'motion/react'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import { ResearchProvider } from './context/ResearchContext'
import { AppRoutes } from './routes/AppRoutes'

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <ResearchProvider>
            <MotionConfig reducedMotion="user">
              <AppRoutes />
            </MotionConfig>
          <Toaster
            position="bottom-right"
            toastOptions={{
              duration: 3200,
              style: {
                borderRadius: '14px',
                fontSize: '12px',
                border: '1px solid #e3e7f0',
                boxShadow: '0 16px 40px rgba(16,24,40,.08)',
              },
            }}
          />
          </ResearchProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}

export default App
