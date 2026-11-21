import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  BookOpen,
  UploadCloud,
  Search,
  RefreshCw,
  Trash2,
  Layers,
  ShieldCheck,
  ShieldAlert,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ChevronRight,
  X,
  FileCode,
  Hash,
  Database,
  Cpu,
  Eye,
  Sliders,
} from 'lucide-react'
import {
  knowledgeApi,
  DocumentSummary,
  DocumentDetail,
  DocumentChunk,
  KnowledgeStats,
  CategoriesMeta,
  DocumentCategory,
  AccessLevel,
} from '../../api/knowledge'
import { useAuth } from '../../context/AuthContext'
import { TopHeader } from '../../components/layout/TopHeader'

export const KnowledgeBase: React.FC = () => {
  const { user } = useAuth()
  const canManage = user?.role === 'ADMIN'

  // Data states
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [stats, setStats] = useState<KnowledgeStats | null>(null)
  const [categoriesMeta, setCategoriesMeta] = useState<CategoriesMeta | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedAccessLevel, setSelectedAccessLevel] = useState<string>('')

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadCategory, setUploadCategory] = useState<DocumentCategory>('POLICY')
  const [uploadAccessLevel, setUploadAccessLevel] = useState<AccessLevel>('INTERNAL')
  const [uploadTitle, setUploadTitle] = useState<string>('')
  const [uploadDescription, setUploadDescription] = useState<string>('')
  const [uploadTags, setUploadTags] = useState<string>('')
  const [uploadDepartment, setUploadDepartment] = useState<string>('')
  const [uploadAuthor, setUploadAuthor] = useState<string>('')
  const [uploadChangeSummary, setUploadChangeSummary] = useState<string>('')
  const [isUploading, setIsUploading] = useState<boolean>(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Chunk Inspector Drawer state
  const [selectedDocForChunks, setSelectedDocForChunks] = useState<DocumentSummary | null>(null)
  const [chunks, setChunks] = useState<DocumentChunk[]>([])
  const [isLoadingChunks, setIsLoadingChunks] = useState<boolean>(false)
  const [chunkVersion, setChunkVersion] = useState<number | undefined>(undefined)

  // Telemetry & Detail Drawer state
  const [selectedDocDetail, setSelectedDocDetail] = useState<DocumentDetail | null>(null)

  // Reindex modal state
  const [reindexDocId, setReindexDocId] = useState<string | null>(null)
  const [reindexTargetTokens, setReindexTargetTokens] = useState<number>(512)
  const [reindexOverlapTokens, setReindexOverlapTokens] = useState<number>(64)
  const [isReindexing, setIsReindexing] = useState<boolean>(false)

  // Load initial data
  const fetchData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [docsData, statsData, catsData] = await Promise.all([
        knowledgeApi.listDocuments({
          category: selectedCategory || undefined,
          access_level: selectedAccessLevel || undefined,
          search: searchQuery || undefined,
        }),
        knowledgeApi.getStats().catch(() => null),
        knowledgeApi.getCategories().catch(() => null),
      ])
      setDocuments(docsData)
      if (statsData) setStats(statsData)
      if (catsData) setCategoriesMeta(catsData)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load knowledge documents')
    } finally {
      setIsLoading(false)
    }
  }, [selectedCategory, selectedAccessLevel, searchQuery])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Handle File Selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setUploadFile(file)
      if (!uploadTitle) {
        const cleanName = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ')
        setUploadTitle(cleanName.charAt(0).toUpperCase() + cleanName.slice(1))
      }
    }
  }

  // Handle Upload Submission
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!uploadFile) {
      setError('Please select a document file to upload.')
      return
    }

    setIsUploading(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('category', uploadCategory)
      formData.append('access_level', uploadAccessLevel)
      if (uploadTitle) formData.append('title', uploadTitle)
      if (uploadDescription) formData.append('description', uploadDescription)
      if (uploadTags) formData.append('tags', uploadTags)
      if (uploadDepartment) formData.append('department_id', uploadDepartment)
      if (uploadAuthor) formData.append('author', uploadAuthor)
      if (uploadChangeSummary) formData.append('change_summary', uploadChangeSummary)

      const res = await knowledgeApi.uploadDocument(formData)
      setSuccessMessage(res.message)
      setIsUploadModalOpen(false)
      resetUploadForm()
      await fetchData()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Document upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const resetUploadForm = () => {
    setUploadFile(null)
    setUploadTitle('')
    setUploadDescription('')
    setUploadTags('')
    setUploadDepartment('')
    setUploadAuthor('')
    setUploadChangeSummary('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // Open Chunks Inspector
  const handleInspectChunks = async (doc: DocumentSummary, ver?: number) => {
    setSelectedDocForChunks(doc)
    setChunkVersion(ver || doc.active_version)
    setIsLoadingChunks(true)
    try {
      const res = await knowledgeApi.getChunks(doc.document_id, ver || doc.active_version)
      setChunks(res.chunks)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to retrieve document chunks')
    } finally {
      setIsLoadingChunks(false)
    }
  }

  // Open Document Detail & Ingestion Telemetry
  const handleViewDetail = async (docId: string) => {
    try {
      const detail = await knowledgeApi.getDocument(docId)
      setSelectedDocDetail(detail)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to retrieve document details')
    }
  }

  // Handle Document Deletion
  const handleDeleteDocument = async (docId: string, title: string) => {
    if (!window.confirm(`Permanently delete "${title}" and all its vector chunks?`)) {
      return
    }
    try {
      await knowledgeApi.deleteDocument(docId)
      setSuccessMessage(`Document "${title}" and all associated vectors deleted.`)
      if (selectedDocForChunks?.document_id === docId) setSelectedDocForChunks(null)
      if (selectedDocDetail?.document_id === docId) setSelectedDocDetail(null)
      await fetchData()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete document')
    }
  }

  // Handle Reindexing
  const handleExecuteReindex = async () => {
    if (!reindexDocId) return
    setIsReindexing(true)
    setError(null)
    try {
      const res = await knowledgeApi.reindexDocument(reindexDocId, {
        target_chunk_tokens: reindexTargetTokens,
        chunk_overlap_tokens: reindexOverlapTokens,
      })
      setSuccessMessage(res.message)
      setReindexDocId(null)
      await fetchData()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Reindexing failed')
    } finally {
      setIsReindexing(false)
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
  }

  const getStatusBadge = (status: string, isQuarantined: boolean) => {
    if (isQuarantined || status === 'QUARANTINED') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-medium bg-red-500/10 text-red-400 border border-red-500/20">
          <ShieldAlert className="w-3 h-3 text-red-400" />
          Quarantined
        </span>
      )
    }
    if (status === 'COMPLETED') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          Active / Indexed
        </span>
      )
    }
    if (status === 'PROCESSING' || status === 'PENDING') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <Clock className="w-3 h-3 text-amber-400 animate-spin" />
          Processing
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-medium bg-red-500/10 text-red-400 border border-red-500/20">
        <AlertTriangle className="w-3 h-3 text-red-400" />
        Failed
      </span>
    )
  }

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'CLINICAL_PROTOCOL':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/20'
      case 'SOP':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20'
      case 'POLICY':
        return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
      case 'EQUIPMENT_MANUAL':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
      case 'INFECTION_CONTROL':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/20'
      default:
        return 'text-[#a5a5ac] bg-white/5 border-white/10'
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#131315] text-[#f0f0f3] overflow-hidden select-none">
      <TopHeader
        title="Hospital Knowledge Base"
        breadcrumbs={[
          { label: 'HospitalOps', href: '/dashboard' },
          { label: 'Knowledge Base', href: '/knowledge' },
        ]}
      />

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        {/* Alerts */}
        {error && (
          <div className="flex items-center justify-between p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300 text-xs">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {successMessage && (
          <div className="flex items-center justify-between p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>{successMessage}</span>
            </div>
            <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-emerald-200">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Header Action Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold text-[#f0f0f3] tracking-tight flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-[#9ba8ff]" />
              Approved Hospital Knowledge Catalog
            </h1>
            <p className="text-xs text-[#8e8e96] mt-0.5">
              Structured operational policies, clinical guidelines, and equipment documentation indexed in ChromaDB for future RAG retrieval.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={fetchData}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-xs text-[#dedee1] transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-[#a5a5ac] ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>

            {canManage && (
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-[#9ba8ff] hover:bg-[#8897fa] text-[#131315] font-medium text-xs transition-colors shadow-sm"
              >
                <UploadCloud className="w-4 h-4" />
                Upload Document
              </button>
            )}
          </div>
        </div>

        {/* Metric Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-3.5 rounded-lg bg-[#19191b] border border-line flex flex-col justify-between">
              <span className="text-[11px] font-medium text-[#8e8e96] uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-400" />
                Total Documents
              </span>
              <span className="text-xl font-bold text-[#f0f0f3] mt-2 font-mono">
                {stats.total_documents}
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-[#19191b] border border-line flex flex-col justify-between">
              <span className="text-[11px] font-medium text-[#8e8e96] uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-purple-400" />
                Indexed Chunks
              </span>
              <span className="text-xl font-bold text-[#f0f0f3] mt-2 font-mono">
                {stats.total_chunks}
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-[#19191b] border border-line flex flex-col justify-between">
              <span className="text-[11px] font-medium text-[#8e8e96] uppercase tracking-wider flex items-center gap-1.5">
                <Hash className="w-3.5 h-3.5 text-amber-400" />
                Total Tokens
              </span>
              <span className="text-xl font-bold text-[#f0f0f3] mt-2 font-mono">
                {stats.total_tokens.toLocaleString()}
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-[#19191b] border border-line flex flex-col justify-between">
              <span className="text-[11px] font-medium text-[#8e8e96] uppercase tracking-wider flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-emerald-400" />
                Storage Footprint
              </span>
              <span className="text-xl font-bold text-[#f0f0f3] mt-2 font-mono">
                {formatBytes(stats.storage_bytes)}
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-[#19191b] border border-line flex flex-col justify-between">
              <span className="text-[11px] font-medium text-[#8e8e96] uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-good" />
                Privacy Guard
              </span>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xl font-bold text-good font-mono">0 Leaks</span>
                {stats.quarantined_documents > 0 && (
                  <span className="text-[10.5px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-mono">
                    {stats.quarantined_documents} quarantined
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Filter Bar */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 p-2.5 rounded-lg bg-[#161618] border border-line">
          <div className="relative w-full md:w-80">
            <Search className="w-3.5 h-3.5 text-[#6f6f78] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by title, filename, or tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#1c1c1f] border border-white/5 rounded-md pl-9 pr-3 py-1.5 text-xs text-[#f0f0f3] placeholder-[#6f6f78] focus:outline-none focus:border-[#9ba8ff]/50"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-[#1c1c1f] border border-white/5 rounded-md px-2.5 py-1.5 text-xs text-[#dedee1] focus:outline-none focus:border-[#9ba8ff]/50"
            >
              <option value="">All Categories</option>
              {categoriesMeta?.categories.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>

            <select
              value={selectedAccessLevel}
              onChange={(e) => setSelectedAccessLevel(e.target.value)}
              className="bg-[#1c1c1f] border border-white/5 rounded-md px-2.5 py-1.5 text-xs text-[#dedee1] focus:outline-none focus:border-[#9ba8ff]/50"
            >
              <option value="">All Access Levels</option>
              {categoriesMeta?.access_levels.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Documents Table */}
        <div className="rounded-lg bg-[#19191b] border border-line overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#141416] border-b border-line text-[#8e8e96] font-medium uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-3">Document Title & File</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Access</th>
                  <th className="px-4 py-3">Version</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Chunks / Tokens</th>
                  <th className="px-4 py-3">Updated</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {documents.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-[#8e8e96]">
                      {isLoading ? 'Loading knowledge documents...' : 'No knowledge documents found matching criteria.'}
                    </td>
                  </tr>
                ) : (
                  documents.map((doc) => (
                    <tr key={doc.document_id} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="px-4 py-3">
                        <div className="flex flex-col min-w-0 max-w-xs">
                          <span
                            onClick={() => handleViewDetail(doc.document_id)}
                            className="font-medium text-[#f0f0f3] hover:text-[#9ba8ff] cursor-pointer truncate"
                          >
                            {doc.title}
                          </span>
                          <span className="text-[10.5px] text-[#74747c] font-mono truncate">
                            {doc.source_filename} ({formatBytes(doc.file_size_bytes)})
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${getCategoryColor(doc.category)}`}>
                          {doc.category.replace(/_/g, ' ')}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        <span className="text-[10.5px] text-[#dedee1] font-mono">
                          {doc.access_level}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        <span className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 font-mono text-[10.5px] text-[#c7c7cc]">
                          v{doc.active_version}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        {getStatusBadge(doc.status, doc.is_quarantined)}
                      </td>

                      <td className="px-4 py-3 font-mono text-[11px] text-[#a5a5ac]">
                        <span>{doc.total_chunks} chunks</span>
                        <span className="text-[#63636b] ml-1">({doc.total_tokens.toLocaleString()} tok)</span>
                      </td>

                      <td className="px-4 py-3 text-[10.5px] text-[#8e8e96] font-mono">
                        {new Date(doc.updated_at).toLocaleDateString()}
                      </td>

                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleInspectChunks(doc)}
                            title="Inspect Chunks"
                            className="p-1 rounded text-[#a5a5ac] hover:text-[#9ba8ff] hover:bg-white/5 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => handleViewDetail(doc.document_id)}
                            title="Telemetry & History"
                            className="p-1 rounded text-[#a5a5ac] hover:text-[#dedee1] hover:bg-white/5 transition-colors"
                          >
                            <ChevronRight className="w-3.5 h-3.5" />
                          </button>

                          {canManage && (
                            <>
                              <button
                                onClick={() => setReindexDocId(doc.document_id)}
                                title="Reindex Chunks"
                                className="p-1 rounded text-[#a5a5ac] hover:text-amber-400 hover:bg-white/5 transition-colors"
                              >
                                <Sliders className="w-3.5 h-3.5" />
                              </button>

                              <button
                                onClick={() => handleDeleteDocument(doc.document_id, doc.title)}
                                title="Delete Document"
                                className="p-1 rounded text-[#a5a5ac] hover:text-red-400 hover:bg-white/5 transition-colors"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Upload Modal ──────────────────────────────────────────────────────── */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="bg-[#19191b] border border-line rounded-xl w-full max-w-xl shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-4 border-b border-line">
              <div className="flex items-center gap-2 text-sm font-semibold text-[#f0f0f3]">
                <UploadCloud className="w-4 h-4 text-[#9ba8ff]" />
                <span>Upload Hospital Knowledge Document</span>
              </div>
              <button
                onClick={() => setIsUploadModalOpen(false)}
                className="text-[#8e8e96] hover:text-[#f0f0f3] p-1 rounded hover:bg-white/5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="p-5 space-y-4 overflow-y-auto flex-1">
              {/* File Dropzone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-colors ${
                  uploadFile ? 'border-[#9ba8ff]/60 bg-[#9ba8ff]/5' : 'border-white/10 hover:border-white/20 bg-white/[0.02]'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,.docx,.txt,.md,.html"
                  className="hidden"
                />
                <FileCode className="w-8 h-8 text-[#9ba8ff] mx-auto mb-2 opacity-80" />
                {uploadFile ? (
                  <div>
                    <span className="text-xs font-semibold text-[#f0f0f3]">{uploadFile.name}</span>
                    <span className="text-[10px] text-[#8e8e96] block font-mono mt-0.5">
                      {formatBytes(uploadFile.size)}
                    </span>
                  </div>
                ) : (
                  <div>
                    <span className="text-xs font-medium text-[#dedee1]">Click to select a hospital document</span>
                    <span className="text-[10px] text-[#6f6f78] block mt-1">
                      Supports PDF, DOCX, Markdown (.md), Plain Text (.txt), and HTML (max 25MB)
                    </span>
                  </div>
                )}
              </div>

              {/* Title & Category */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">Document Title</label>
                  <input
                    type="text"
                    required
                    value={uploadTitle}
                    onChange={(e) => setUploadTitle(e.target.value)}
                    placeholder="e.g. ICU Bed Allocation Protocol"
                    className="w-full bg-[#141416] border border-line rounded-md px-3 py-1.5 text-xs text-[#f0f0f3] focus:outline-none focus:border-[#9ba8ff]/60"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">Category</label>
                  <select
                    value={uploadCategory}
                    onChange={(e) => setUploadCategory(e.target.value as DocumentCategory)}
                    className="w-full bg-[#141416] border border-line rounded-md px-3 py-1.5 text-xs text-[#f0f0f3] focus:outline-none focus:border-[#9ba8ff]/60"
                  >
                    <option value="POLICY">Policy</option>
                    <option value="SOP">Standard Operating Procedure</option>
                    <option value="CLINICAL_PROTOCOL">Clinical Protocol</option>
                    <option value="EQUIPMENT_MANUAL">Equipment Manual</option>
                    <option value="INFECTION_CONTROL">Infection Control</option>
                    <option value="ADMINISTRATIVE">Administrative</option>
                    <option value="CAPACITY_PLANNING">Capacity Planning</option>
                    <option value="GENERAL_REFERENCE">General Reference</option>
                  </select>
                </div>
              </div>

              {/* Access Level & Tags */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">Access Sensitivity</label>
                  <select
                    value={uploadAccessLevel}
                    onChange={(e) => setUploadAccessLevel(e.target.value as AccessLevel)}
                    className="w-full bg-[#141416] border border-line rounded-md px-3 py-1.5 text-xs text-[#f0f0f3] focus:outline-none focus:border-[#9ba8ff]/60"
                  >
                    <option value="INTERNAL">INTERNAL (Hospital Operations)</option>
                    <option value="PUBLIC">PUBLIC (All Personnel)</option>
                    <option value="RESTRICTED">RESTRICTED (Department Leads)</option>
                    <option value="CONFIDENTIAL">CONFIDENTIAL (Executive Leadership)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">Tags (comma-separated)</label>
                  <input
                    type="text"
                    value={uploadTags}
                    onChange={(e) => setUploadTags(e.target.value)}
                    placeholder="icu, ventilators, surge"
                    className="w-full bg-[#141416] border border-line rounded-md px-3 py-1.5 text-xs text-[#f0f0f3] focus:outline-none focus:border-[#9ba8ff]/60"
                  />
                </div>
              </div>

              {/* Description & Change Summary */}
              <div>
                <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">Description</label>
                <textarea
                  rows={2}
                  value={uploadDescription}
                  onChange={(e) => setUploadDescription(e.target.value)}
                  placeholder="Operational scope, targeted clinical units, and applicability..."
                  className="w-full bg-[#141416] border border-line rounded-md px-3 py-1.5 text-xs text-[#f0f0f3] focus:outline-none focus:border-[#9ba8ff]/60 resize-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">Version Change Summary</label>
                <input
                  type="text"
                  value={uploadChangeSummary}
                  onChange={(e) => setUploadChangeSummary(e.target.value)}
                  placeholder="e.g. Annual protocol review and surge threshold updates"
                  className="w-full bg-[#141416] border border-line rounded-md px-3 py-1.5 text-xs text-[#f0f0f3] focus:outline-none focus:border-[#9ba8ff]/60"
                />
              </div>

              {/* Privacy Warning */}
              <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <span>
                  <strong>Healthcare Data Boundary:</strong> Documents will be automatically scanned by the 10-stage pipeline. Any files containing Protected Health Information (PHI) or patient records will be quarantined.
                </span>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-line">
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-md bg-white/5 hover:bg-white/10 text-xs text-[#dedee1]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !uploadFile}
                  className="px-4 py-1.5 rounded-md bg-[#9ba8ff] hover:bg-[#8897fa] text-[#131315] font-semibold text-xs flex items-center gap-1.5 disabled:opacity-50"
                >
                  {isUploading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Running 10-Stage Ingestion...
                    </>
                  ) : (
                    'Start Ingestion Pipeline'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Chunk Inspector Drawer ────────────────────────────────────────────── */}
      {selectedDocForChunks && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-[#19191b] border-l border-line shadow-2xl flex flex-col">
          <div className="flex items-center justify-between p-4 border-b border-line">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#9ba8ff]" />
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-[#f0f0f3]">
                  {selectedDocForChunks.title}
                </span>
                <span className="text-[10px] text-[#74747c] font-mono">
                  Indexed Chunks · Version {chunkVersion}
                </span>
              </div>
            </div>
            <button
              onClick={() => setSelectedDocForChunks(null)}
              className="text-[#8e8e96] hover:text-[#f0f0f3] p-1 rounded hover:bg-white/5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {isLoadingChunks ? (
              <div className="py-12 text-center text-xs text-[#8e8e96] flex flex-col items-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-[#9ba8ff]" />
                <span>Retrieving chunks from ChromaDB...</span>
              </div>
            ) : chunks.length === 0 ? (
              <div className="py-12 text-center text-xs text-[#8e8e96]">
                No vector chunks found for this version.
              </div>
            ) : (
              chunks.map((chunk) => (
                <div
                  key={chunk.chunk_id}
                  className="p-3.5 rounded-lg bg-[#141416] border border-line hover:border-[#9ba8ff]/30 transition-colors space-y-2"
                >
                  <div className="flex items-center justify-between text-[10px] text-[#74747c] font-mono">
                    <span className="text-[#9ba8ff] font-semibold">{chunk.chunk_id}</span>
                    <div className="flex items-center gap-2">
                      {chunk.section_title && (
                        <span className="px-1.5 py-0.5 rounded bg-white/5 text-[#dedee1]">
                          {chunk.section_title}
                        </span>
                      )}
                      {chunk.page_number && (
                        <span className="px-1.5 py-0.5 rounded bg-white/5">Page {chunk.page_number}</span>
                      )}
                      <span>{chunk.token_count} tokens</span>
                    </div>
                  </div>

                  <pre className="text-xs text-[#dedee1] font-mono whitespace-pre-wrap bg-[#101012] p-3 rounded border border-white/5 leading-relaxed overflow-x-auto">
                    {chunk.text}
                  </pre>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Document Detail & Telemetry Drawer ─────────────────────────────────── */}
      {selectedDocDetail && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-[#19191b] border-l border-line shadow-2xl flex flex-col">
          <div className="flex items-center justify-between p-4 border-b border-line">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[#9ba8ff]" />
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-[#f0f0f3]">{selectedDocDetail.title}</span>
                <span className="text-[10px] text-[#74747c] font-mono">
                  {selectedDocDetail.document_id} · Active v{selectedDocDetail.active_version}
                </span>
              </div>
            </div>
            <button
              onClick={() => setSelectedDocDetail(null)}
              className="text-[#8e8e96] hover:text-[#f0f0f3] p-1 rounded hover:bg-white/5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs">
            {/* Metadata Summary */}
            <div>
              <span className="text-[10px] uppercase font-semibold text-[#8e8e96] tracking-wider block mb-2">
                Metadata & Attributes
              </span>
              <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-[#141416] border border-line font-mono text-[11px]">
                <div>
                  <span className="text-[#6f6f78] block text-[9.5px]">CATEGORY</span>
                  <span className="text-[#dedee1]">{selectedDocDetail.category}</span>
                </div>
                <div>
                  <span className="text-[#6f6f78] block text-[9.5px]">ACCESS LEVEL</span>
                  <span className="text-[#dedee1]">{selectedDocDetail.access_level}</span>
                </div>
                <div>
                  <span className="text-[#6f6f78] block text-[9.5px]">SOURCE FILE</span>
                  <span className="text-[#dedee1] truncate block">{selectedDocDetail.source_filename}</span>
                </div>
                <div>
                  <span className="text-[#6f6f78] block text-[9.5px]">FILE SIZE</span>
                  <span className="text-[#dedee1]">{formatBytes(selectedDocDetail.file_size_bytes)}</span>
                </div>
              </div>
            </div>

            {/* Version History */}
            <div>
              <span className="text-[10px] uppercase font-semibold text-[#8e8e96] tracking-wider block mb-2">
                Version History
              </span>
              <div className="space-y-1.5">
                {selectedDocDetail.versions.map((ver) => (
                  <div
                    key={ver.version_id}
                    className={`p-2.5 rounded border text-[11px] flex items-center justify-between ${
                      ver.version === selectedDocDetail.active_version
                        ? 'bg-[#9ba8ff]/10 border-[#9ba8ff]/30 text-[#f0f0f3]'
                        : 'bg-[#141416] border-line text-[#a5a5ac]'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold">v{ver.version}</span>
                      <span className="text-[10px] text-[#74747c]">
                        {new Date(ver.created_at).toLocaleDateString()}
                      </span>
                      {ver.change_summary && (
                        <span className="text-[10.5px] italic text-[#dedee1]">
                          — {ver.change_summary}
                        </span>
                      )}
                    </div>
                    <span className="font-mono text-[10px]">{ver.chunk_count} chunks</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 10-Stage Pipeline Telemetry */}
            {selectedDocDetail.latest_ingestion_run && (
              <div>
                <span className="text-[10px] uppercase font-semibold text-[#8e8e96] tracking-wider block mb-2 flex items-center justify-between">
                  <span>10-Stage Ingestion Telemetry</span>
                  <span className="font-mono text-[9px] text-[#6f6f78]">
                    {selectedDocDetail.latest_ingestion_run.total_duration_ms?.toFixed(1)} ms total
                  </span>
                </span>
                <div className="space-y-1 rounded-lg bg-[#141416] border border-line p-2">
                  {selectedDocDetail.latest_ingestion_run.stages.map((st, i) => (
                    <div
                      key={st.stage}
                      className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-white/[0.02] text-[11px]"
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-4 font-mono text-[9px] text-[#6f6f78]">{i + 1}</span>
                        <span className="font-mono text-[#dedee1]">{st.stage}</span>
                      </div>
                      <div className="flex items-center gap-2 font-mono text-[10px]">
                        <span className="text-[#8e8e96]">{st.duration_ms.toFixed(1)} ms</span>
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            st.status === 'success' ? 'bg-emerald-400' : 'bg-red-400'
                          }`}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Reindex Modal ─────────────────────────────────────────────────────── */}
      {reindexDocId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="bg-[#19191b] border border-line rounded-xl w-full max-w-md shadow-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-[#f0f0f3] flex items-center gap-2">
                <Sliders className="w-4 h-4 text-amber-400" />
                Reindex Knowledge Document
              </span>
              <button
                onClick={() => setReindexDocId(null)}
                className="text-[#8e8e96] hover:text-[#f0f0f3]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-[#8e8e96]">
              Re-chunk and re-embed this document from its archived source file using custom chunk boundaries.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">
                  Target Chunk Tokens (default: 512)
                </label>
                <input
                  type="number"
                  min={64}
                  max={2048}
                  value={reindexTargetTokens}
                  onChange={(e) => setReindexTargetTokens(parseInt(e.target.value) || 512)}
                  className="w-full bg-[#141416] border border-line rounded-md px-3 py-1.5 text-xs text-[#f0f0f3]"
                />
              </div>

              <div>
                <label className="text-[11px] font-medium text-[#8e8e96] mb-1 block">
                  Overlap Tokens (default: 64)
                </label>
                <input
                  type="number"
                  min={0}
                  max={512}
                  value={reindexOverlapTokens}
                  onChange={(e) => setReindexOverlapTokens(parseInt(e.target.value) || 64)}
                  className="w-full bg-[#141416] border border-line rounded-md px-3 py-1.5 text-xs text-[#f0f0f3]"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-line">
              <button
                onClick={() => setReindexDocId(null)}
                className="px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteReindex}
                disabled={isReindexing}
                className="px-3.5 py-1.5 rounded bg-amber-500 hover:bg-amber-400 text-[#131315] font-semibold text-xs flex items-center gap-1.5"
              >
                {isReindexing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                Execute Reindex
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
