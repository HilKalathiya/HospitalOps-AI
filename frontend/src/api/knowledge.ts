/**
 * HospitalOps AI — Hospital Knowledge & RAG Ingestion API Client (Chunk 4.1).
 *
 * Types and API client for document management, multi-format ingestion,
 * stage-by-stage pipeline telemetry, vector chunk inspection, and version control.
 */

import { apiClient } from './client'

export type DocumentCategory =
  | 'POLICY'
  | 'SOP'
  | 'CLINICAL_PROTOCOL'
  | 'EQUIPMENT_MANUAL'
  | 'INFECTION_CONTROL'
  | 'ADMINISTRATIVE'
  | 'CAPACITY_PLANNING'
  | 'GENERAL_REFERENCE'

export type AccessLevel = 'PUBLIC' | 'INTERNAL' | 'RESTRICTED' | 'CONFIDENTIAL'

export type IngestionStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'QUARANTINED'

export type IngestionStage =
  | 'DOCUMENT_INPUT'
  | 'FILE_VALIDATION'
  | 'DOCUMENT_EXTRACTION'
  | 'CONTENT_CLEANING'
  | 'METADATA_EXTRACTION'
  | 'DOCUMENT_CHUNKING'
  | 'PRIVACY_VALIDATION'
  | 'EMBEDDING_GENERATION'
  | 'VECTOR_INDEXING'
  | 'COMPLETED'

export interface StageTelemetry {
  stage: IngestionStage
  status: 'success' | 'failed' | 'skipped'
  duration_ms: number
  details?: Record<string, unknown>
  error?: string | null
}

export interface IngestionRun {
  ingestion_id: string
  document_id: string
  version: number
  status: IngestionStatus
  current_stage: IngestionStage
  stages: StageTelemetry[]
  chunks_produced: number
  tokens_produced: number
  embeddings_generated: number
  error_message?: string | null
  initiated_by: string
  created_at: string
  completed_at?: string | null
  total_duration_ms?: number | null
}

export interface DocumentVersion {
  version_id: string
  document_id: string
  version: number
  content_hash: string
  file_path: string
  file_size_bytes: number
  chunk_count: number
  total_tokens: number
  status: IngestionStatus
  is_active: boolean
  created_by: string
  change_summary?: string | null
  created_at: string
}

export interface DocumentSummary {
  document_id: string
  title: string
  category: DocumentCategory
  access_level: AccessLevel
  tags: string[]
  department_id?: string | null
  active_version: number
  file_type: string
  file_size_bytes: number
  source_filename: string
  status: IngestionStatus
  total_chunks: number
  total_tokens: number
  is_quarantined: boolean
  quarantine_reason?: string | null
  created_by: string
  created_at: string
  updated_at: string
}

export interface DocumentDetail extends DocumentSummary {
  description?: string | null
  author?: string | null
  versions: DocumentVersion[]
  latest_ingestion_run?: IngestionRun | null
}

export interface DocumentChunk {
  chunk_id: string
  document_id: string
  version: number
  chunk_index: number
  text: string
  section_title?: string | null
  page_number?: number | null
  token_count: number
  char_count: number
  is_table: boolean
}

export interface DocumentChunksResponse {
  document_id: string
  version: number
  total_chunks: number
  chunks: DocumentChunk[]
}

export interface DocumentUploadResponse {
  document_id: string
  version: number
  title: string
  status: IngestionStatus
  is_duplicate: boolean
  chunks_count: number
  total_tokens: number
  ingestion_id: string
  message: string
}

export interface KnowledgeStats {
  total_documents: number
  total_chunks: number
  total_tokens: number
  quarantined_documents: number
  documents_by_category: Record<string, number>
  documents_by_access_level: Record<string, number>
  storage_bytes: number
}

export interface CategoryOption {
  value: string
  label: string
}

export interface CategoriesMeta {
  categories: CategoryOption[]
  access_levels: CategoryOption[]
  supported_file_types: string[]
}

export interface SearchFilters {
  category?: DocumentCategory | null
  access_levels?: AccessLevel[] | null
  access_level?: AccessLevel | null
  department_id?: string | null
  document_id?: string | null
  version?: number | null
  min_similarity?: number | null
  max_distance?: number | null
}

export interface KnowledgeSearchRequest {
  query: string
  top_k?: number
  min_score?: number
  filters?: SearchFilters
}

export interface EmbeddingSpaceInfo {
  provider: string
  model: string
  version: string
  dimension: number
  metric: string
  space_id: string
  provider_name?: string
  model_name?: string
}

export interface KnowledgeSearchResult {
  chunk_id: string
  document_id: string
  document_title: string
  document_version: number
  chunk_index: number
  content_excerpt: string
  full_text: string
  section_title?: string | null
  page_number?: number | null
  category: DocumentCategory
  department_id?: string | null
  access_level: AccessLevel
  distance: number
  similarity_score: number
  ranking_position: number
  is_table: boolean
  excerpt?: string
  version?: number
  token_count?: number
}

export interface KnowledgeSearchResponse {
  query_id: string
  query: string
  result_count: number
  embedding_space: EmbeddingSpaceInfo
  search_duration_ms: number
  filters_applied: Record<string, unknown>
  results: KnowledgeSearchResult[]
}

export interface RetrievalHealthResponse {
  status: string
  chroma_connected: boolean
  collection_name: string
  total_chunks: number
  embedding_space: EmbeddingSpaceInfo
  is_ready: boolean
}

// ── Chunk 4.3: Context Retrieval & Assembly Types ─────────────────────────────

export type ContextOrdering = 'relevance' | 'document_order' | 'grouped_by_doc'

export type RetrievalStatus =
  | 'SUCCESS'
  | 'NO_RESULTS'
  | 'INSUFFICIENT_CONTEXT'
  | 'PARTIAL_CONTEXT'
  | 'FAILED'

export interface KnowledgeRetrievalRequest {
  query: string
  top_k?: number
  candidate_k?: number
  max_context_tokens?: number
  filters?: SearchFilters
  context_ordering?: ContextOrdering
  include_formatted_context?: boolean
  min_relevance_threshold?: number
}

export interface SourceCitation {
  citation_id: string
  citation_marker: string
  document_id: string
  document_title: string
  document_version: number
  chunk_id: string
  section_title?: string | null
  heading_path: string[]
  page_number?: number | null
  source_reference: string
}

export interface ContextBlock {
  citation_id: string
  document_id: string
  document_title: string
  document_version: number
  chunk_id: string
  chunk_index: number
  section_title?: string | null
  heading_path: string[]
  page_number?: number | null
  content: string
  token_count: number
  category: DocumentCategory
  department_id?: string | null
  access_level: AccessLevel
  rank: number
  distance: number
  similarity_score: number
  is_table: boolean
}

export interface SkippedChunkInfo {
  chunk_id: string
  document_id: string
  document_title: string
  rank: number
  token_count: number
  similarity_score: number
  skip_reason: string
}

export interface RetrievalMetadata {
  embedding_space: EmbeddingSpaceInfo
  candidate_count: number
  retrieved_count: number
  selected_count: number
  skipped_count: number
  token_budget: number
  assembled_token_count: number
  overhead_token_count: number
  token_count_method: string
  retrieval_duration_ms: number
  context_ordering: string
}

export interface KnowledgeRetrievalResponse {
  retrieval_id: string
  status: RetrievalStatus
  status_reason?: string | null
  query: string
  created_at: string
  metadata: RetrievalMetadata
  context_blocks: ContextBlock[]
  citations: SourceCitation[]
  formatted_context?: string | null
  skipped_chunks: SkippedChunkInfo[]
  limitations: string[]
  warnings: string[]
}

// ── Chunk 4.4: RAG Grounded Answer Generation Types ─────────────────────────

export type AnswerType =
  | 'DIRECT_ANSWER'
  | 'CONDITIONAL_ANSWER'
  | 'PROCEDURAL_GUIDANCE'
  | 'POLICY_STATEMENT'
  | 'INSUFFICIENT_INFORMATION'
  | 'CONFLICTING_INFORMATION'
  | 'OUT_OF_SCOPE'

export type AnswerStatus =
  | 'ANSWERED'
  | 'PARTIAL_ANSWER'
  | 'INSUFFICIENT_EVIDENCE'
  | 'CONFLICTING_EVIDENCE'
  | 'OUT_OF_SCOPE'
  | 'GENERATION_UNAVAILABLE'
  | 'FAILED'

export interface KnowledgeAnswerRequest {
  query: string
  top_k?: number
  candidate_k?: number
  max_context_tokens?: number
  filters?: SearchFilters
  max_sources?: number
  require_citations?: boolean
  temperature?: number
}

export interface CitationReference {
  citation_marker: string
  citation_id: string
  document_id: string
  document_title: string
  document_version: number
  chunk_id: string
  section_title?: string | null
  page_number?: number | null
  source_reference: string
  similarity_score: number
  excerpt: string
  category?: DocumentCategory | null
  access_level?: AccessLevel | null
}

export interface RetrievalSummary {
  retrieval_id: string
  retrieval_status: string
  candidate_count: number
  selected_chunks_count: number
  skipped_count?: number
  context_tokens_used: number
  retrieval_duration_ms: number
}

export interface GenerationMetadata {
  provider_name: string
  model_name: string
  prompt_version: string
  generation_duration_ms: number
  total_duration_ms: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  retrieval_summary: RetrievalSummary
  citations_verified: boolean
  citations_validated_count: number
  invalid_citations_detected: string[]
  retry_count: number
}

export interface KnowledgeAnswerResponse {
  answer_id: string
  status: AnswerStatus
  status_reason?: string | null
  query: string
  answer: string
  answer_type: AnswerType
  confidence_assessment: string
  citations: CitationReference[]
  retrieved_sources: CitationReference[]
  limitations: string[]
  conflicts_detected: string[]
  follow_up_questions?: string[]
  is_clinical_query: boolean
  clinical_disclaimer?: string | null
  metadata: GenerationMetadata
  created_at: string
}

export interface AnswerHealthResponse {
  status: string
  is_generation_ready: boolean
  provider_name: string
  model_name: string
  external_provider_enabled: boolean
  total_documents_indexed: number
  total_chunks_indexed: number
}

export const knowledgeApi = {
  listDocuments: (params?: {
    category?: string
    access_level?: string
    search?: string
    limit?: number
    skip?: number
  }) => {
    const q = new URLSearchParams()
    if (params?.category) q.set('category', params.category)
    if (params?.access_level) q.set('access_level', params.access_level)
    if (params?.search) q.set('search', params.search)
    if (params?.limit) q.set('limit', params.limit.toString())
    if (params?.skip) q.set('skip', params.skip.toString())
    const qs = q.toString() ? `?${q.toString()}` : ''
    return apiClient.get<DocumentSummary[]>(`/knowledge/documents${qs}`)
  },

  getDocument: (documentId: string) =>
    apiClient.get<DocumentDetail>(`/knowledge/documents/${documentId}`),

  getChunks: (documentId: string, version?: number) => {
    const qs = version ? `?version=${version}` : ''
    return apiClient.get<DocumentChunksResponse>(
      `/knowledge/documents/${documentId}/chunks${qs}`
    )
  },

  uploadDocument: async (formData: FormData): Promise<DocumentUploadResponse> => {
    // Note: formData requires multipart/form-data without setting application/json Content-Type
    const token = (apiClient as unknown as { _accessToken?: string })._accessToken
    const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1'
    const headers: Record<string, string> = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${baseUrl}/knowledge/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(err.detail || `Upload failed with status ${response.status}`)
    }

    return response.json()
  },

  reindexDocument: (
    documentId: string,
    params?: { target_chunk_tokens?: number; chunk_overlap_tokens?: number }
  ) =>
    apiClient.post<DocumentUploadResponse>(
      `/knowledge/documents/${documentId}/reindex`,
      params ?? {}
    ),

  deleteDocument: (documentId: string) =>
    apiClient.delete<{ deleted: boolean; document_id: string; message: string }>(
      `/knowledge/documents/${documentId}`
    ),

  getStats: () => apiClient.get<KnowledgeStats>('/knowledge/stats'),

  getCategories: () => apiClient.get<CategoriesMeta>('/knowledge/categories'),

  listIngestionRuns: (documentId?: string, limit = 50) => {
    const qs = documentId ? `?document_id=${documentId}&limit=${limit}` : `?limit=${limit}`
    return apiClient.get<IngestionRun[]>(`/knowledge/ingestion-runs${qs}`)
  },

  getIngestionRun: (ingestionId: string) =>
    apiClient.get<IngestionRun>(`/knowledge/ingestion-runs/${ingestionId}`),

  search: (req: KnowledgeSearchRequest) =>
    apiClient.post<KnowledgeSearchResponse>('/knowledge/search', req),

  retrieveContext: (req: KnowledgeRetrievalRequest) =>
    apiClient.post<KnowledgeRetrievalResponse>('/knowledge/retrieve', req),

  getSearchHealth: () =>
    apiClient.get<RetrievalHealthResponse>('/knowledge/search/health'),

  generateAnswer: (req: KnowledgeAnswerRequest) =>
    apiClient.post<KnowledgeAnswerResponse>('/knowledge/answer', req),

  getAnswerHealth: () =>
    apiClient.get<AnswerHealthResponse>('/knowledge/answer/health'),
}
