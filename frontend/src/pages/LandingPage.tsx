import { motion } from 'motion/react'
import {
  ArrowRight,
  BookOpen,
  BrainCircuit,
  Check,
  ChevronRight,
  Globe,
  Layers,
  Menu,
  Moon,
  Search,
  ShieldCheck,
  Sparkles,
  Sun,
  UploadCloud,
  X,
  FileCheck2,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useState } from 'react'
import { Button, GlassCard, cn } from '../components/ui/Primitives'
import { useTheme } from '../context/ThemeContext'

const features = [
  {
    icon: UploadCloud,
    title: 'Dynamic PDF Ingestion',
    copy: 'Process full scientific papers with Unstructured.io document element parsing and structure-aware chunking.',
    tone: 'primary',
  },
  {
    icon: Search,
    title: 'Hybrid Dual-Index Retrieval',
    copy: 'ChromaDB dense vectors + BM25 sparse retrieval fused with Reciprocal Rank Fusion (RRF) and Cross-Encoder reranking.',
    tone: 'violet',
  },
  {
    icon: BrainCircuit,
    title: 'Scope-Aware Grounded Chat',
    copy: 'Target retrieval to a single paper, your session uploads, baseline peer-reviewed corpus, or external discoveries.',
    tone: 'teal',
  },
  {
    icon: ShieldCheck,
    title: 'Calibrated Abstention Engine',
    copy: 'Strictly grounded at operating threshold τ = 0.35. Eliminates unconstrained hallucinations by explicitly abstaining.',
    tone: 'amber',
  },
  {
    icon: Globe,
    title: 'Online Literature Discovery',
    copy: 'Directly search arXiv and Semantic Scholar to discover and ingest newly published scientific literature on demand.',
    tone: 'primary',
  },
  {
    icon: BookOpen,
    title: 'Pre-Indexed Baseline Corpus',
    copy: '316+ peer-reviewed papers with 48,600+ indexed chunks across multiple computer science disciplines.',
    tone: 'violet',
  },
]

const pillars = [
  {
    icon: Layers,
    title: 'Dual-Stage Retrieval Precision',
    description:
      'Sparse BM25 captures exact academic terminology, Dense BGE embeddings capture deep semantic intent, and MiniLM cross-encoders optimize top-k relevance.',
    metric: '90.0% HitRate@5',
  },
  {
    icon: ShieldCheck,
    title: '3-State Grounding Framework',
    description:
      'Categorizes answers into Strong Evidence, Partial Evidence with explicit gap disclosure, or Deterministic Abstention when literature is absent.',
    metric: '92.9% Selective Accuracy',
  },
  {
    icon: FileCheck2,
    title: 'Spatial PDF Evidence Lineage',
    description:
      'Click any citation in the synthesized response to open the interactive PDF reader with verbatim page and paragraph coordinates highlighted.',
    metric: '100% Provenance Trace',
  },
]

export function LandingPage() {
  const { mode, toggleMode } = useTheme()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-screen overflow-hidden bg-canvas text-ink">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-border/70 bg-canvas/75 backdrop-blur-xl">
        <div className="mx-auto flex h-[72px] max-w-[1320px] items-center justify-between px-5 sm:px-8">
          <Link to="/" className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-violet text-white shadow-xs">
              <Sparkles size={17} />
            </span>
            <span className="font-display text-2xl font-semibold tracking-tight text-ink">ResearchMind</span>
          </Link>
          <nav className="hidden items-center gap-8 text-sm text-slate lg:flex">
            <a href="#capabilities" className="transition hover:text-primary">
              Capabilities
            </a>
            <a href="#architecture" className="transition hover:text-primary">
              Architecture
            </a>
            <a href="#workflow" className="transition hover:text-primary">
              Workflow
            </a>
            <Link to="/login" className="transition hover:text-primary">
              Sign in
            </Link>
          </nav>
          <div className="flex items-center gap-2">
            <button
              className="flex h-10 w-10 items-center justify-center rounded-full text-slate transition hover:bg-primary-soft hover:text-primary dark:hover:bg-white/10"
              onClick={toggleMode}
              aria-label="Toggle theme"
            >
              {mode === 'light' ? <Moon size={17} /> : <Sun size={17} className="text-amber-400" />}
            </button>
            <Link to="/signup" className="hidden sm:block">
              <Button variant="primary" size="sm">
                Get started <ArrowRight size={15} />
              </Button>
            </Link>
            <button
              className="flex h-10 w-10 items-center justify-center rounded-full text-slate lg:hidden"
              onClick={() => setMenuOpen((open) => !open)}
              aria-label="Toggle menu"
            >
              {menuOpen ? <X size={19} /> : <Menu size={19} />}
            </button>
          </div>
        </div>
        {menuOpen && (
          <div className="border-t border-border bg-surface px-5 py-4 lg:hidden">
            <nav className="flex flex-col gap-3 text-sm text-slate">
              <a href="#capabilities" onClick={() => setMenuOpen(false)}>
                Capabilities
              </a>
              <a href="#architecture" onClick={() => setMenuOpen(false)}>
                Architecture
              </a>
              <a href="#workflow" onClick={() => setMenuOpen(false)}>
                Workflow
              </a>
              <Link to="/login">Sign in</Link>
              <Link to="/signup" className="font-semibold text-primary">
                Get started
              </Link>
            </nav>
          </div>
        )}
      </header>

      <main className="pt-[72px]">
        {/* Hero Section */}
        <section className="relative isolate px-5 pb-24 pt-24 sm:px-8 lg:pb-32 lg:pt-36">
          <div className="pointer-events-none absolute -right-20 top-20 -z-10 h-96 w-96 rounded-full bg-violet/10 blur-[100px]" />
          <div className="pointer-events-none absolute -left-24 top-64 -z-10 h-80 w-80 rounded-full bg-primary/10 blur-[100px]" />
          <div className="mx-auto grid max-w-[1320px] items-center gap-16 lg:grid-cols-[1.03fr_0.97fr]">
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/15 bg-primary-soft px-3 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-primary dark:bg-primary/20 dark:text-white">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal" />
                Explainable AI RAG for Scientific Literature
              </div>
              <h1 className="max-w-3xl font-display text-6xl font-semibold leading-[0.9] tracking-[-0.045em] text-ink sm:text-7xl lg:text-[88px]">
                Ground every claim in <span className="gradient-text">verifiable evidence.</span>
              </h1>
              <p className="mt-7 max-w-xl text-base leading-7 text-slate sm:text-lg">
                Lumina is an end-to-end scientific literature intelligence platform. Combining dual-index hybrid
                retrieval, strict abstention calibration, and interactive PDF spatial citations.
              </p>
              <div className="mt-9 flex flex-col gap-3 sm:flex-row">
                <Link to="/signup">
                  <Button variant="primary" size="lg">
                    Launch workspace <ArrowRight size={17} />
                  </Button>
                </Link>
                <Link to="/app/upload">
                  <Button variant="secondary" size="lg">
                    <UploadCloud size={17} /> Ingest a research PDF
                  </Button>
                </Link>
              </div>
              <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate">
                <span className="flex items-center gap-1.5">
                  <Check size={14} className="text-teal" /> Scope-isolated retrieval
                </span>
                <span className="flex items-center gap-1.5">
                  <Check size={14} className="text-teal" /> Zero hallucination tolerance
                </span>
                <span className="flex items-center gap-1.5">
                  <Check size={14} className="text-teal" /> PDF drawer synchronization
                </span>
              </div>
            </motion.div>

            {/* Interactive Hero Visual */}
            <motion.div
              className="relative mx-auto w-full max-w-[590px]"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.15, duration: 0.7 }}
            >
              <div className="absolute inset-8 rounded-[38px] bg-gradient-to-br from-primary/20 via-transparent to-violet/20 blur-3xl" />
              <GlassCard className="relative overflow-hidden rounded-[2rem] p-3 shadow-float">
                <div className="relative aspect-[0.95] overflow-hidden rounded-[1.5rem] bg-[#0e1730] p-5 text-white">
                  <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full border border-white/10 bg-primary/30 blur-2xl" />
                  <div className="absolute -bottom-12 -left-10 h-48 w-48 rounded-full bg-violet/30 blur-3xl" />
                  <div className="relative z-10 flex items-center justify-between">
                    <div>
                      <p className="mono-label text-white/50">Scientific Engine</p>
                      <p className="mt-1 text-sm font-semibold">Dual-Index Hybrid RRF (k=60)</p>
                    </div>
                    <span className="rounded-full border border-teal/30 bg-teal/10 px-2 py-1 text-[9px] font-bold uppercase tracking-widest text-teal">
                      System 2.0
                    </span>
                  </div>
                  <div className="relative mt-10 flex items-center justify-center">
                    <div className="absolute h-64 w-64 rounded-full border border-white/10" />
                    <div className="absolute h-44 w-44 rounded-full border border-white/10" />
                    <div className="absolute h-28 w-28 animate-pulse rounded-full bg-gradient-to-br from-[#3b82f6] to-[#8b5cf6] opacity-90 blur-sm" />
                    <div className="relative flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-primary to-violet shadow-[0_0_70px_rgba(85,90,255,0.75)]">
                      <Sparkles size={30} />
                    </div>
                    {[0, 1, 2, 3, 4].map((item) => (
                      <motion.span
                        key={item}
                        className="absolute h-2 w-2 rounded-full bg-white"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 8 + item, repeat: Infinity, ease: 'linear' }}
                        style={{ transform: `rotate(${item * 72}deg) translateY(-110px)` }}
                      />
                    ))}
                  </div>
                  <div className="relative mt-11 grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-white/10 bg-white/10 p-3 backdrop-blur">
                      <p className="text-[10px] text-white/50">Baseline Papers</p>
                      <p className="mt-1 font-display text-3xl">316+</p>
                      <div className="mt-2 h-1 rounded-full bg-white/10">
                        <div className="h-full w-4/5 rounded-full bg-teal" />
                      </div>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-white/10 p-3 backdrop-blur">
                      <p className="text-[10px] text-white/50">Indexed Chunks</p>
                      <p className="mt-1 font-display text-3xl">48.6k</p>
                      <p className="mt-2 text-[10px] text-teal">ChromaDB + BM25</p>
                    </div>
                  </div>
                </div>
              </GlassCard>
              <div className="absolute -bottom-5 -left-5 flex items-center gap-3 rounded-2xl border border-border bg-surface px-4 py-3 shadow-float">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-soft text-teal">
                  <ShieldCheck size={17} />
                </span>
                <div>
                  <p className="text-xs font-bold text-ink">Strict Evidence State</p>
                  <p className="text-[10px] text-slate">Calibrated at τ = 0.35</p>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* Capabilities Section */}
        <section id="capabilities" className="border-y border-border bg-surface/60 px-5 py-24 sm:px-8 lg:py-32">
          <div className="mx-auto max-w-[1320px]">
            <div className="max-w-xl">
              <p className="mono-label mb-3 text-primary">Core Capabilities</p>
              <h2 className="font-display text-5xl font-semibold leading-[0.95] text-ink sm:text-6xl">
                Engineered for rigorous scientific inquiry.
              </h2>
              <p className="mt-5 text-base leading-7 text-slate">
                Designed to eliminate hallucinations, preserve citation lineage, and synthesize complex literature with
                explainability.
              </p>
            </div>
            <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {features.map(({ icon: Icon, title, copy, tone }, index) => (
                <motion.div
                  key={title}
                  initial={{ opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ delay: index * 0.04 }}
                >
                  <GlassCard interactive className="h-full p-6">
                    <div
                      className={cn(
                        'mb-7 flex h-11 w-11 items-center justify-center rounded-2xl',
                        tone === 'primary' && 'bg-primary-soft text-primary dark:bg-primary/20',
                        tone === 'violet' && 'bg-violet-soft text-violet dark:bg-violet-900/20',
                        tone === 'teal' && 'bg-teal-soft text-teal dark:bg-teal-900/20',
                        tone === 'amber' && 'bg-amber-soft text-amber dark:bg-amber-900/20'
                      )}
                    >
                      <Icon size={20} />
                    </div>
                    <h3 className="font-display text-3xl font-semibold text-ink">{title}</h3>
                    <p className="mt-3 text-sm leading-6 text-slate">{copy}</p>
                    <Link to="/app" className="mt-7 flex items-center gap-2 text-xs font-bold text-primary">
                      Explore in workspace <ChevronRight size={14} />
                    </Link>
                  </GlassCard>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Scientific Architecture Section */}
        <section id="architecture" className="bg-[#0e1730] px-5 py-24 text-white sm:px-8 lg:py-32">
          <div className="mx-auto max-w-[1320px]">
            <div className="flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
              <div>
                <p className="mono-label mb-3 text-[#86a8ff]">Empirical Architecture</p>
                <h2 className="max-w-xl font-display text-5xl font-semibold leading-[0.95] sm:text-6xl">
                  Built on rigorous evaluation benchmarks.
                </h2>
              </div>
              <p className="max-w-sm text-sm leading-6 text-white/55">
                Evaluated across 75 benchmark queries, 9 query topologies, and multi-stage score traces.
              </p>
            </div>
            <div className="mt-14 grid gap-6 lg:grid-cols-3">
              {pillars.map((pillar) => {
                const Icon = pillar.icon
                return (
                  <GlassCard key={pillar.title} className="border-white/10 bg-white/5 p-6 text-white">
                    <div className="flex items-center justify-between">
                      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-violet-300">
                        <Icon size={20} />
                      </span>
                      <span className="rounded-full bg-teal/20 px-2.5 py-1 text-xs font-bold text-teal">
                        {pillar.metric}
                      </span>
                    </div>
                    <h3 className="mt-6 font-display text-2xl font-semibold">{pillar.title}</h3>
                    <p className="mt-3 text-xs leading-6 text-white/60">{pillar.description}</p>
                  </GlassCard>
                )
              })}
            </div>
          </div>
        </section>

        {/* Workflow Section */}
        <section id="workflow" className="px-5 py-24 sm:px-8 lg:py-32">
          <div className="mx-auto max-w-[1320px]">
            <div className="text-center">
              <p className="mono-label mb-3 text-primary">Pipeline Workflow</p>
              <h2 className="font-display text-5xl font-semibold leading-[0.95] text-ink sm:text-6xl">
                From raw PDF to verifiable synthesis.
              </h2>
            </div>
            <div className="relative mt-16 grid gap-6 md:grid-cols-4">
              {[
                { title: 'Upload PDF', copy: 'Unstructured.io extracts titles, narratives, tables, and formula elements.' },
                { title: 'Dual Indexing', copy: 'Dense ChromaDB vectors and BM25 sparse index built in real-time.' },
                { title: 'Scope-Aware Query', copy: 'Isolate queries to single papers, session uploads, or baseline corpus.' },
                { title: 'Grounded Answer', copy: 'Verbatim citations with interactive PDF drawer highlighting exact coordinates.' },
              ].map((step, index) => (
                <motion.div
                  key={step.title}
                  className="relative"
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                >
                  <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-primary/15 bg-primary-soft font-display text-2xl font-semibold text-primary dark:bg-primary/20 dark:text-white">
                    0{index + 1}
                  </div>
                  <h3 className="font-display text-3xl font-semibold text-ink">{step.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate">{step.copy}</p>
                  {index < 3 && (
                    <ArrowRight className="absolute right-4 top-5 hidden text-border md:block" size={20} />
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Call to action */}
        <section className="px-5 py-24 sm:px-8 lg:py-32">
          <div className="relative mx-auto max-w-[1320px] overflow-hidden rounded-[2rem] bg-gradient-to-br from-primary to-violet px-6 py-16 text-center text-white sm:px-12">
            <div className="absolute -left-10 -top-20 h-60 w-60 rounded-full bg-white/10 blur-3xl" />
            <div className="relative">
              <p className="mono-label mb-3 text-white/60">Ready to Explore</p>
              <h2 className="mx-auto max-w-2xl font-display text-5xl font-semibold leading-[0.92] sm:text-6xl">
                Start querying your scientific corpus today.
              </h2>
              <p className="mx-auto mt-5 max-w-xl text-sm leading-6 text-white/70">
                Experience high-integrity scientific question answering with citations you can always verify.
              </p>
              <Link to="/app" className="mt-8 inline-flex">
                <Button variant="secondary" size="lg" className="border-0 bg-white text-primary hover:bg-white/90">
                  Open Lumina Workspace <ArrowRight size={17} />
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border px-5 py-10 sm:px-8">
        <div className="mx-auto flex max-w-[1320px] flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-violet text-white shadow-xs">
                <Sparkles size={15} />
              </span>
              <span className="font-display text-2xl font-semibold text-ink">ResearchMind</span>
            </div>
            <p className="mt-3 max-w-xs text-xs leading-5 text-slate">
              Explainable AI Retrieval-Augmented Generation for Scientific Literature.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-x-12 gap-y-3 text-xs text-slate sm:flex">
            <a href="#capabilities" className="hover:text-primary">
              Capabilities
            </a>
            <a href="#architecture" className="hover:text-primary">
              Architecture
            </a>
            <a href="#workflow" className="hover:text-primary">
              Workflow
            </a>
            <Link to="/login" className="hover:text-primary">
              Sign in
            </Link>
          </div>
          <p className="text-[10px] text-slate">© 2026 Lumina · Dynamic Grounded RAG Platform</p>
        </div>
      </footer>
    </div>
  )
}
