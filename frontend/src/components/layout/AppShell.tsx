import { AnimatePresence, motion } from 'motion/react'
import {
  BookOpen,
  Bot,
  Command,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Search,
  Sparkles,
  Sun,
  UploadCloud,
  UserCircle,
  X,
  Globe,
  History,
} from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Button, cn } from '../ui/Primitives'
import { useTheme } from '../../context/ThemeContext'
import { useAuth } from '../../context/AuthContext'
import { useResearch } from '../../context/ResearchContext'
import { PdfViewerDrawer } from '../pdf/PdfViewerDrawer'
import { OnlineDiscoveryModal } from '../discovery/OnlineDiscoveryModal'

interface AppShellProps {
  children?: ReactNode
}

const primaryNav = [
  { label: 'Overview', to: '/app', icon: LayoutDashboard },
  { label: 'Research library', to: '/app/library', icon: BookOpen },
  { label: 'Upload papers', to: '/app/upload', icon: UploadCloud },
  { label: 'AI chat & citations', to: '/app/chat', icon: Bot },
  { label: 'Research history', to: '/app/history', icon: History },
]

const secondaryNav = [
  { label: 'Profile', to: '/app/profile', icon: UserCircle },
]

const commands = [
  { label: 'Open overview', to: '/app' },
  { label: 'Search research library', to: '/app/library' },
  { label: 'Start an AI chat', to: '/app/chat' },
  { label: 'Upload a research paper', to: '/app/upload' },
  { label: 'Open research history', to: '/app/history' },
  { label: 'View profile', to: '/app/profile' },
]

function BrandMark() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-2xl bg-ink text-white shadow-[0_8px_18px_rgba(16,24,40,0.18)]">
        <Sparkles size={18} className="text-violet-300" />
        <span className="absolute -bottom-4 -right-3 h-8 w-8 rounded-full bg-violet/70 blur-lg" />
      </div>
      <div>
        <p className="font-display text-2xl font-semibold leading-none tracking-tight text-ink">
          Lumina
        </p>
        <p className="mono-label mt-1 text-[9px] text-slate font-bold uppercase tracking-wider">
          Dynamic Grounded RAG
        </p>
      </div>
    </div>
  )
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { openOnlineDiscovery } = useResearch()
  const { user, displayName, initials, logout } = useAuth()

  return (
    <aside className="flex h-full w-[260px] shrink-0 flex-col border-r border-border bg-surface/75 px-4 py-5 backdrop-blur-2xl dark:bg-[#111a2f]/80">
      <div className="px-2">
        <BrandMark />
      </div>

      <div className="mt-8 flex items-center justify-between px-2">
        <span className="mono-label text-slate">Workspace</span>
        <span className="rounded-full bg-teal-soft px-2 py-0.5 text-[9px] font-bold text-teal">
          SYSTEM 2.0
        </span>
      </div>

      <nav className="mt-3 flex-1 space-y-1 overflow-y-auto" aria-label="Workspace navigation">
        {primaryNav.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/app'}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition duration-200',
                isActive
                  ? 'bg-primary-soft font-semibold text-primary dark:bg-primary/20 dark:text-white'
                  : 'text-slate hover:bg-surface-muted hover:text-ink dark:hover:bg-white/5'
              )
            }
          >
            <Icon
              size={17}
              className={cn(
                'transition',
                location.pathname === to ? 'text-primary dark:text-white' : 'text-slate group-hover:text-primary'
              )}
            />
            <span>{label}</span>
            {label.includes('AI chat') && <span className="ml-auto h-2 w-2 rounded-full bg-teal" />}
          </NavLink>
        ))}

        {/* Dedicated Online Discovery Action */}
        <button
          onClick={() => {
            if (onNavigate) onNavigate()
            openOnlineDiscovery()
          }}
          className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-slate transition duration-200 hover:bg-violet-soft hover:text-violet dark:hover:bg-violet-900/20"
        >
          <Globe size={17} className="text-violet group-hover:scale-110 transition-transform" />
          <span>Online paper discovery</span>
        </button>
      </nav>

      <div className="border-t border-border pt-4">
        <div className="px-2 pb-2">
          <span className="mono-label text-slate">Account</span>
        </div>
        {secondaryNav.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition duration-200',
                isActive
                  ? 'bg-primary-soft font-semibold text-primary dark:bg-primary/20 dark:text-white'
                  : 'text-slate hover:bg-surface-muted hover:text-ink dark:hover:bg-white/5'
              )
            }
          >
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
        <button
          onClick={() => {
            logout()
            if (onNavigate) onNavigate()
            navigate('/login')
          }}
          className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate transition hover:bg-danger-soft hover:text-danger"
        >
          <LogOut size={17} />
          <span>Sign out</span>
        </button>
      </div>

      <div className="mt-4 flex items-center gap-3 rounded-2xl bg-surface-muted p-3 dark:bg-white/5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-violet text-white font-bold text-xs shadow-xs">
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-bold text-ink">{displayName}</p>
          <p className="truncate text-[10px] text-slate">{user?.email || 'Logged in'}</p>
        </div>
      </div>
    </aside>
  )
}

function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const filtered = useMemo(
    () => commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase())),
    [query]
  )

  useEffect(() => {
    if (!open) setQuery('')
  }, [open])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[120] flex items-start justify-center bg-black/50 p-4 pt-[12vh] backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={onClose}
        >
          <motion.div
            className="glass-panel w-full max-w-xl overflow-hidden rounded-3xl bg-surface"
            initial={{ y: -16, scale: 0.98 }}
            animate={{ y: 0, scale: 1 }}
            exit={{ y: -16, scale: 0.98 }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-border px-5">
              <Search size={18} className="text-slate" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') onClose()
                  if (e.key === 'Enter' && filtered[0]) {
                    navigate(filtered[0].to)
                    onClose()
                  }
                }}
                placeholder="Jump to a Lumina workspace view..."
                className="h-14 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-slate/60"
              />
              <kbd className="rounded-md border border-border px-1.5 py-1 text-[10px] text-slate">
                ESC
              </kbd>
            </div>
            <div className="p-2">
              {filtered.map((command, index) => (
                <button
                  key={command.to}
                  className="flex w-full items-center justify-between rounded-xl px-3 py-3 text-left text-sm text-ink transition hover:bg-primary-soft hover:text-primary"
                  onClick={() => {
                    navigate(command.to)
                    onClose()
                  }}
                >
                  <span className="flex items-center gap-3">
                    <Command size={15} className="text-slate" />
                    {command.label}
                  </span>
                  {index === 0 && <span className="mono-label text-[9px] text-slate">Return</span>}
                </button>
              ))}
              {filtered.length === 0 && (
                <p className="px-3 py-8 text-center text-sm text-slate">No views found.</p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function Topbar({ onMenu, onCommand }: { onMenu: () => void; onCommand: () => void }) {
  const { mode, toggleMode } = useTheme()
  const { openOnlineDiscovery } = useResearch()
  const { user, displayName, initials, logout } = useAuth()
  const navigate = useNavigate()
  const [profileOpen, setProfileOpen] = useState(false)

  return (
    <header className="sticky top-0 z-30 flex h-[76px] items-center justify-between border-b border-border bg-canvas/75 px-4 backdrop-blur-xl sm:px-6 lg:px-10">
      <div className="flex min-w-0 items-center gap-3">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenu} aria-label="Open navigation">
          <Menu size={19} />
        </Button>

        <button
          onClick={onCommand}
          className="hidden h-10 w-[min(430px,48vw)] items-center gap-3 rounded-full border border-border bg-surface px-4 text-left text-xs text-slate transition hover:border-primary/30 sm:flex"
        >
          <Search size={16} />
          <span className="flex-1 truncate">Search papers, authors, citations, and models</span>
          <kbd className="rounded-md border border-border px-1.5 py-1 font-mono text-[9px]">⌘ K</kbd>
        </button>
      </div>

      <div className="flex items-center gap-2">
        {/* Global Online Discovery Trigger */}
        <Button
          variant="secondary"
          size="sm"
          onClick={() => openOnlineDiscovery()}
          className="hidden sm:inline-flex text-xs font-semibold"
        >
          <Globe size={14} className="text-violet" /> Discover Papers
        </Button>

        <button
          onClick={toggleMode}
          className="flex h-10 w-10 items-center justify-center rounded-full text-slate transition hover:bg-primary-soft hover:text-primary dark:hover:bg-white/10"
          aria-label={`Switch to ${mode === 'light' ? 'dark' : 'light'} mode`}
          title={`Switch to ${mode === 'light' ? 'dark' : 'light'} mode`}
        >
          {mode === 'light' ? <Moon size={18} /> : <Sun size={18} className="text-amber-400" />}
        </button>

        <div className="mx-2 hidden h-7 w-px bg-border sm:block" />

        <div className="relative">
          <button
            onClick={() => setProfileOpen((v) => !v)}
            className="flex items-center gap-2 rounded-full py-1 pl-1 pr-2 transition hover:bg-surface-muted dark:hover:bg-white/5"
            aria-expanded={profileOpen}
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-violet text-white text-xs font-bold shadow-xs">
              {initials}
            </div>
            <span className="hidden text-left sm:block">
              <span className="block text-xs font-bold text-ink">{displayName}</span>
              <span className="block text-[10px] text-slate">{user?.role || user?.institution || 'Researcher'}</span>
            </span>
          </button>

          <AnimatePresence>
            {profileOpen && (
              <motion.div
                className="absolute right-0 top-12 w-48 rounded-2xl border border-border bg-surface p-2 shadow-float"
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
              >
                <button
                  onClick={() => {
                    navigate('/app/profile')
                    setProfileOpen(false)
                  }}
                  className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-xs text-ink hover:bg-primary-soft dark:hover:bg-white/10"
                >
                  <UserCircle size={15} /> View profile
                </button>
                <button
                  onClick={() => {
                    logout()
                    setProfileOpen(false)
                    navigate('/login')
                  }}
                  className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-xs text-danger hover:bg-danger-soft"
                >
                  <LogOut size={15} /> Sign out
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  )
}

export function AppShell({ children }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCommandOpen(true)
      }
      if (e.key === 'Escape') {
        setCommandOpen(false)
        setMobileOpen(false)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <div className="hidden lg:fixed lg:inset-y-0 lg:z-40 lg:flex">
        <Sidebar />
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="fixed inset-0 z-[90] bg-black/50 backdrop-blur-sm lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileOpen(false)}
          >
            <motion.div
              className="h-full w-[min(290px,85vw)] bg-surface shadow-float"
              initial={{ x: -290 }}
              animate={{ x: 0 }}
              exit={{ x: -290 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-end p-3">
                <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
                  <X size={18} />
                </Button>
              </div>
              <Sidebar onNavigate={() => setMobileOpen(false)} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="lg:pl-[260px]">
        <Topbar onMenu={() => setMobileOpen(true)} onCommand={() => setCommandOpen(true)} />
        <main className="mx-auto max-w-[1480px] px-4 py-7 sm:px-6 lg:px-10 lg:py-10">
          {children ?? <Outlet />}
        </main>
      </div>

      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />

      {/* Global Interactive PDF Viewer Drawer */}
      <PdfViewerDrawer />

      {/* Global Online Paper Discovery Modal */}
      <OnlineDiscoveryModal />
    </div>
  )
}
