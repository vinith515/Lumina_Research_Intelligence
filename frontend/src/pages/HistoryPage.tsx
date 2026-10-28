import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  History,
  Search,
  Trash2,
  RefreshCw,
  MessageSquare,
  UploadCloud,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Clock,
  ShieldCheck,
  BookOpen,
  ArrowRight,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../context/AuthContext'
import { useResearch } from '../context/ResearchContext'
import {
  getUserHistory,
  deleteHistoryItem,
  clearUserHistory,
  type HistoryItem,
  type HistoryQueryItem,
  type HistoryUploadItem,
  type UserStatsResponse,
  type StructuredCitation,
} from '../services/api'
import { Button, Badge, SectionHeader, cn } from '../components/ui/Primitives'

export function HistoryPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { openPdfViewer } = useResearch()

  const [items, setItems] = useState<HistoryItem[]>([])
  const [stats, setStats] = useState<UserStatsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'all' | 'queries' | 'uploads'>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [evidenceFilter, setEvidenceFilter] = useState<'all' | 'STATE_A' | 'STATE_B' | 'STATE_C'>('all')
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({})
  const [showClearModal, setShowClearModal] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const userEmail = user?.email || 'guest@lumina.ai'

  async function loadHistory() {
    setIsLoading(true)
    try {
      const data = await getUserHistory(userEmail, {
        type: activeTab,
        search: searchTerm.trim() || undefined,
        limit: 100,
      })
      setItems(data.items || [])
      setStats(data.stats || null)
    } catch (err: any) {
      console.error('Failed to load user history:', err)
      toast.error('Could not load history from database.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [userEmail, activeTab])

  // Trigger search on enter or when search term changes after debounce
  useEffect(() => {
    const handler = setTimeout(() => {
      loadHistory()
    }, 300)
    return () => clearTimeout(handler)
  }, [searchTerm])

  function toggleExpand(id: string) {
    setExpandedItems((prev) => ({
      ...prev,
      [id]: !prev[id],
    }))
  }

  async function handleDelete(item: HistoryItem) {
    try {
      await deleteHistoryItem(item.id, userEmail)
      setItems((prev) => prev.filter((i) => i.id !== item.id))
      toast.success('History record removed.')
      if (stats) {
        setStats({
          ...stats,
          total_queries: item.type === 'query' ? Math.max(0, stats.total_queries - 1) : stats.total_queries,
          total_uploads: item.type === 'upload' ? Math.max(0, stats.total_uploads - 1) : stats.total_uploads,
        })
      }
    } catch (err: any) {
      console.error('Failed to delete item:', err)
      toast.error('Failed to delete record.')
    }
  }

  async function handleClearAll() {
    setIsDeleting(true)
    try {
      await clearUserHistory(userEmail, activeTab)
      setShowClearModal(false)
      toast.success('History cleared successfully.')
      await loadHistory()
    } catch (err: any) {
      console.error('Failed to clear history:', err)
      toast.error('Failed to clear history.')
    } finally {
      setIsDeleting(false)
    }
  }

  function handleResumeChat(queryText: string) {
    navigate('/app/chat', { state: { initialQuery: queryText } })
  }

  function handleOpenCitation(c: StructuredCitation) {
    openPdfViewer({
      paperId: c.paper_id,
      title: c.title,
      page: c.page_start || 1,
      snippet: c.snippet,
      section: c.section,
      citationId: c.citation_id,
    })
  }

  // Filter items by evidence state if applicable
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (evidenceFilter === 'all') return true
      if (item.type !== 'query') return false
      return item.evidence_state === evidenceFilter
    })
  }, [items, evidenceFilter])

  return (
    <div className="space-y-8">
      {/* Header */}
      <SectionHeader
        eyebrow="Persistent Audit Trail"
        title="Research & Activity History"
        description="Every scientific inquiry, grounded synthesis, verified citation, and paper upload is logged into your personal database."
        action={
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={loadHistory} disabled={isLoading}>
              <RefreshCw size={15} className={cn(isLoading && 'animate-spin')} /> Refresh
            </Button>
            {items.length > 0 && (
              <Button
                variant="secondary"
                className="text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/30"
                onClick={() => setShowClearModal(true)}
              >
                <Trash2 size={15} /> Clear History
              </Button>
            )}
          </div>
        }
      />

      {/* Metrics Summary Strip */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm dark:bg-white/5">
            <div className="flex items-center justify-between">
              <span className="mono-label text-slate">Total Queries</span>
              <MessageSquare size={16} className="text-primary" />
            </div>
            <p className="mt-2 font-display text-2xl font-bold text-ink dark:text-white">
              {stats.total_queries}
            </p>
            <p className="mt-0.5 text-[11px] text-slate">Scientific inquiries</p>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm dark:bg-white/5">
            <div className="flex items-center justify-between">
              <span className="mono-label text-slate">Total Citations</span>
              <ShieldCheck size={16} className="text-teal" />
            </div>
            <p className="mt-2 font-display text-2xl font-bold text-ink dark:text-white">
              {stats.total_citations}
            </p>
            <p className="mt-0.5 text-[11px] text-slate">Peer-reviewed links</p>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm dark:bg-white/5">
            <div className="flex items-center justify-between">
              <span className="mono-label text-slate">Papers Uploaded</span>
              <UploadCloud size={16} className="text-violet" />
            </div>
            <p className="mt-2 font-display text-2xl font-bold text-ink dark:text-white">
              {stats.total_uploads}
            </p>
            <p className="mt-0.5 text-[11px] text-slate">Indexed manuscripts</p>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm dark:bg-white/5">
            <div className="flex items-center justify-between">
              <span className="mono-label text-slate">Evidence Ratio</span>
              <Sparkles size={16} className="text-amber-500" />
            </div>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="inline-flex items-center gap-1 text-xs font-bold text-teal">
                <span className="h-2 w-2 rounded-full bg-teal" />
                {stats.evidence_distribution.STATE_A}
              </span>
              <span className="text-slate">/</span>
              <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-500">
                <span className="h-2 w-2 rounded-full bg-amber-500" />
                {stats.evidence_distribution.STATE_B}
              </span>
              <span className="text-slate">/</span>
              <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-500">
                <span className="h-2 w-2 rounded-full bg-rose-500" />
                {stats.evidence_distribution.STATE_C}
              </span>
            </div>
            <p className="mt-1 text-[10px] text-slate">State A / State B / State C</p>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Type Tabs */}
        <div className="inline-flex rounded-2xl border border-border bg-surface p-1 shadow-sm dark:bg-white/5">
          <button
            onClick={() => setActiveTab('all')}
            className={cn(
              'rounded-xl px-4 py-2 text-xs font-semibold transition',
              activeTab === 'all'
                ? 'bg-primary text-white shadow-sm'
                : 'text-slate hover:text-ink dark:hover:text-white'
            )}
          >
            All Activity
          </button>
          <button
            onClick={() => setActiveTab('queries')}
            className={cn(
              'rounded-xl px-4 py-2 text-xs font-semibold transition',
              activeTab === 'queries'
                ? 'bg-primary text-white shadow-sm'
                : 'text-slate hover:text-ink dark:hover:text-white'
            )}
          >
            Research Q&A
          </button>
          <button
            onClick={() => setActiveTab('uploads')}
            className={cn(
              'rounded-xl px-4 py-2 text-xs font-semibold transition',
              activeTab === 'uploads'
                ? 'bg-primary text-white shadow-sm'
                : 'text-slate hover:text-ink dark:hover:text-white'
            )}
          >
            Manuscript Uploads
          </button>
        </div>

        {/* Search & Evidence State Dropdown */}
        <div className="flex items-center gap-2">
          {activeTab !== 'uploads' && (
            <select
              value={evidenceFilter}
              onChange={(e) => setEvidenceFilter(e.target.value as any)}
              className="rounded-xl border border-border bg-surface px-3 py-2 text-xs font-semibold text-ink outline-none dark:bg-slate-900 dark:border-white/10 dark:text-white"
            >
              <option value="all">All Evidence States</option>
              <option value="STATE_A">State A — Strong Evidence</option>
              <option value="STATE_B">State B — Partial Evidence</option>
              <option value="STATE_C">State C — Insufficient Evidence</option>
            </select>
          )}

          <div className="relative min-w-[220px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate" />
            <input
              type="text"
              placeholder="Search past questions or papers..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-9 w-full rounded-xl border border-border bg-surface pl-9 pr-3 text-xs text-ink outline-none placeholder:text-slate/60 focus:border-primary dark:bg-white/5 dark:border-white/10 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* History Items Feed */}
      {isLoading ? (
        <div className="flex h-64 flex-col items-center justify-center gap-3">
          <RefreshCw size={24} className="animate-spin text-primary" />
          <p className="text-xs text-slate font-medium">Retrieving personal history from SQLite...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="rounded-[2rem] border border-dashed border-border bg-surface/40 p-12 text-center dark:bg-white/5">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-soft text-primary dark:bg-primary/20">
            <History size={26} />
          </div>
          <h3 className="mt-4 font-display text-lg font-bold text-ink dark:text-white">
            No research history found
          </h3>
          <p className="mx-auto mt-2 max-w-md text-xs text-slate">
            {searchTerm
              ? `No activity matching "${searchTerm}". Try a different search keyword.`
              : 'As you query Lumina and upload research manuscripts, your grounded Q&A trails and citations will be preserved here.'}
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Button variant="primary" onClick={() => navigate('/app/chat')}>
              <Sparkles size={14} /> Start Research Chat
            </Button>
            <Button variant="secondary" onClick={() => navigate('/app/upload')}>
              <UploadCloud size={14} /> Upload Paper
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredItems.map((item) => (
            <HistoryCard
              key={item.id}
              item={item}
              isExpanded={Boolean(expandedItems[item.id])}
              onToggle={() => toggleExpand(item.id)}
              onDelete={() => handleDelete(item)}
              onResumeChat={handleResumeChat}
              onOpenCitation={handleOpenCitation}
            />
          ))}
        </div>
      )}

      {/* Clear History Confirmation Modal */}
      <AnimatePresence>
        {showClearModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-[2rem] border border-border bg-surface p-6 shadow-2xl dark:bg-[#151f38]"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400">
                <Trash2 size={24} />
              </div>
              <h3 className="mt-4 font-display text-xl font-bold text-ink dark:text-white">
                Clear Personal History?
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-slate">
                This will permanently delete your logged research interactions, answers, and upload trails
                stored for <strong className="text-ink dark:text-white">{userEmail}</strong> in the database.
                This action cannot be undone.
              </p>

              <div className="mt-6 flex items-center justify-end gap-3">
                <Button variant="secondary" onClick={() => setShowClearModal(false)} disabled={isDeleting}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  className="bg-rose-600 hover:bg-rose-700 text-white"
                  onClick={handleClearAll}
                  disabled={isDeleting}
                >
                  {isDeleting ? 'Clearing...' : 'Yes, Delete All'}
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

function HistoryCard({
  item,
  isExpanded,
  onToggle,
  onDelete,
  onResumeChat,
  onOpenCitation,
}: {
  item: HistoryItem
  isExpanded: boolean
  onToggle: () => void
  onDelete: () => void
  onResumeChat: (query: string) => void
  onOpenCitation: (c: StructuredCitation) => void
}) {
  if (item.type === 'upload') {
    const uploadItem = item as HistoryUploadItem
    return (
      <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm transition hover:shadow-md dark:bg-white/5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3.5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet/10 text-violet">
              <UploadCloud size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Badge tone="violet">Upload Activity</Badge>
                <Badge tone={uploadItem.status === 'COMPLETED' ? 'teal' : uploadItem.status === 'FAILED' ? 'danger' : 'amber'}>
                  {uploadItem.status}
                </Badge>
                <Badge tone="primary">
                  {uploadItem.ingestion_mode === 'permanent' ? 'Permanent Corpus' : 'Session Isolated'}
                </Badge>
              </div>
              <h4 className="mt-1.5 font-display text-sm font-bold text-ink dark:text-white">
                {uploadItem.title || uploadItem.filename}
              </h4>
              <p className="mt-1 text-[11px] text-slate">
                File: <code className="text-ink dark:text-slate-300">{uploadItem.filename}</code> •{' '}
                {uploadItem.total_chunks > 0 ? `${uploadItem.total_chunks} chunks indexed` : 'Processing'} •{' '}
                {uploadItem.created_at}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center">
            <button
              onClick={onDelete}
              className="rounded-lg p-2 text-slate hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/30"
              title="Delete upload history record"
            >
              <Trash2 size={15} />
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Otherwise: Research Query Item
  const qItem = item as HistoryQueryItem
  const stateTone =
    qItem.evidence_state === 'STATE_A'
      ? 'teal'
      : qItem.evidence_state === 'STATE_B'
      ? 'amber'
      : 'danger'

  const stateLabel =
    qItem.evidence_state === 'STATE_A'
      ? 'State A: Strong Evidence'
      : qItem.evidence_state === 'STATE_B'
      ? 'State B: Partial Evidence'
      : 'State C: Insufficient Evidence'

  return (
    <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm transition hover:shadow-md dark:bg-white/5">
      {/* Card Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="primary">Research Q&A</Badge>
            <Badge tone={stateTone}>{stateLabel}</Badge>
            <Badge tone="neutral">{qItem.knowledge_scope.replace(/_/g, ' ')}</Badge>
            {qItem.latency_ms > 0 && (
              <span className="mono-label text-[10px] text-slate">
                <Clock size={11} className="inline mr-1" />
                {(qItem.latency_ms / 1000).toFixed(2)}s
              </span>
            )}
            <span className="text-[11px] text-slate ml-auto sm:ml-0">{qItem.created_at}</span>
          </div>

          <h4 className="mt-2.5 font-display text-base font-bold text-ink dark:text-white">
            {qItem.query}
          </h4>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 self-end sm:self-start">
          <Button
            variant="secondary"
            className="h-8 px-2.5 text-xs text-primary"
            onClick={() => onResumeChat(qItem.query)}
            title="Ask this question again in Chat"
          >
            <Sparkles size={13} /> Resume <ArrowRight size={13} />
          </Button>

          <button
            onClick={onToggle}
            className="rounded-lg p-1.5 text-slate hover:bg-surface-muted hover:text-ink dark:hover:bg-white/10"
            title={isExpanded ? 'Collapse answer' : 'Expand full answer'}
          >
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          <button
            onClick={onDelete}
            className="rounded-lg p-1.5 text-slate hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/30"
            title="Delete this query from history"
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {/* Answer Preview or Full Markdown */}
      <div className="mt-3.5 rounded-xl border border-border/60 bg-surface-muted/30 p-4 dark:bg-white/[0.02]">
        <div
          className={cn(
            'prose prose-xs max-w-none text-xs leading-relaxed text-ink/90 dark:prose-invert dark:text-slate-200',
            !isExpanded && 'line-clamp-3'
          )}
        >
          <ReactMarkdown>{qItem.answer}</ReactMarkdown>
        </div>

        {!isExpanded && (
          <button
            onClick={onToggle}
            className="mt-2 text-[11px] font-semibold text-primary hover:underline"
          >
            Read complete grounded synthesis →
          </button>
        )}
      </div>

      {/* Inline Verified Citations */}
      {qItem.citations && qItem.citations.length > 0 && (
        <div className="mt-3.5">
          <p className="mono-label text-[10px] text-slate">
            Verified Citations ({qItem.citations.length}):
          </p>
          <div className="mt-1.5 flex flex-wrap gap-2">
            {qItem.citations.map((c, i) => (
              <button
                key={c.citation_id || i}
                onClick={() => onOpenCitation(c)}
                className="group inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-2.5 py-1 text-[11px] font-medium text-slate transition hover:border-primary/50 hover:text-primary dark:bg-white/5"
                title={`Open ${c.title} (Page ${c.page_start || 1})`}
              >
                <BookOpen size={11} className="text-primary/70 group-hover:text-primary" />
                <span className="font-bold text-primary">[{c.citation_id || `C${i + 1}`}]</span>
                <span className="max-w-[200px] truncate">{c.title}</span>
                <span className="text-[10px] text-slate/70">p.{c.page_start || 1}</span>
                <ExternalLink size={10} className="opacity-0 group-hover:opacity-100" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
