import React from 'react'

interface CitationPillProps {
  marker: string
  isSelected?: boolean
  onClick?: (marker: string) => void
  documentTitle?: string
  sectionTitle?: string | null
  className?: string
}

export const CitationPill: React.FC<CitationPillProps> = ({
  marker,
  isSelected = false,
  onClick,
  documentTitle,
  sectionTitle,
  className = '',
}) => {
  // Normalize marker display, e.g. "S1" -> "[S1]", "[S1]" -> "[S1]"
  const cleanId = marker.replace('[', '').replace(']', '')
  const displayMarker = `[${cleanId}]`

  const tooltipText = documentTitle
    ? `View evidence from: ${documentTitle}${sectionTitle ? ` · ${sectionTitle}` : ''}`
    : `View citation source ${displayMarker}`

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onClick?.(cleanId)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick?.(cleanId)
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      title={tooltipText}
      aria-label={tooltipText}
      aria-pressed={isSelected}
      className={`inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[11px] font-mono font-semibold transition-all cursor-pointer select-none focus:outline-hidden focus:ring-2 focus:ring-[#9ba8ff] ${
        isSelected
          ? 'bg-[#9ba8ff] text-[#131315] ring-2 ring-[#9ba8ff]/60 shadow-xs scale-105'
          : 'bg-[#9ba8ff]/20 text-[#c2cbff] hover:bg-[#9ba8ff]/30 hover:text-white border border-[#9ba8ff]/40'
      } ${className}`}
    >
      {displayMarker}
    </button>
  )
}
