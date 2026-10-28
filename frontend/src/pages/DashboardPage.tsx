import { useState, useEffect } from 'react'
import { motion } from 'motion/react'
import {
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Sparkles,
  UploadCloud,
  Globe,
  Database,
  Cpu,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useResearch } from '../context/ResearchContext'
import { useAuth } from '../context/AuthContext'
import { getHealth, getUserHistory, type HealthResponse, type PaperItem, type HistoryItem } from '../services/api'
import { Button, GlassCard, Badge, SectionHeader } from '../components/ui/Primitives'

export function DashboardPage() {
  const navigate = useNavigate()
  const { papers, openOnlineDiscovery } = useResearch()
  const { user, displayName } = useAuth()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [recentHistory, setRecentHistory] = useState<HistoryItem[]>([])

  useEffect(() => {
    getHealth()
      .then((data: HealthResponse) => setHealth(data))
      .catch((err: unknown) => console.warn('Could not fetch backend health:', err))

    if (user?.email) {
      getUserHistory(user.email, { limit: 3 })
        .then((res) => setRecentHistory(res.items || []))
        .catch((err) => console.warn('Could not fetch recent history:', err))
    }
  }, [user?.email])

  const baselineCount = health?.baseline_papers_count ?? papers.filter((p: PaperItem) => !p.is_user_uploaded).length
  const userUploadsCount = papers.filter((p: PaperItem) => p.is_user_uploaded).length

  return (
    <div className="space-y-10">
      <SectionHeader
        eyebrow="Lumina Intelligence Workspace"
        title={displayName ? `Welcome back, ${displayName}` : 'Welcome to Lumina'}
        description="A multi-tier research-paper RAG platform powered by Unstructured document extraction, SciBERT embeddings, hybrid FAISS + BM25 retrieval, and Gemini reasoning."
        action={
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={() => openOnlineDiscovery()}>
              <Globe size={15} /> Discover Online
            </Button>
            <Link to="/app/upload">
              <Button variant="primary">
                <UploadCloud size={16} /> Upload Papers
              </Button>
            </Link>
          </div>
        }
      />

      {/* Hero Intelligence Banner */}
      <section className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-[#091124] via-[#0f1d40] to-[#181333] p-6 text-white shadow-float sm:p-8 border border-white/10 dark:border-white/15">
        <div className="absolute -right-16 -top-20 h-64 w-64 rounded-full bg-primary/40 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 left-1/2 h-48 w-48 rounded-full bg-violet/30 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-white/90">
              <Sparkles size={13} className="text-[#f4c96d]" /> Grounded Scientific Intelligence
            </div>
            <h2 className="max-w-2xl font-display text-4xl font-semibold leading-[0.96] text-white sm:text-5xl">
              {papers.length > 0 ? `${papers.length} peer-reviewed papers` : '316+ peer-reviewed papers'} indexed and ready.
            </h2>
            <p className="mt-4 max-w-xl text-sm leading-6 text-white/80">
              ResearchMind prevents hallucinations by strictly constraining answers to verbatim retrieved citations
              and spatial PDF coordinates across our 5 specialized AI research domains.
            </p>

            {/* Core Domain Badges */}
            <div className="mt-5 flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold text-white/70 uppercase tracking-wider mr-1">
                Core Domains:
              </span>
              {[
                { name: 'Computer Vision', count: 80, id: 'ComputerVision', icon: '👁️' },
                { name: 'Deep Learning', count: 73, id: 'DeepLearning', icon: '🧠' },
                { name: 'Generative AI', count: 66, id: 'GenerativeAI', icon: '✨' },
                { name: 'Machine Learning', count: 48, id: 'MachineLearning', icon: '⚙️' },
                { name: 'NLP', count: 49, id: 'NLP', icon: '💬' },
              ].map((domain) => (
                <button
                  key={domain.id}
                  onClick={() => navigate(`/app/library?domain=${domain.id}`)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold text-white backdrop-blur transition hover:bg-white/25 hover:border-white/40 cursor-pointer"
                  title={`Explore ${domain.count} papers in ${domain.name}`}
                >
                  <span>{domain.icon}</span>
                  <span>{domain.name}</span>
                  <span className="rounded-full bg-white/20 px-1.5 py-0.2 text-[10px] font-mono text-white/90">
                    {domain.count}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:w-[320px]">
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
              <p className="font-display text-3xl font-bold text-white">{baselineCount}</p>
              <p className="mt-1 text-[10px] uppercase tracking-wider text-white/70">Baseline Corpus</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
              <p className="font-display text-3xl font-bold text-white">{userUploadsCount}</p>
              <p className="mt-1 text-[10px] uppercase tracking-wider text-white/70">Session Uploads</p>
            </div>
          </div>
        </div>
      </section>

      {/* Quick Action Navigation */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="mono-label text-primary">Core Workflows</p>
            <h2 className="mt-1 font-display text-3xl font-semibold text-ink">Action Center</h2>
          </div>
          <Link to="/app/chat" className="text-xs font-semibold text-primary">
            Open Chat Console <ArrowUpRight size={14} className="inline" />
          </Link>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {[
            {
              label: 'Grounded AI Chat',
              copy: 'Ask complex research questions with clickable citations and PDF sync.',
              icon: Bot,
              to: '/app/chat',
              tone: 'primary',
            },
            {
              label: 'Upload Research PDF',
              copy: 'Ingest private papers into session-isolated FAISS and BM25 indices.',
              icon: UploadCloud,
              to: '/app/upload',
              tone: 'violet',
            },
            {
              label: 'Online Paper Discovery',
              copy: 'Search arXiv & Semantic Scholar to ingest external literature on demand.',
              icon: Globe,
              action: () => openOnlineDiscovery(),
              tone: 'teal',
            },
          ].map(({ label, copy, icon: Icon, to, tone, action }, index) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08 }}
            >
              {to ? (
                <Link to={to} className="group block h-full">
                  <GlassCard interactive className="flex h-full items-start gap-4 p-5">
                    <span
                      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${
                        tone === 'primary'
                          ? 'bg-primary-soft text-primary'
                          : tone === 'violet'
                          ? 'bg-violet-soft text-violet'
                          : 'bg-teal-soft text-teal'
                      }`}
                    >
                      <Icon size={20} />
                    </span>
                    <span>
                      <span className="block font-display text-2xl font-semibold text-ink transition group-hover:text-primary">
                        {label}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-slate">{copy}</span>
                    </span>
                    <ArrowUpRight
                      size={16}
                      className="ml-auto text-slate transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary"
                    />
                  </GlassCard>
                </Link>
              ) : (
                <button onClick={action} className="group block h-full w-full text-left">
                  <GlassCard interactive className="flex h-full items-start gap-4 p-5">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-teal-soft text-teal">
                      <Icon size={20} />
                    </span>
                    <span>
                      <span className="block font-display text-2xl font-semibold text-ink transition group-hover:text-primary">
                        {label}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-slate">{copy}</span>
                    </span>
                    <ArrowUpRight
                      size={16}
                      className="ml-auto text-slate transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary"
                    />
                  </GlassCard>
                </button>
              )}
            </motion.div>
          ))}
        </div>
      </section>

      {/* Recent Research History Section */}
      {recentHistory.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="mono-label text-primary">Audit Trail</p>
              <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Recent Research History</h2>
            </div>
            <Link to="/app/history" className="text-xs font-semibold text-primary hover:underline">
              View all history <ArrowUpRight size={14} className="inline" />
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {recentHistory.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  if (item.type === 'query') {
                    navigate('/app/chat', { state: { initialQuery: (item as any).query } })
                  } else {
                    navigate('/app/history')
                  }
                }}
                className="cursor-pointer group"
              >
                <GlassCard
                  interactive
                  className="p-4 transition hover:shadow-md h-full"
                >
                  <div className="flex items-center justify-between">
                    <Badge tone={item.type === 'query' ? 'primary' : 'violet'}>
                      {item.type === 'query' ? 'Research Q&A' : 'Paper Upload'}
                    </Badge>
                    <span className="text-[10px] text-slate">{item.created_at.split(' ')[0]}</span>
                  </div>
                  <h4 className="mt-2 line-clamp-2 font-display text-sm font-bold text-ink transition group-hover:text-primary dark:text-white">
                    {item.type === 'query' ? (item as any).query : (item as any).title || (item as any).filename}
                  </h4>
                  <p className="mt-1 line-clamp-2 text-xs text-slate">
                    {item.type === 'query'
                      ? (item as any).answer.replace(/[#*`_]/g, '')
                      : `Ingested to ${(item as any).ingestion_mode} corpus.`}
                  </p>
                </GlassCard>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Status & Telemetry Grid */}
      <section className="grid gap-4 sm:grid-cols-3">
        <GlassCard className="flex items-center gap-3 p-4">
          <CheckCircle2 className="text-teal" size={18} />
          <div>
            <p className="text-xs font-bold text-ink">
              Backend API {health?.status === 'healthy' ? 'Operational' : 'Ready'}
            </p>
            <p className="text-[10px] text-slate">FastAPI 2.0 on 127.0.0.1:8000</p>
          </div>
        </GlassCard>

        <GlassCard className="flex items-center gap-3 p-4">
          <Cpu className="text-primary" size={18} />
          <div>
            <p className="text-xs font-bold text-ink">SciBERT + Cross-Encoder</p>
            <p className="text-[10px] text-slate">Dense embeddings & semantic reranking</p>
          </div>
        </GlassCard>

        <GlassCard className="flex items-center gap-3 p-4">
          <Database className="text-violet" size={18} />
          <div>
            <p className="text-xs font-bold text-ink">FAISS Vector Index</p>
            <p className="text-[10px] text-slate">Cosine similarity + BM25 reciprocal rank fusion</p>
          </div>
        </GlassCard>
      </section>
    </div>
  )
}
