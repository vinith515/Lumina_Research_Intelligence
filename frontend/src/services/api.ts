import axios from 'axios'

// ---------------------------------------------------------
// TypeScript Schemas aligned with FastAPI Backend
// ---------------------------------------------------------

export type KnowledgeScope =
  | 'this_paper'
  | 'user_papers'
  | 'global'
  | 'global_plus_user'
  | 'global_plus_user_plus_online'

export interface ScopeDefinition {
  id: KnowledgeScope
  label: string
  description: string
  color: string
}

export type IngestionJobStage =
  | 'PENDING'
  | 'DOWNLOADING'
  | 'DOWNLOADED'
  | 'PARSING'
  | 'CHUNKING'
  | 'EMBEDDING'
  | 'INDEXING'
  | 'COMPLETED'
  | 'FAILED'

export interface ViewerReference {
  paper_id?: string
  page: number
  page_number: number
  text: string
  snippet: string
  bbox?: number[][] | null
}

export interface CitationScoreBreakdown {
  dense_score?: number | null
  dense_rank?: number | null
  bm25_score?: number | null
  bm25_rank?: number | null
  rrf_score?: number | null
  rrf_rank?: number | null
  reranker_score?: number | null
  reranker_rank?: number | null
  final_confidence: number
  section_boost_applied?: number | null
}

export interface ComponentQualityAssessment {
  gemini_availability: string
  citation_generation: string
  target_paper_relevance: string
  methodology_extraction: string
  cross_paper_contamination: string
  overall_answer_quality: string
}

export interface ClaimExplanation {
  claim: string
  claim_index: number
  is_grounded: boolean
  is_supported_by_passage: boolean
  answers_question: boolean
  belongs_to_target_paper: boolean
  supporting_chunk_ids: string[]
  evidence_strength: string
  rationale: string
  verification_method: string
}

export interface GroundingAssessment {
  total_claims: number
  supported_claims: number
  unsupported_claims: number
  contradicted_claims: number
  grounded_ratio: number
  evidence_strength_overall: string
  verification_method: string
  hallucination_warning?: string | null
  target_paper_id?: string | null
  target_paper_title?: string | null
  component_assessment?: ComponentQualityAssessment | null
}

export interface XAIExplanation {
  query: string
  retrieval_explanation: Record<string, any>
  final_evidence: any[]
  claim_explanations: ClaimExplanation[]
  grounding: GroundingAssessment
  evidence_strength: string
  evidence_state: string
  abstained: boolean
  faithfulness_score: number
  retrieval_funnel: {
    total_corpus_chunks?: number
    dense_candidates_retrieved?: number
    sparse_candidates_retrieved?: number
    fused_candidates_evaluated?: number
    final_verified_passages?: number
    pruning_ratio?: string
    [key: string]: any
  }
  contrastive_insights: string[]
  citation_rationales: Record<string, string>
}

export interface StructuredCitation {
  citation_id: string
  paper_id: string
  title: string
  authors: string[]
  page_start: number
  page_end: number
  section: string
  subsection?: string | null
  chunk_id: string
  retrieval_score: number
  retrieval_method: string
  snippet: string
  scope: string
  source: string
  viewer_reference?: ViewerReference | null
  score_breakdown?: CitationScoreBreakdown | null
  selection_rationale?: string
  matched_keywords?: string[]
  supported_claims?: number[]
}

export interface SourceChunk {
  chunk_id: string
  paper_id: string
  title: string
  authors: string[]
  section: string
  subsection?: string | null
  page_start: number
  page_end: number
  text: string
  scope: string
  source: string
  final_score?: number
  reranker_score?: number
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
  target_paper_id?: string | null
  target_paper_title?: string | null
}

export interface QueryApiRequest {
  query: string
  knowledge_scope?: KnowledgeScope
  scope_paper_ids?: string[]
  session_id?: string
  user_email?: string
  top_k?: number
  retrieval_mode?: string
  conversation_history?: ChatHistoryMessage[]
}

export interface HistoryQueryItem {
  id: string
  type: 'query'
  user_email: string
  session_id?: string | null
  query: string
  answer: string
  evidence_state: string
  knowledge_scope: string
  retrieval_mode: string
  target_paper_title?: string | null
  latency_ms: number
  abstained: boolean
  citations_count: number
  citations: StructuredCitation[]
  sources: SourceChunk[]
  created_at: string
}

export interface HistoryUploadItem {
  id: string
  type: 'upload'
  user_email: string
  session_id?: string | null
  job_id: string
  paper_id?: string | null
  filename: string
  title: string
  ingestion_mode: string
  status: string
  total_pages: number
  total_chunks: number
  created_at: string
}

export type HistoryItem = HistoryQueryItem | HistoryUploadItem

export interface UserStatsResponse {
  total_queries: number
  total_uploads: number
  total_citations: number
  evidence_distribution: {
    STATE_A: number
    STATE_B: number
    STATE_C: number
  }
  scopes_distribution: Record<string, number>
}

export interface UserHistoryResponse {
  user_email: string
  total_items: number
  items: HistoryItem[]
  stats: UserStatsResponse
}

export interface QueryApiResponse {
  query: string
  answer: string
  retrieval_mode: string
  evidence_state: string
  abstained: boolean
  target_paper_id?: string | null
  target_paper_title?: string | null
  needs_clarification: boolean
  knowledge_scope: KnowledgeScope
  scope_paper_ids: string[]
  online_search_suggested: boolean
  suggested_query?: string | null
  sources: SourceChunk[]
  structured_citations: StructuredCitation[]
  latency_ms: number
  faithfulness_score?: number | null
  xai_explanation?: XAIExplanation | null
  component_assessment?: ComponentQualityAssessment | null
}

export interface UploadPaperResponse {
  job_id: string
  status: IngestionJobStage
  file_name: string
  message: string
}

export interface IngestionJob {
  job_id: string
  paper_id?: string | null
  title?: string | null
  filename?: string | null
  file_name: string
  file_path?: string | null
  source: string
  scope: string
  session_id?: string | null
  status: IngestionJobStage
  progress_percent: number
  progress_pct?: number
  status_message: string
  current_stage: string
  total_pages: number
  total_chunks: number
  chunk_count: number
  created_at: string
  updated_at: string
  error?: string | null
  error_message?: string | null
}

export interface OnlinePaperCandidate {
  id: string
  candidate_id?: string
  title: string
  authors: string[]
  year?: number | null
  abstract?: string | null
  source_provider: 'arxiv' | 'semantic_scholar' | string
  source?: string
  identifier?: string
  doi?: string | null
  arxiv_id?: string | null
  semantic_scholar_id?: string | null
  url?: string | null
  pdf_url?: string | null
  relevance_score?: number | null
  isSelected?: boolean
}

export interface SearchOnlineRequest {
  query: string
  provider?: 'all' | 'arxiv' | 'semantic_scholar'
  max_results?: number
}

export interface SearchOnlineResponse {
  query: string
  provider: string
  candidates_count: number
  candidates: OnlinePaperCandidate[]
}

export interface IngestOnlineResponse {
  message: string
  jobs: Array<{
    job_id: string
    title: string
    file_name: string
    status: string
  }>
}

export interface PaperItem {
  paper_id: string
  title: string
  filename: string
  category: string
  total_pages: number
  total_chunks: number
  year?: number | null
  scope: string
  source: string
  is_user_uploaded: boolean
  session_id?: string | null
}

export interface ListPapersResponse {
  total_papers: number
  papers: PaperItem[]
}

export interface HealthResponse {
  status: string
  service: string
  version: string
  baseline_papers_count: number
  total_ingestion_jobs: number
  scopes: string[]
}

// ---------------------------------------------------------
// Axios Instance & Configuration
// ---------------------------------------------------------

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120000, // 2 minutes for LLM generation or indexing
  headers: {
    'Content-Type': 'application/json',
  },
})

// ---------------------------------------------------------
// API Client Functions
// ---------------------------------------------------------

export async function getHealth(): Promise<HealthResponse> {
  const res = await api.get<HealthResponse>('/health')
  return res.data
}

export async function getScopes(): Promise<ScopeDefinition[]> {
  const res = await api.get<ScopeDefinition[]>('/scopes')
  return res.data
}

export async function executeQuery(req: QueryApiRequest): Promise<QueryApiResponse> {
  const res = await api.post<QueryApiResponse>('/query', req)
  return res.data
}

export async function uploadPaper(
  file: File,
  sessionId: string = 'default_user',
  ingestionMode: 'permanent' | 'session_only' = 'permanent',
  userEmail?: string
): Promise<UploadPaperResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('session_id', sessionId)
  formData.append('ingestion_mode', ingestionMode)
  if (userEmail) {
    formData.append('user_email', userEmail)
  }
  const res = await api.post<UploadPaperResponse>('/papers/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function getIngestionStatus(jobId: string): Promise<IngestionJob> {
  const res = await api.get<IngestionJob>(`/ingestion/${encodeURIComponent(jobId)}`)
  return res.data
}

export async function listIngestionJobs(sessionId?: string): Promise<IngestionJob[]> {
  const params = sessionId ? { session_id: sessionId } : {}
  const res = await api.get<IngestionJob[]>('/ingestion', { params })
  return res.data
}

export async function searchOnlinePapers(
  query: string,
  provider: 'all' | 'arxiv' | 'semantic_scholar' = 'all',
  maxResults: number = 6
): Promise<SearchOnlineResponse> {
  const res = await api.post<SearchOnlineResponse>('/papers/search-online', {
    query,
    provider,
    max_results: maxResults,
  })
  if (res.data && Array.isArray(res.data.candidates)) {
    res.data.candidates = res.data.candidates.map((c: any) => ({
      ...c,
      id: c.id || c.candidate_id || c.identifier || `cand_${Math.random().toString(36).substring(2, 9)}`,
      candidate_id: c.candidate_id || c.id || '',
      source_provider: c.source_provider || c.source || 'arxiv',
      source: c.source || c.source_provider || 'arxiv',
    }))
  }
  return res.data
}

export async function ingestOnlinePapers(
  candidates: OnlinePaperCandidate[],
  sessionId: string = 'default_user',
  ingestionMode: 'permanent' | 'session_only' = 'permanent'
): Promise<IngestOnlineResponse> {
  const res = await api.post<IngestOnlineResponse>('/papers/ingest-online', {
    candidates,
    session_id: sessionId,
    ingestion_mode: ingestionMode,
  })
  return res.data
}

export async function listPapers(sessionId?: string): Promise<ListPapersResponse> {
  const params = sessionId ? { session_id: sessionId } : {}
  const res = await api.get<ListPapersResponse>('/papers', { params })
  return res.data
}

export function getPaperPdfUrl(paperId: string, page?: number): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
  const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl
  const url = `${cleanBase}/papers/${encodeURIComponent(paperId)}/pdf`
  return page ? `${url}#page=${page}` : url
}

// ---------------------------------------------------------
// User Profile & History API Endpoints
// ---------------------------------------------------------

export async function syncUser(user: {
  email: string
  name: string
  institution?: string
  role?: string
}): Promise<{ status: string; user: any }> {
  const res = await api.post('/user/sync', user)
  return res.data
}

export async function getUserHistory(
  userEmail: string,
  params?: {
    type?: 'all' | 'queries' | 'uploads'
    search?: string
    limit?: number
    offset?: number
  }
): Promise<UserHistoryResponse> {
  const res = await api.get<UserHistoryResponse>('/user/history', {
    params: {
      user_email: userEmail,
      type: params?.type || 'all',
      search: params?.search || undefined,
      limit: params?.limit || 50,
      offset: params?.offset || 0,
    },
  })
  return res.data
}

export async function getHistoryItem(
  historyId: string,
  userEmail?: string
): Promise<HistoryItem> {
  const res = await api.get<HistoryItem>(`/user/history/${encodeURIComponent(historyId)}`, {
    params: userEmail ? { user_email: userEmail } : {},
  })
  return res.data
}

export async function deleteHistoryItem(
  historyId: string,
  userEmail: string
): Promise<{ status: string; id: string }> {
  const res = await api.delete(`/user/history/${encodeURIComponent(historyId)}`, {
    params: { user_email: userEmail },
  })
  return res.data
}

export async function clearUserHistory(
  userEmail: string,
  type: 'all' | 'queries' | 'uploads' = 'all'
): Promise<{ status: string; user_email: string; type: string }> {
  const res = await api.delete('/user/history', {
    params: { user_email: userEmail, type },
  })
  return res.data
}

export async function getUserStats(userEmail: string): Promise<UserStatsResponse> {
  const res = await api.get<UserStatsResponse>('/user/stats', {
    params: { user_email: userEmail },
  })
  return res.data
}

