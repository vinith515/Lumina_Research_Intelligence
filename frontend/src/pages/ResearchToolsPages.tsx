import { useState, useEffect } from 'react'
import {
  ArrowLeft,
  ArrowUpRight,
  ChevronRight,
  ExternalLink,
  FileText,
  Save,
  Sparkles,
  UserRound,
} from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import { useResearch } from '../context/ResearchContext'
import { Badge, Button, Field, GlassCard, Input, SectionHeader } from '../components/ui/Primitives'

export function ProfilePage() {
  const { user, displayName, initials, updateProfile, logout } = useAuth()
  const navigate = useNavigate()
  const [saved, setSaved] = useState(false)

  const [name, setName] = useState(displayName)
  const [email, setEmail] = useState(user?.email || '')
  const [institution, setInstitution] = useState(user?.institution || 'Research Institute')
  const [role, setRole] = useState(user?.role || 'Researcher')
  const [interests, setInterests] = useState(
    user?.researchInterests?.join(', ') || 'Machine Learning, Scientific RAG, Information Retrieval'
  )

  useEffect(() => {
    setName(displayName)
    setEmail(user?.email || '')
    setInstitution(user?.institution || 'Research Institute')
    setRole(user?.role || 'Researcher')
    if (user?.researchInterests) {
      setInterests(user.researchInterests.join(', '))
    }
  }, [user, displayName])

  const handleSave = () => {
    updateProfile({
      name: name.trim() || displayName,
      email: email.trim(),
      institution: institution.trim(),
      role: role.trim(),
      researchInterests: interests
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
    })
    setSaved(true)
    toast.success('Profile updated successfully.')
    setTimeout(() => setSaved(false), 2500)
  }

  const handleDeleteAccount = () => {
    if (window.confirm('Are you sure you want to sign out and clear your active session?')) {
      logout()
      toast.success('Session cleared.')
      navigate('/login')
    }
  }

  const parsedInterests = interests
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Your Research Identity"
        title="Researcher Profile"
        description="Manage your identity, affiliation, and academic interests for contextual scientific synthesis."
        action={
          <Button variant="primary" onClick={handleSave}>
            <Save size={15} /> {saved ? 'Saved' : 'Save profile'}
          </Button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[0.65fr_1.35fr]">
        <GlassCard className="flex flex-col items-center p-6 text-center">
          <div className="relative">
            <div className="flex h-28 w-28 items-center justify-center rounded-[2rem] bg-gradient-to-br from-primary to-violet text-3xl font-bold text-white shadow-float">
              {initials}
            </div>
          </div>
          <h2 className="mt-6 font-display text-3xl font-semibold text-ink">{displayName}</h2>
          <p className="mt-1 text-xs text-slate">
            {role} · {institution}
          </p>
          <div className="mt-7 w-full border-t border-border pt-5 text-left">
            <p className="mono-label text-primary">Research interests</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {parsedInterests.map((interest, idx) => (
                <Badge
                  key={interest}
                  tone={idx % 3 === 0 ? 'primary' : idx % 3 === 1 ? 'violet' : 'teal'}
                >
                  {interest}
                </Badge>
              ))}
            </div>
          </div>
        </GlassCard>
        <div className="space-y-6">
          <GlassCard className="p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-soft text-primary">
                <UserRound size={18} />
              </div>
              <div>
                <h2 className="font-display text-3xl font-semibold text-ink">Personal details</h2>
                <p className="text-xs text-slate">This information is private to your active research session.</p>
              </div>
            </div>
            <div className="mt-7 grid gap-5 sm:grid-cols-2">
              <Field label="Full name">
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Alex Morgan" />
              </Field>
              <Field label="Research email">
                <Input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  type="email"
                  placeholder="researcher@university.edu"
                />
              </Field>
              <Field label="Institution / Organization">
                <Input
                  value={institution}
                  onChange={(e) => setInstitution(e.target.value)}
                  placeholder="e.g. Department of Computer Science"
                />
              </Field>
              <Field label="Academic Role">
                <Input
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g. Lead Researcher / Graduate Scholar"
                />
              </Field>
              <div className="sm:col-span-2">
                <Field label="Research interests" hint="Separate multiple interests with commas.">
                  <Input
                    value={interests}
                    onChange={(e) => setInterests(e.target.value)}
                    placeholder="Machine Learning, Retrieval-Augmented Generation, Computational Biology"
                  />
                </Field>
              </div>
            </div>
            <div className="mt-6 flex justify-end">
              <Button variant="primary" onClick={handleSave}>
                <Save size={15} /> Save changes
              </Button>
            </div>
          </GlassCard>

          <div className="rounded-card border border-danger/15 bg-danger-soft p-5">
            <p className="mono-label text-danger">Session Management</p>
            <h2 className="mt-2 font-display text-2xl font-semibold text-danger">Sign out / Reset Session</h2>
            <p className="mt-2 text-xs leading-5 text-danger/70">
              Clear your active session credentials and return to the login screen.
            </p>
            <Button variant="danger" size="sm" className="mt-5" onClick={handleDeleteAccount}>
              Sign out of workspace
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function PaperDetailPage() {
  const navigate = useNavigate()
  const { paperId } = useParams()
  const { papers, openPdfViewer, setPaperIsolation } = useResearch()

  const paper = papers.find((p) => p.paper_id === paperId)

  if (!paper) return <Navigate to="/app/library" replace />

  return (
    <div className="space-y-8">
      <button
        onClick={() => navigate('/app/library')}
        className="flex items-center gap-2 text-xs font-semibold text-slate hover:text-primary transition"
      >
        <ArrowLeft size={15} /> Back to research library
      </button>

      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="teal">{paper.category || 'Peer-Reviewed'}</Badge>
            {paper.is_user_uploaded && <Badge tone="primary">User Upload</Badge>}
            {paper.year && <span className="text-xs text-slate">{paper.year}</span>}
          </div>
          <h1 className="mt-4 max-w-4xl font-display text-5xl font-semibold leading-[0.92] text-ink sm:text-6xl">
            {paper.title}
          </h1>
          <p className="mt-4 text-sm text-slate">{paper.category || 'Peer-Reviewed Scientific Literature'}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => openPdfViewer({ paperId: paper.paper_id, title: paper.title, page: 1 })}
          >
            <ExternalLink size={15} /> Open PDF Drawer
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              setPaperIsolation(paper.paper_id, paper.title)
              navigate('/app/chat')
            }}
          >
            <Sparkles size={15} /> Query in AI Chat
          </Button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="space-y-6">
          <GlassCard className="p-6">
            <div className="flex items-center gap-2">
              <FileText size={17} className="text-primary" />
              <p className="mono-label text-primary">Paper Details</p>
            </div>
            <p className="mt-5 text-base leading-8 text-slate">
              This paper has been indexed into the Lumina dual-index retrieval engine (ChromaDB dense embeddings + BM25 sparse index). It is ready for scope-isolated semantic retrieval and claim verification.
            </p>
          </GlassCard>

          <GlassCard className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="mono-label text-violet">Structure</p>
                <h2 className="mt-1 font-display text-3xl font-semibold text-ink">Corpus Partitioning</h2>
              </div>
              <Badge tone="violet">{paper.total_chunks || 'Structured'} chunks</Badge>
            </div>
            <div className="mt-6 grid gap-2 sm:grid-cols-2">
              {[
                'Title & Metadata Extraction',
                'Abstract & Executive Narrative',
                'Methodology & Architecture',
                'Empirical Evaluation & Results',
                'Discussion & Evidence Lineage',
                'References & Provenance Nodes',
              ].map((section, index) => (
                <div
                  key={section}
                  className="flex items-center justify-between rounded-xl border border-border bg-surface-muted/50 px-4 py-3 text-left text-xs font-semibold text-ink dark:bg-white/5"
                >
                  <span>
                    {index + 1}. {section}
                  </span>
                  <ChevronRight size={14} className="text-slate" />
                </div>
              ))}
            </div>
          </GlassCard>
        </div>

        <aside className="space-y-6">
          <GlassCard className="p-6">
            <p className="mono-label text-slate">Index Telemetry</p>
            <dl className="mt-5 space-y-4">
              {[
                ['Paper ID', paper.paper_id],
                ['Category', paper.category || 'Computer Science'],
                ['Total Chunks', `${paper.total_chunks || 'Indexed'}`],
                ['Retrieval Mode', 'Hybrid RRF (k=60)'],
                ['Indexing Status', 'Embedded & Ready'],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-4">
                  <dt className="text-xs text-slate">{label}</dt>
                  <dd className="text-right text-xs font-bold text-ink truncate max-w-[180px]">{value}</dd>
                </div>
              ))}
            </dl>
          </GlassCard>
        </aside>
      </div>
    </div>
  )
}

export function ErrorPage({ code = '404' }: { code?: '404' | '500' | 'network' }) {
  const location = useLocation()
  const resolved = code === '404' && location.pathname === '/network-error' ? 'network' : code
  const content =
    resolved === '500'
      ? {
          eyebrow: 'System Notice',
          title: 'The server lost the thread.',
          copy: 'We could not complete that request. Your indexed corpus is safe; please try again.',
          action: 'Return to workspace',
        }
      : resolved === 'network'
      ? {
          eyebrow: 'Connection Notice',
          title: 'The connection went quiet.',
          copy: 'Check your connection to the Lumina backend, then return to the workspace.',
          action: 'Return to workspace',
        }
      : {
          eyebrow: 'Page Not Found',
          title: 'This view does not exist.',
          copy: 'The page you are looking for may have moved or was removed in the latest workspace update.',
          action: 'Back to workspace',
        }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-5 py-12 text-center">
      <div className="max-w-xl">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-primary to-violet text-white shadow-md">
          <Sparkles size={24} />
        </div>
        <p className="mono-label mt-8 text-primary">{content.eyebrow}</p>
        <h1 className="mt-4 font-display text-6xl font-semibold leading-[0.9] text-ink sm:text-8xl">
          {resolved === 'network' ? 'Offline.' : code}
        </h1>
        <h2 className="mt-5 font-display text-4xl font-semibold leading-tight text-ink">{content.title}</h2>
        <p className="mx-auto mt-4 max-w-md text-sm leading-6 text-slate">{content.copy}</p>
        <div className="mt-8">
          <Link to="/app">
            <Button variant="primary">
              {content.action} <ArrowUpRight size={16} />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
