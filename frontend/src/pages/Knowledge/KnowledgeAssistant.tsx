import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  knowledgeApi,
  KnowledgeAnswerResponse,
  AnswerHealthResponse,
  CategoriesMeta,
  DocumentCategory,
  AccessLevel,
} from '../../api/knowledge'
import { TopHeader } from '../../components/layout/TopHeader'
import { AssistantHeader } from '../../components/knowledge/AssistantHeader'
import { QuestionComposer } from '../../components/knowledge/QuestionComposer'
import { SuggestedQuestions } from '../../components/knowledge/SuggestedQuestions'
import { AdvancedSearchSettings } from '../../components/knowledge/AdvancedSearchSettings'
import { AnswerPanel } from '../../components/knowledge/AnswerPanel'
import { CitationEvidencePanel } from '../../components/knowledge/CitationEvidencePanel'
import { GenerationMetadataPanel } from '../../components/knowledge/GenerationMetadataPanel'
import { SessionHistoryDrawer } from '../../components/knowledge/SessionHistoryDrawer'
import { AssistantEmptyState } from '../../components/knowledge/AssistantEmptyState'
import { AssistantLoadingState } from '../../components/knowledge/AssistantLoadingState'
import { AssistantErrorState } from '../../components/knowledge/AssistantErrorState'
import {
  AssistantQueryConfig,
  DEFAULT_QUERY_CONFIG,
  SessionHistoryItem,
} from '../../types/assistant'

export const KnowledgeAssistant: React.FC = () => {
  const [searchParams] = useSearchParams()

  // Query input state
  const [question, setQuestion] = useState<string>('')
  const [config, setConfig] = useState<AssistantQueryConfig>(DEFAULT_QUERY_CONFIG)
  const [isAdvancedOpen, setIsAdvancedOpen] = useState<boolean>(false)

  // Subsystem health and categories
  const [health, setHealth] = useState<AnswerHealthResponse | null>(null)
  const [isLoadingHealth, setIsLoadingHealth] = useState<boolean>(true)
  const [categoriesMeta, setCategoriesMeta] = useState<CategoriesMeta | null>(null)

  // Execution states
  const [isGenerating, setIsGenerating] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [currentResponse, setCurrentResponse] = useState<KnowledgeAnswerResponse | null>(null)

  // Citation selection and evidence view tab
  const [selectedCitationMarker, setSelectedCitationMarker] = useState<string | null>(null)
  const [evidenceTab, setEvidenceTab] = useState<'citations' | 'retrieved'>('citations')

  // In-memory session history (strictly local to current browser session)
  const [sessionHistory, setSessionHistory] = useState<SessionHistoryItem[]>([])
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null)
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false)

  // Mobile / Tablet active view tab
  const [mobileViewTab, setMobileViewTab] = useState<'answer' | 'evidence'>('answer')

  const answerSectionRef = useRef<HTMLDivElement>(null)

  // Fetch health diagnostics and category metadata on mount
  useEffect(() => {
    let isMounted = true

    const loadInitialMetadata = async () => {
      setIsLoadingHealth(true)
      try {
        const [healthRes, catsRes] = await Promise.allSettled([
          knowledgeApi.getAnswerHealth(),
          knowledgeApi.getCategories(),
        ])

        if (isMounted) {
          if (healthRes.status === 'fulfilled') {
            setHealth(healthRes.value)
          }
          if (catsRes.status === 'fulfilled') {
            setCategoriesMeta(catsRes.value)
          }
        }
      } catch {
        // Non-blocking fallback
      } finally {
        if (isMounted) {
          setIsLoadingHealth(false)
        }
      }
    }

    loadInitialMetadata()
    return () => {
      isMounted = false
    }
  }, [])

  // Execute Grounded Question Answering API call
  const handleAskQuestion = useCallback(
    async (queryOverride?: string) => {
      const targetQuery = (queryOverride || question).trim()
      if (!targetQuery || isGenerating) return

      setIsGenerating(true)
      setError(null)
      setSelectedCitationMarker(null)

      try {
        const res = await knowledgeApi.generateAnswer({
          query: targetQuery,
          top_k: config.topK,
          max_context_tokens: config.tokenBudget,
          max_sources: config.maxSources,
          require_citations: config.requireCitations,
          temperature: config.temperature,
          filters: {
            category: (config.categoryFilter as DocumentCategory) || undefined,
            access_levels: config.accessFilter ? [config.accessFilter as AccessLevel] : undefined,
          },
        })

        setCurrentResponse(res)

        // Record in-memory session entry
        const historyItem: SessionHistoryItem = {
          id: res.answer_id || `hist_${Date.now()}`,
          question: targetQuery,
          response: res,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }

        setSessionHistory((prev) => [historyItem, ...prev])
        setActiveHistoryId(historyItem.id)

        // Clear input composer only on successful synthesis
        setQuestion('')

        // Scroll smoothly to answer panel
        setTimeout(() => {
          answerSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 100)
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Knowledge Assistant operational query failed')
      } finally {
        setIsGenerating(false)
      }
    },
    [question, config, isGenerating]
  )

  // Handle URL query parameter ?q=... on initial mount
  useEffect(() => {
    const qParam = searchParams.get('q')
    if (qParam && qParam.trim()) {
      const decodedQ = qParam.trim()
      setQuestion(decodedQ)
      handleAskQuestion(decodedQ)
    }
  }, [searchParams, handleAskQuestion])

  // Handle selecting a citation marker [S1] from the inline answer text
  const handleCitationClick = (marker: string) => {
    setSelectedCitationMarker(marker)
    setEvidenceTab('citations')
    setMobileViewTab('evidence')
  }

  // Restore previous Q&A from in-memory session history
  const handleSelectHistoryItem = (item: SessionHistoryItem) => {
    setCurrentResponse(item.response)
    setActiveHistoryId(item.id)
    setSelectedCitationMarker(null)
    setError(null)
    setMobileViewTab('answer')
  }

  // Clear in-memory session history
  const handleClearHistory = () => {
    setSessionHistory([])
    setActiveHistoryId(null)
  }

  // Follow-up question suggestion click
  const handleSelectFollowUp = (fq: string) => {
    setQuestion(fq)
    handleAskQuestion(fq)
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#111113] text-ink select-none">
      <TopHeader title="Hospital Knowledge Assistant" />

      <main className="flex-1 p-4 md:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto w-full">
        {/* Main Header with Readiness Telemetry and Non-Clinical Notice */}
        <AssistantHeader
          health={health}
          isLoadingHealth={isLoadingHealth}
          sessionQuestionCount={sessionHistory.length}
          onToggleHistory={() => setIsHistoryOpen(true)}
          isHistoryOpen={isHistoryOpen}
        />

        {/* Question Composer Area */}
        <div className="space-y-3">
          <QuestionComposer
            question={question}
            onChange={setQuestion}
            onSubmit={() => handleAskQuestion()}
            isLoading={isGenerating}
          />

          {/* Quick-Pick Suggested Operational Inquiries */}
          {!currentResponse && !isGenerating && (
            <SuggestedQuestions
              onSelectQuestion={(q) => {
                setQuestion(q)
                handleAskQuestion(q)
              }}
              disabled={isGenerating}
            />
          )}

          {/* Collapsible Advanced Retrieval & Generation Settings */}
          <AdvancedSearchSettings
            config={config}
            onChange={setConfig}
            categoriesMeta={categoriesMeta}
            isOpen={isAdvancedOpen}
            onToggle={() => setIsAdvancedOpen(!isAdvancedOpen)}
          />
        </div>

        {/* Mobile View Tab Switcher (Visible only when answer is available on small screens) */}
        {currentResponse && !isGenerating && (
          <div className="flex lg:hidden items-center p-1 rounded-xl bg-[#19191b] border border-line">
            <button
              type="button"
              onClick={() => setMobileViewTab('answer')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                mobileViewTab === 'answer'
                  ? 'bg-[#9ba8ff] text-[#131315] font-semibold shadow-xs'
                  : 'text-[#8e8e96] hover:text-[#dedee1]'
              }`}
            >
              Grounded Answer
            </button>
            <button
              type="button"
              onClick={() => setMobileViewTab('evidence')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                mobileViewTab === 'evidence'
                  ? 'bg-[#9ba8ff] text-[#131315] font-semibold shadow-xs'
                  : 'text-[#8e8e96] hover:text-[#dedee1]'
              }`}
            >
              <span>Evidence Sources</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-white/10">
                {currentResponse.citations.length}
              </span>
            </button>
          </div>
        )}

        {/* Main Content Workspace */}
        <div ref={answerSectionRef} className="space-y-6">
          {/* State 1: Loading */}
          {isGenerating && <AssistantLoadingState />}

          {/* State 2: Error */}
          {!isGenerating && error && (
            <AssistantErrorState
              error={error}
              onRetry={() => handleAskQuestion()}
              onReset={() => {
                setError(null)
                setQuestion('')
              }}
            />
          )}

          {/* State 3: Empty Workspace (Before first question) */}
          {!isGenerating && !error && !currentResponse && (
            <AssistantEmptyState
              onSelectQuestion={(q) => {
                setQuestion(q)
                handleAskQuestion(q)
              }}
              disabled={isGenerating}
            />
          )}

          {/* State 4: Grounded Answer & Evidence Inspector */}
          {!isGenerating && !error && currentResponse && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column (Desktop 7 cols): Answer Panel & Telemetry */}
              <div
                className={`lg:col-span-7 space-y-5 ${
                  mobileViewTab === 'answer' ? 'block' : 'hidden lg:block'
                }`}
              >
                <AnswerPanel
                  response={currentResponse}
                  selectedCitationMarker={selectedCitationMarker}
                  onCitationClick={handleCitationClick}
                  onSelectFollowUp={handleSelectFollowUp}
                />

                {currentResponse.metadata && (
                  <GenerationMetadataPanel metadata={currentResponse.metadata} />
                )}
              </div>

              {/* Right Column (Desktop 5 cols): Evidence Inspector & Sources */}
              <div
                className={`lg:col-span-5 space-y-5 lg:sticky lg:top-4 ${
                  mobileViewTab === 'evidence' ? 'block' : 'hidden lg:block'
                }`}
              >
                <CitationEvidencePanel
                  citations={currentResponse.citations}
                  retrievedSources={currentResponse.retrieved_sources}
                  selectedMarker={selectedCitationMarker}
                  onSelectMarker={setSelectedCitationMarker}
                  activeTab={evidenceTab}
                  onTabChange={setEvidenceTab}
                />
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Slide-over In-Memory Session History Drawer */}
      <SessionHistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        items={sessionHistory}
        activeItemId={activeHistoryId}
        onSelectItem={handleSelectHistoryItem}
        onClearHistory={handleClearHistory}
      />
    </div>
  )
}
export default KnowledgeAssistant
