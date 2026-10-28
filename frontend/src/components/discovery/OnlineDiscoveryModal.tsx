import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Search,
  Globe,
  CheckSquare,
  Square,
  ExternalLink,
  LoaderCircle,
  FileCheck2,
  X,
  Sparkles,
  ArrowRight,
  Database,
  Calendar,
  User,
  Clock,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useResearch } from '../../context/ResearchContext'
import {
  searchOnlinePapers,
  ingestOnlinePapers,
  type OnlinePaperCandidate,
  type IngestionJobStage,
} from '../../services/api'
import { Badge, Button, GlassCard, cn } from '../ui/Primitives'

const STAGE_LABELS: Record<string, string> = {
  PENDING: 'Pending in Queue',
  DOWNLOADING: 'Downloading PDF',
  DOWNLOADED: 'Download Completed',
  PARSING: 'Extracting Elements (Unstructured)',
  CHUNKING: 'Semantic Chunking',
  EMBEDDING: 'Generating Embeddings (SciBERT)',
  INDEXING: 'Indexing to FAISS & BM25',
  COMPLETED: 'Ready for Retrieval',
  FAILED: 'Processing Failed',
}

const STAGE_ORDER: IngestionJobStage[] = [
  'DOWNLOADING',
  'PARSING',
  'CHUNKING',
  'EMBEDDING',
  'INDEXING',
  'COMPLETED',
]

export function OnlineDiscoveryModal() {
  const {
    onlineDiscovery,
    closeOnlineDiscovery,
    trackJob,
    activeJobs,
    setSelectedScope,
    refreshPapers,
    sessionId,
  } = useResearch()

  const [query, setQuery] = useState('')
  const [provider, setProvider] = useState<'all' | 'arxiv' | 'semantic_scholar'>('all')
  const [isSearching, setIsSearching] = useState(false)
  const [candidates, setCandidates] = useState<OnlinePaperCandidate[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [isConfirmingIngest, setIsConfirmingIngest] = useState(false)
  const [isIngesting, setIsIngesting] = useState(false)
  const [ingestionMode, setIngestionMode] = useState<'permanent' | 'session_only'>('permanent')
  const [createdJobIds, setCreatedJobIds] = useState<string[]>([])
  const [hasSearched, setHasSearched] = useState(false)

  useEffect(() => {
    if (onlineDiscovery.isOpen) {
      const q = onlineDiscovery.initialQuery || ''
      setQuery(q)
      setCandidates([])
      setSelectedIds(new Set())
      setIsConfirmingIngest(false)
      setIsIngesting(false)
      setCreatedJobIds([])
      setHasSearched(false)

      if (q.trim()) {
        executeSearch(q, provider)
      }
    }
  }, [onlineDiscovery.isOpen, onlineDiscovery.initialQuery])

  if (!onlineDiscovery.isOpen) return null

  async function executeSearch(searchQuery: string, searchProvider = provider) {
    if (!searchQuery.trim()) return
    setIsSearching(true)
    setHasSearched(true)
    try {
      const res = await searchOnlinePapers(searchQuery, searchProvider, 8)
      // Normalize candidates to guarantee non-null unique id
      const mapped = (res.candidates || []).map((c, idx) => ({
        ...c,
        id: c.id || c.candidate_id || c.identifier || `cand_${idx}_${Date.now()}`,
        source_provider: c.source_provider || (c as any).source || 'arxiv',
      }))
      // Sort candidates by relevance score descending
      const sorted = mapped.sort(
        (a, b) => (b.relevance_score ?? 0.8) - (a.relevance_score ?? 0.8)
      )
      setCandidates(sorted)
      // Auto-select the top 2 most relevant by default
      const defaultSelected = new Set(sorted.slice(0, 2).map((c) => c.id).filter(Boolean))
      setSelectedIds(defaultSelected)
    } catch (err) {
      toast.error('Failed to search online sources. Check your connection.')
      console.error(err)
    } finally {
      setIsSearching(false)
    }
  }

  function toggleCandidate(id: string) {
    if (!id) return
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  function selectAll() {
    setSelectedIds(new Set(candidates.map((c) => c.id).filter(Boolean)))
  }

  function deselectAll() {
    setSelectedIds(new Set())
  }

  async function handleConfirmAndIngest() {
    const selectedCandidates = candidates.filter((c) => selectedIds.has(c.id))
    if (!selectedCandidates.length) {
      toast.error('Please select at least one paper to ingest.')
      return
    }

    setIsIngesting(true)
    try {
      const res = await ingestOnlinePapers(selectedCandidates, sessionId, ingestionMode)
      const jobIds = res.jobs.map((j) => j.job_id)
      setCreatedJobIds(jobIds)
      jobIds.forEach((jid) => trackJob(jid))
      const modeLabel = ingestionMode === 'permanent' ? 'Permanent Database' : 'Session Only'
      toast.success(`Dispatched ingestion (${modeLabel}) for ${jobIds.length} paper(s)!`)
    } catch (err) {
      toast.error('Error starting ingestion. Please try again.')
      console.error(err)
    } finally {
      setIsIngesting(false)
      setIsConfirmingIngest(false)
    }
  }

  // Check progress of created jobs
  const trackedJobs = activeJobs.filter((j) => createdJobIds.includes(j.job_id))
  const allCompleted =
    trackedJobs.length > 0 &&
    trackedJobs.every((j) => j.status === 'COMPLETED' || j.status === 'FAILED')
  const completedSuccessCount = trackedJobs.filter((j) => j.status === 'COMPLETED').length

  function handleContinueWithQuery() {
    // Switch scope to Expanded Research
    setSelectedScope('global_plus_user_plus_online')
    refreshPapers()
    closeOnlineDiscovery()
    if (onlineDiscovery.onComplete) {
      onlineDiscovery.onComplete()
    }
    toast.success('Scope switched to Expanded Research. Context updated!')
  }

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="glass-panel flex max-h-[90vh] w-full max-w-4xl flex-col rounded-3xl bg-surface shadow-2xl dark:bg-[#0f172a]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-primary text-white shadow-sm">
              <Globe size={20} />
            </div>
            <div>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Online Research Discovery
              </h2>
              <p className="text-xs text-slate">
                Search & ingest peer-reviewed literature from arXiv and Semantic Scholar
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={closeOnlineDiscovery} aria-label="Close modal">
            <X size={18} />
          </Button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Active Job Progress View (If jobs were initiated) */}
          {createdJobIds.length > 0 ? (
            <div className="space-y-6">
              <div className="rounded-2xl border border-primary/20 bg-primary-soft/40 p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-primary font-semibold text-sm">
                    <LoaderCircle
                      className={allCompleted ? 'text-teal' : 'animate-spin text-primary'}
                      size={18}
                    />
                    <span>
                      {allCompleted
                        ? `Ingestion Finished (${completedSuccessCount}/${trackedJobs.length} Ready)`
                        : 'Dynamic Celery Ingestion Pipeline Running'}
                    </span>
                  </div>
                  <Badge tone={allCompleted ? 'teal' : 'primary'}>
                    {allCompleted ? 'Complete' : 'In Progress'}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-slate">
                  Downloaded papers are processed through PDF layout extraction, semantic chunking,
                  SciBERT embeddings, and indexed into FAISS & BM25.
                </p>
              </div>

              {/* Progress for each paper */}
              <div className="space-y-4">
                {trackedJobs.map((job) => {
                  const currentStageIdx = STAGE_ORDER.indexOf(job.status)
                  const isDone = job.status === 'COMPLETED'
                  const isFail = job.status === 'FAILED'

                  return (
                    <GlassCard key={job.job_id} className="p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h4 className="truncate text-sm font-bold text-ink">
                            {job.file_name.replace('.pdf', '')}
                          </h4>
                          <p className="mt-0.5 text-xs text-slate">
                            {job.status_message || STAGE_LABELS[job.status] || job.status}
                          </p>
                        </div>
                        <Badge tone={isDone ? 'teal' : isFail ? 'danger' : 'violet'}>
                          {job.status}
                        </Badge>
                      </div>

                      {/* Stage checklist display matching Section 7 */}
                      <div className="mt-4 grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px]">
                        {[
                          { key: 'DOWNLOADING', label: 'Download' },
                          { key: 'PARSING', label: 'Extraction' },
                          { key: 'CHUNKING', label: 'Chunking' },
                          { key: 'EMBEDDING', label: 'Embedding' },
                          { key: 'INDEXING', label: 'Indexing' },
                        ].map((stage, idx) => {
                          let stageStatus = 'pending'
                          if (isDone) {
                            stageStatus = 'completed'
                          } else if (currentStageIdx > idx) {
                            stageStatus = 'completed'
                          } else if (currentStageIdx === idx) {
                            stageStatus = 'active'
                          }

                          return (
                            <div
                              key={stage.key}
                              className={`rounded-xl p-2 border ${
                                stageStatus === 'completed'
                                  ? 'border-teal/30 bg-teal-soft/60 text-teal dark:bg-teal-900/20'
                                  : stageStatus === 'active'
                                  ? 'border-primary/40 bg-primary-soft text-primary animate-pulse'
                                  : 'border-border bg-surface-muted text-slate/70 dark:bg-white/5'
                              }`}
                            >
                              <div className="font-semibold">{stage.label}</div>
                              <div className="text-[9px] uppercase tracking-wider">
                                {stageStatus === 'completed'
                                  ? 'Completed'
                                  : stageStatus === 'active'
                                  ? 'In Progress'
                                  : 'Pending'}
                              </div>
                            </div>
                          )
                        })}
                      </div>

                      {isDone && (
                        <p className="mt-3 text-[11px] font-semibold text-teal flex items-center gap-1.5">
                          <FileCheck2 size={13} /> {job.chunk_count} chunks indexed into knowledge graph.
                        </p>
                      )}
                    </GlassCard>
                  )
                })}
              </div>

              {allCompleted && (
                <div className="pt-3 flex justify-end">
                  <Button variant="primary" size="lg" onClick={handleContinueWithQuery}>
                    Continue with Original Research Question <ArrowRight size={16} />
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <>
              {/* Search Bar & Provider Filter */}
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="flex flex-1 items-center gap-2 rounded-2xl border border-border bg-surface px-4 py-1.5 shadow-sm">
                  <Search size={18} className="text-slate" />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && executeSearch(query)}
                    placeholder="Search arXiv and Semantic Scholar (e.g. attention mechanisms, MoE scaling)..."
                    className="h-10 min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-slate/60"
                  />
                  {query && (
                    <button
                      onClick={() => setQuery('')}
                      className="text-slate hover:text-ink text-xs"
                    >
                      Clear
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={provider}
                    onChange={(e) => {
                      const newP = e.target.value as 'all' | 'arxiv' | 'semantic_scholar'
                      setProvider(newP)
                      if (query.trim()) executeSearch(query, newP)
                    }}
                    className="h-11 rounded-2xl border border-border bg-surface px-3 text-xs font-semibold text-ink outline-none"
                  >
                    <option value="all">All Sources (arXiv + S2)</option>
                    <option value="arxiv">arXiv Only</option>
                    <option value="semantic_scholar">Semantic Scholar Only</option>
                  </select>

                  <Button
                    variant="primary"
                    disabled={isSearching || !query.trim()}
                    onClick={() => executeSearch(query)}
                  >
                    {isSearching ? (
                      <>
                        <LoaderCircle size={15} className="animate-spin" /> Searching...
                      </>
                    ) : (
                      <>
                        <Search size={15} /> Search
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Candidate Results */}
              {isSearching ? (
                <div className="py-20 text-center">
                  <LoaderCircle size={32} className="mx-auto animate-spin text-primary" />
                  <p className="mt-4 font-display text-xl font-semibold text-ink">
                    Querying scientific paper indices...
                  </p>
                  <p className="mt-1 text-xs text-slate">
                    Cross-referencing arXiv preprint API and Semantic Scholar graph
                  </p>
                </div>
              ) : candidates.length > 0 ? (
                <div className="space-y-4">
                  {/* Action Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
                    <div className="flex items-center gap-3">
                      <span className="mono-label text-xs text-ink font-semibold">
                        Found {candidates.length} Candidate Papers
                      </span>
                      <div className="flex items-center gap-2 text-xs">
                        <button
                          onClick={selectAll}
                          className="text-primary hover:underline font-semibold"
                        >
                          Select All
                        </button>
                        <span className="text-slate">•</span>
                        <button
                          onClick={deselectAll}
                          className="text-slate hover:text-ink font-semibold"
                        >
                          Deselect All
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate font-medium">
                        {selectedIds.size} paper(s) selected
                      </span>
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={selectedIds.size === 0}
                        onClick={() => setIsConfirmingIngest(true)}
                      >
                        <Database size={14} /> Ingest Selected Papers
                      </Button>
                    </div>
                  </div>

                  {/* List of candidates */}
                  <div className="space-y-3">
                    {candidates.map((cand) => {
                      const isSelected = selectedIds.has(cand.id)
                      const isArxiv = cand.source_provider === 'arxiv'

                      return (
                        <div
                          key={cand.id}
                          onClick={() => toggleCandidate(cand.id)}
                          className={`cursor-pointer rounded-2xl border p-4 transition-all ${
                            isSelected
                              ? 'border-primary/50 bg-primary-soft/30 shadow-sm dark:bg-primary/10'
                              : 'border-border bg-surface hover:border-border/80 hover:bg-surface-muted/40'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                toggleCandidate(cand.id)
                              }}
                              className="mt-1 text-primary"
                              aria-label={isSelected ? 'Deselect paper' : 'Select paper'}
                            >
                              {isSelected ? (
                                <CheckSquare size={19} className="text-primary" />
                              ) : (
                                <Square size={19} className="text-slate/40" />
                              )}
                            </button>

                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge tone={isArxiv ? 'violet' : 'teal'}>
                                  {isArxiv ? 'arXiv' : 'Semantic Scholar'}
                                </Badge>
                                {cand.year && (
                                  <span className="flex items-center gap-1 text-[11px] text-slate font-medium">
                                    <Calendar size={11} /> {cand.year}
                                  </span>
                                )}
                                {cand.relevance_score != null && (
                                  <span className="mono-label text-[10px] text-primary bg-primary-soft px-2 py-0.5 rounded-full font-bold">
                                    {(cand.relevance_score * 100).toFixed(0)}% Match
                                  </span>
                                )}
                              </div>

                              <h3 className="mt-2 font-display text-base font-bold text-ink hover:text-primary transition leading-snug">
                                {cand.title}
                              </h3>

                              {cand.authors && cand.authors.length > 0 && (
                                <p className="mt-1 flex items-center gap-1 text-xs text-slate truncate">
                                  <User size={12} className="shrink-0" />{' '}
                                  {cand.authors.slice(0, 4).join(', ')}
                                  {cand.authors.length > 4 ? ` et al.` : ''}
                                </p>
                              )}

                              {cand.abstract && (
                                <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate/85">
                                  {cand.abstract}
                                </p>
                              )}

                              <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-slate">
                                {(cand.doi || cand.arxiv_id) && (
                                  <span className="font-mono text-[10px] text-slate/70">
                                    ID: {cand.doi || cand.arxiv_id}
                                  </span>
                                )}
                                {cand.url && (
                                  <a
                                    href={cand.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="inline-flex items-center gap-1 text-primary hover:underline font-semibold"
                                  >
                                    View Source <ExternalLink size={11} />
                                  </a>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : hasSearched ? (
                <div className="py-16 text-center">
                  <Database size={32} className="mx-auto text-slate/40" />
                  <h3 className="mt-3 font-display text-xl font-semibold text-ink">
                    No online papers found
                  </h3>
                  <p className="mt-1 text-xs text-slate max-w-sm mx-auto">
                    Try broadening your search query or switching providers to find relevant research.
                  </p>
                </div>
              ) : (
                <div className="py-16 text-center">
                  <Sparkles size={32} className="mx-auto text-primary" />
                  <h3 className="mt-3 font-display text-xl font-semibold text-ink">
                    Discover New Knowledge
                  </h3>
                  <p className="mt-1 text-xs text-slate max-w-md mx-auto">
                    Enter a research question or topic above to find candidates from peer-reviewed
                    sources. You choose exactly which papers to download and ingest.
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Confirmation Modal Overlay: Ask every time */}
        <AnimatePresence>
          {isConfirmingIngest && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-30 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm rounded-3xl"
            >
              <div className="w-full max-w-lg rounded-3xl bg-surface p-6 sm:p-7 shadow-2xl border border-border dark:bg-[#10182c] dark:border-white/15">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-violet text-white shadow-sm">
                    <Database size={20} />
                  </div>
                  <div>
                    <h3 className="font-display text-2xl font-bold text-ink">
                      Choose Ingestion Target
                    </h3>
                    <p className="text-xs text-slate dark:text-slate-300">
                      {selectedIds.size} paper(s) selected from online discovery
                    </p>
                  </div>
                </div>

                <p className="mt-4 text-xs text-slate dark:text-slate-300 leading-relaxed">
                  Where would you like to ingest these papers? Lumina prompts you every time to ensure corpus accuracy:
                </p>

                {/* Target Options */}
                <div className="mt-3.5 space-y-2.5">
                  <div
                    onClick={() => setIngestionMode('permanent')}
                    className={cn(
                      'cursor-pointer rounded-2xl border p-3.5 transition-all',
                      ingestionMode === 'permanent'
                        ? 'border-primary bg-primary-soft/50 ring-2 ring-primary/20 dark:bg-blue-950/40 dark:border-blue-500/60'
                        : 'border-border bg-surface-muted/40 hover:border-primary/40 dark:bg-white/5 dark:border-white/10'
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary text-white text-xs">
                        <Database size={15} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <h4 className="text-xs font-bold text-ink">
                            Permanent Database (Global Corpus)
                          </h4>
                          <Badge tone="teal">Persistent</Badge>
                        </div>
                        <p className="mt-0.5 text-[11px] text-slate dark:text-slate-300 leading-relaxed">
                          Save into the permanent research database. Available for all future sessions, global searches, and cross-project analysis.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div
                    onClick={() => setIngestionMode('session_only')}
                    className={cn(
                      'cursor-pointer rounded-2xl border p-3.5 transition-all',
                      ingestionMode === 'session_only'
                        ? 'border-violet bg-violet-soft/50 ring-2 ring-violet/20 dark:bg-purple-950/40 dark:border-purple-500/60'
                        : 'border-border bg-surface-muted/40 hover:border-violet/40 dark:bg-white/5 dark:border-white/10'
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-violet text-white text-xs">
                        <Clock size={15} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <h4 className="text-xs font-bold text-ink">
                            Session Only (Temporary)
                          </h4>
                          <Badge tone="violet">Isolated</Badge>
                        </div>
                        <p className="mt-0.5 text-[11px] text-slate dark:text-slate-300 leading-relaxed">
                          Index strictly for your active research session. Does not affect the shared database.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Candidate list summary */}
                <div className="mt-3.5 max-h-28 overflow-y-auto rounded-xl border border-border bg-surface-muted/50 p-2.5 space-y-1 dark:bg-white/5 dark:border-white/10">
                  {candidates
                    .filter((c) => selectedIds.has(c.id))
                    .map((c) => (
                      <p key={c.id} className="text-[11px] font-semibold text-ink truncate">
                        • {c.title}
                      </p>
                    ))}
                </div>

                <div className="mt-5 flex justify-end gap-2 pt-2 border-t border-border dark:border-white/10">
                  <Button
                    variant="ghost"
                    onClick={() => setIsConfirmingIngest(false)}
                    disabled={isIngesting}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    onClick={handleConfirmAndIngest}
                    disabled={isIngesting}
                  >
                    {isIngesting ? (
                      <>
                        <LoaderCircle size={14} className="animate-spin" /> Ingesting...
                      </>
                    ) : (
                      'Confirm & Ingest Papers'
                    )}
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
