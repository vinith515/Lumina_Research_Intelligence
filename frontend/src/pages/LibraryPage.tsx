import { useState, useMemo } from 'react'
import { motion } from 'motion/react'
import {
  FileText,
  Search,
  Plus,
  ExternalLink,
  MessageSquare,
  Globe,
  Calendar,
  Layers,
} from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useResearch } from '../context/ResearchContext'
import type { PaperItem } from '../services/api'
import { Badge, Button, GlassCard, Pagination, SectionHeader, cn } from '../components/ui/Primitives'

type CategoryFilter = 'all' | 'baseline' | 'user' | 'online'

export function LibraryPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { papers, isLoadingPapers, setPaperIsolation, openPdfViewer, openOnlineDiscovery } =
    useResearch()

  const [query, setQuery] = useState('')
  const [tab, setTab] = useState<CategoryFilter>('all')
  const [sort, setSort] = useState<'title' | 'chunks'>('title')
  const [page, setPage] = useState(1)
  const perPage = 9

  const selectedDomain = searchParams.get('domain') || 'all'

  function setSelectedDomain(domain: string) {
    const next = new URLSearchParams(searchParams)
    if (domain === 'all') {
      next.delete('domain')
    } else {
      next.set('domain', domain)
    }
    setSearchParams(next)
    setPage(1)
  }

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim()
    return papers
      .filter((paper: PaperItem) => {
        if (selectedDomain !== 'all') {
          const domLower = selectedDomain.toLowerCase()
          const catLower = (paper.category || '').toLowerCase()
          if (!catLower.includes(domLower) && !domLower.includes(catLower)) {
            return false
          }
        }
        if (tab === 'baseline') return !paper.is_user_uploaded && paper.source === 'baseline_corpus'
        if (tab === 'user') return paper.is_user_uploaded && (paper.source === 'user_upload' || paper.category === 'User Uploaded')
        if (tab === 'online') return paper.source?.startsWith('online_') || paper.category === 'Online Research'
        return true
      })
      .filter((paper: PaperItem) => {
        if (!q) return true
        return (
          paper.title.toLowerCase().includes(q) ||
          paper.paper_id.toLowerCase().includes(q) ||
          (paper.category && paper.category.toLowerCase().includes(q))
        )
      })
      .sort((a: PaperItem, b: PaperItem) => {
        if (sort === 'chunks') {
          return (b.total_chunks || 0) - (a.total_chunks || 0)
        }
        return a.title.localeCompare(b.title)
      })
  }, [papers, query, tab, sort])

  const pageItems = filtered.slice((page - 1) * perPage, page * perPage)
  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage))

  function handleAskAboutPaper(paper: PaperItem) {
    setPaperIsolation(paper.paper_id, paper.title)
    navigate('/app/chat')
  }

  function handleOpenPdf(paper: PaperItem) {
    openPdfViewer({
      paperId: paper.paper_id,
      title: paper.title,
      page: 1,
    })
  }

  const baselineCount = papers.filter((p: PaperItem) => !p.is_user_uploaded).length
  const userCount = papers.filter((p: PaperItem) => p.is_user_uploaded && (p.source === 'user_upload' || p.category === 'User Uploaded')).length
  const onlineCount = papers.filter((p: PaperItem) => p.source?.startsWith('online_') || p.category === 'Online Research').length

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Corpus Index & Provenance"
        title="Research Library"
        description="Explore the multi-tier paper knowledge graph. Isolated across the pre-indexed peer-reviewed baseline corpus, custom session uploads, and dynamically imported online papers."
        action={
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={() => openOnlineDiscovery()}>
              <Globe size={15} /> Discover Online
            </Button>
            <Button variant="primary" onClick={() => navigate('/app/upload')}>
              <Plus size={15} /> Upload PDF
            </Button>
          </div>
        }
      />

      {/* Search & Filter Controls */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex w-full max-w-md items-center gap-2 rounded-full border border-border bg-surface px-4 shadow-xs dark:bg-[#10182c] dark:border-white/15">
          <Search size={16} className="text-slate dark:text-slate-400" />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setPage(1)
            }}
            placeholder="Search titles, paper IDs, topics..."
            className="h-11 min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-slate/60 dark:text-white dark:placeholder:text-slate-400"
          />
          {query && (
            <button onClick={() => setQuery('')} className="text-xs text-slate hover:text-ink dark:text-slate-300 dark:hover:text-white">
              Clear
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Category Tabs */}
          <div className="flex rounded-full bg-surface-muted p-1 dark:bg-white/5 border border-transparent dark:border-white/10">
            {[
              { id: 'all', label: `All (${papers.length})` },
              { id: 'baseline', label: `Baseline KB (${baselineCount})` },
              { id: 'user', label: `My Uploads (${userCount})` },
              { id: 'online', label: `Online Papers (${onlineCount})` },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  setTab(t.id as CategoryFilter)
                  setPage(1)
                }}
                className={cn(
                  'rounded-full px-3 py-1.5 text-xs font-semibold transition',
                  tab === t.id
                    ? 'bg-surface text-primary shadow-xs dark:bg-white/10 dark:text-blue-300'
                    : 'text-slate hover:text-ink dark:text-slate-300 dark:hover:text-white'
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as 'title' | 'chunks')}
            className="h-10 rounded-full border border-border bg-surface px-3 text-xs font-semibold text-ink outline-none shadow-xs dark:bg-[#10182c] dark:border-white/15 dark:text-white"
          >
            <option value="title" className="dark:bg-[#10182c]">Sort: Title A–Z</option>
            <option value="chunks" className="dark:bg-[#10182c]">Sort: Most Chunks</option>
          </select>
        </div>
      </div>

      {/* Core Domain Filter Chips */}
      <div className="flex flex-wrap items-center gap-2 pt-1 pb-2">
        <span className="mono-label text-[10px] text-slate dark:text-slate-400 font-bold mr-1">
          CORE DOMAIN:
        </span>
        {[
          { id: 'all', label: 'All Domains', icon: '🌐' },
          { id: 'ComputerVision', label: 'Computer Vision', icon: '👁️' },
          { id: 'DeepLearning', label: 'Deep Learning', icon: '🧠' },
          { id: 'GenerativeAI', label: 'Generative AI', icon: '✨' },
          { id: 'MachineLearning', label: 'Machine Learning', icon: '⚙️' },
          { id: 'NLP', label: 'NLP', icon: '💬' },
        ].map((d) => (
          <button
            key={d.id}
            type="button"
            onClick={() => setSelectedDomain(d.id)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition border cursor-pointer',
              selectedDomain.toLowerCase() === d.id.toLowerCase()
                ? 'border-primary bg-primary text-white shadow-xs dark:bg-blue-600 dark:border-blue-500'
                : 'border-border bg-surface text-slate hover:border-primary/40 hover:text-ink dark:bg-white/5 dark:border-white/10 dark:text-slate-300 dark:hover:text-white'
            )}
          >
            <span>{d.icon}</span>
            <span>{d.label}</span>
          </button>
        ))}
      </div>

      {/* Grid of Papers */}
      {isLoadingPapers ? (
        <div className="py-20 text-center">
          <p className="font-display text-2xl font-bold text-ink">Loading library papers...</p>
        </div>
      ) : pageItems.length === 0 ? (
        <GlassCard className="p-16 text-center">
          <p className="font-display text-3xl font-semibold text-ink">No research papers found</p>
          <p className="mt-2 text-sm text-slate">
            {tab !== 'all'
              ? `No papers in "${tab}" category match your query.`
              : 'Try clearing your query or uploading a new paper.'}
          </p>
          <Button
            variant="secondary"
            className="mt-6"
            onClick={() => {
              setQuery('')
              setTab('all')
            }}
          >
            Reset Filters
          </Button>
        </GlassCard>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {pageItems.map((paper: PaperItem, index: number) => {
            const isUser = paper.is_user_uploaded && (paper.source === 'user_upload' || paper.category === 'User Uploaded')
            const isOnline = paper.source?.startsWith('online_') || paper.category === 'Online Research'

            return (
              <motion.div
                key={paper.paper_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.03 }}
              >
                <GlassCard interactive className="flex h-full flex-col justify-between p-5">
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      <div
                        className={cn(
                          'flex h-11 w-11 shrink-0 items-center justify-center rounded-xl',
                          isUser
                            ? 'bg-teal-soft text-teal'
                            : isOnline
                            ? 'bg-violet-soft text-violet'
                            : 'bg-primary-soft text-primary'
                        )}
                      >
                        <FileText size={20} />
                      </div>

                      <Badge
                        tone={isUser ? 'teal' : isOnline ? 'violet' : 'primary'}
                      >
                        {isUser
                          ? 'User Upload'
                          : isOnline
                          ? 'Online Paper'
                          : 'Lumina KB'}
                      </Badge>
                    </div>

                    <h3
                      className="mt-4 line-clamp-2 font-display text-lg font-bold leading-snug text-ink dark:text-white"
                      title={paper.title}
                    >
                      {paper.title}
                    </h3>

                    <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate dark:text-slate-300 font-medium">
                      {paper.year && (
                        <span className="flex items-center gap-1">
                          <Calendar size={12} /> {paper.year}
                        </span>
                      )}
                      <span className="h-1 w-1 rounded-full bg-border dark:bg-white/20" />
                      <span>{paper.category || 'General'}</span>
                      {paper.total_chunks > 0 && (
                        <>
                          <span className="h-1 w-1 rounded-full bg-border dark:bg-white/20" />
                          <span className="flex items-center gap-1">
                            <Layers size={11} /> {paper.total_chunks} chunks
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="mt-5 flex items-center justify-between border-t border-border/80 dark:border-white/10 pt-4">
                    <button
                      onClick={() => handleOpenPdf(paper)}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-slate hover:text-primary dark:text-slate-300 dark:hover:text-blue-300 transition"
                    >
                      <ExternalLink size={13} /> View PDF
                    </button>

                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleAskAboutPaper(paper)}
                      className="text-xs"
                    >
                      <MessageSquare size={13} /> Ask Questions
                    </Button>
                  </div>
                </GlassCard>
              </motion.div>
            )
          })}
        </div>
      )}

      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} onChange={setPage} />
      )}
    </div>
  )
}
