import React from 'react'
import {
  History,
  X,
  Trash2,
  Clock,
  BookMarked,
  ArrowRight,
} from 'lucide-react'
import { SessionHistoryItem } from '../../types/assistant'

interface SessionHistoryDrawerProps {
  isOpen: boolean
  onClose: () => void
  items: SessionHistoryItem[]
  activeItemId: string | null
  onSelectItem: (item: SessionHistoryItem) => void
  onClearHistory: () => void
  className?: string
}

export const SessionHistoryDrawer: React.FC<SessionHistoryDrawerProps> = ({
  isOpen,
  onClose,
  items,
  activeItemId,
  onSelectItem,
  onClearHistory,
  className = '',
}) => {
  if (!isOpen) return null

  return (
    <div className={`fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs ${className}`}>
      <div className="w-full max-w-md bg-[#19191b] border-l border-line h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="p-4 border-b border-line flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-[#9ba8ff]" />
            <h3 className="text-sm font-semibold text-[#f0f0f3]">Session Question History</h3>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/5 text-[#8e8e96] border border-line">
              {items.length} {items.length === 1 ? 'entry' : 'entries'}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="text-[#8e8e96] hover:text-[#f0f0f3] p-1 rounded hover:bg-white/5 transition-colors cursor-pointer"
            title="Close drawer"
            aria-label="Close session history drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Privacy Notice Banner */}
        <div className="p-3 bg-white/[0.02] border-b border-line/60 text-[11px] text-[#8e8e96] leading-relaxed">
          <div className="flex items-center gap-1.5 font-medium text-[#dedee1] mb-0.5">
            <Clock className="w-3.5 h-3.5 text-[#9ba8ff]" />
            <span>Browser-Session Memory Only</span>
          </div>
          Questions and responses are held temporarily in-memory for this browser tab only. Nothing is persisted to local storage or shared between users. Each question is executed independently without conversational chaining.
        </div>

        {/* History Items List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {items.length === 0 ? (
            <div className="text-center py-12 space-y-2 text-[#8e8e96]">
              <History className="w-8 h-8 mx-auto text-[#38383e]" />
              <p className="text-xs">No questions asked in this session yet.</p>
              <p className="text-[11px] text-[#6f6f78]">
                Your recent inquiries and verified answers will appear here for quick review.
              </p>
            </div>
          ) : (
            items.map((item) => {
              const isActive = activeItemId === item.id
              const isClinical = item.response.is_clinical_query || item.response.status === 'OUT_OF_SCOPE'
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    onSelectItem(item)
                    onClose()
                  }}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer space-y-2 ${
                    isActive
                      ? 'border-[#9ba8ff] bg-[#9ba8ff]/10 ring-1 ring-[#9ba8ff]/40 shadow-xs'
                      : 'border-line hover:border-[#38383e] bg-[#141416]/70 hover:bg-[#141416]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-semibold text-[#f0f0f3] line-clamp-2 leading-snug">
                      {item.question}
                    </p>
                    <ArrowRight className="w-3.5 h-3.5 text-[#6f6f78] shrink-0 mt-0.5" />
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-1.5 text-[10px] font-mono text-[#8e8e96] pt-1 border-t border-line/40">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-1.5 py-0.2 rounded font-medium ${
                          isClinical
                            ? 'bg-red-500/15 text-red-300'
                            : item.response.status === 'ANSWERED'
                            ? 'bg-emerald-500/15 text-emerald-300'
                            : 'bg-amber-500/15 text-amber-300'
                        }`}
                      >
                        {item.response.status}
                      </span>
                      {item.response.citations.length > 0 && (
                        <span className="flex items-center gap-1 text-[#9ba8ff]">
                          <BookMarked className="w-3 h-3" />
                          <span>{item.response.citations.length} sources</span>
                        </span>
                      )}
                    </div>
                    <span>{item.timestamp}</span>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Drawer Footer Actions */}
        {items.length > 0 && (
          <div className="p-3 border-t border-line flex items-center justify-between">
            <button
              type="button"
              onClick={onClearHistory}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear Session History</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 hover:bg-white/10 text-[#dedee1] hover:text-[#f0f0f3] border border-line transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
