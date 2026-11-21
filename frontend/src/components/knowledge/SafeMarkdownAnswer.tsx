import React from 'react'
import { CitationPill } from './CitationPill'
import { CitationReference } from '../../api/knowledge'

interface SafeMarkdownAnswerProps {
  content: string
  selectedCitationMarker?: string | null
  onCitationClick?: (marker: string) => void
  citations?: CitationReference[]
  className?: string
}

export const SafeMarkdownAnswer: React.FC<SafeMarkdownAnswerProps> = ({
  content,
  selectedCitationMarker,
  onCitationClick,
  citations = [],
  className = '',
}) => {
  // Map citations by marker (e.g. "S1", "[S1]") for rich tooltip metadata
  const citationMap = React.useMemo(() => {
    const map = new Map<string, CitationReference>()
    for (const c of citations) {
      const clean = c.citation_id.replace('[', '').replace(']', '')
      map.set(clean, c)
      map.set(`[${clean}]`, c)
      map.set(c.citation_marker, c)
    }
    return map
  }, [citations])

  // Helper to render inline elements: bold, inline code, and [S1] citation pills
  const renderInline = (text: string): React.ReactNode[] => {
    // Split by citation markers [S\d+]
    const citationParts = text.split(/(\[S\d+\])/g)
    const result: React.ReactNode[] = []

    citationParts.forEach((part, pIdx) => {
      const citMatch = part.match(/^\[(S\d+)\]$/)
      if (citMatch) {
        const marker = citMatch[1]
        const clean = marker.replace('[', '').replace(']', '')
        const isSelected = selectedCitationMarker === clean || selectedCitationMarker === `[${clean}]`
        const ref = citationMap.get(clean)
        result.push(
          <CitationPill
            key={`cit-${pIdx}-${marker}`}
            marker={clean}
            isSelected={isSelected}
            onClick={onCitationClick}
            documentTitle={ref?.document_title}
            sectionTitle={ref?.section_title}
          />
        )
        return
      }

      // Format bold (**bold**) and inline code (`code`) safely
      const codeRegex = /(`[^`]+`|\*\*[^*]+\*\*)/g
      const tokens = part.split(codeRegex)

      tokens.forEach((tok, tIdx) => {
        if (tok.startsWith('`') && tok.endsWith('`') && tok.length > 2) {
          result.push(
            <code
              key={`code-${pIdx}-${tIdx}`}
              className="px-1.5 py-0.5 rounded bg-black/50 text-[#c2cbff] font-mono text-[11px] border border-line/40 mx-0.5"
            >
              {tok.slice(1, -1)}
            </code>
          )
        } else if (tok.startsWith('**') && tok.endsWith('**') && tok.length > 4) {
          result.push(
            <strong key={`bold-${pIdx}-${tIdx}`} className="font-semibold text-[#f0f0f3]">
              {tok.slice(2, -2)}
            </strong>
          )
        } else if (tok) {
          result.push(tok)
        }
      })
    })

    return result
  }

  // Parse markdown content line-by-line into structured blocks
  const renderBlocks = () => {
    const lines = content.split('\n')
    const blocks: React.ReactNode[] = []
    let currentList: { type: 'ul' | 'ol'; items: string[] } | null = null
    let tableRows: string[][] = []

    const flushList = (keySuffix: string | number) => {
      if (!currentList) return
      if (currentList.type === 'ul') {
        blocks.push(
          <ul key={`ul-${keySuffix}`} className="list-disc list-inside space-y-1.5 my-2.5 text-xs text-[#dedee1]">
            {currentList.items.map((it, idx) => (
              <li key={idx} className="leading-relaxed">
                {renderInline(it)}
              </li>
            ))}
          </ul>
        )
      } else {
        blocks.push(
          <ol key={`ol-${keySuffix}`} className="list-decimal list-inside space-y-1.5 my-2.5 text-xs text-[#dedee1]">
            {currentList.items.map((it, idx) => (
              <li key={idx} className="leading-relaxed">
                {renderInline(it)}
              </li>
            ))}
          </ol>
        )
      }
      currentList = null
    }

    const flushTable = (keySuffix: string | number) => {
      if (tableRows.length === 0) return
      const headers = tableRows[0]
      const rows = tableRows.slice(1).filter((r) => !r.every((c) => c.match(/^[-:]+$/)))

      blocks.push(
        <div key={`table-${keySuffix}`} className="overflow-x-auto my-3 border border-line rounded-lg">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-white/5 border-b border-line text-[#8e8e96] font-mono text-[11px]">
                {headers.map((h, i) => (
                  <th key={i} className="px-3 py-2 font-semibold">
                    {h.trim()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line/60 font-sans">
              {rows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-white/[0.02]">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-3 py-2 text-[#dedee1]">
                      {renderInline(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      tableRows = []
    }

    lines.forEach((line, idx) => {
      const trimmed = line.trim()

      // Table row
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        flushList(idx)
        const cells = trimmed
          .slice(1, -1)
          .split('|')
          .map((c) => c.trim())
        tableRows.push(cells)
        return
      } else if (tableRows.length > 0) {
        flushTable(idx)
      }

      // Unordered list item
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const itemText = trimmed.slice(2)
        if (!currentList || currentList.type !== 'ul') {
          flushList(idx)
          currentList = { type: 'ul', items: [itemText] }
        } else {
          currentList.items.push(itemText)
        }
        return
      }

      // Ordered list item (e.g. "1. ", "2. ")
      const numMatch = trimmed.match(/^(\d+)\.\s+(.+)$/)
      if (numMatch) {
        const itemText = numMatch[2]
        if (!currentList || currentList.type !== 'ol') {
          flushList(idx)
          currentList = { type: 'ol', items: [itemText] }
        } else {
          currentList.items.push(itemText)
        }
        return
      }

      // If we were inside a list and hit normal text or blank line, flush list
      if (currentList) {
        flushList(idx)
      }

      // Blank line
      if (!trimmed) {
        return
      }

      // Headings
      if (trimmed.startsWith('### ')) {
        blocks.push(
          <h4 key={`h4-${idx}`} className="text-xs font-semibold text-[#f0f0f3] uppercase tracking-wider mt-3 mb-1">
            {renderInline(trimmed.slice(4))}
          </h4>
        )
      } else if (trimmed.startsWith('## ')) {
        blocks.push(
          <h3 key={`h3-${idx}`} className="text-sm font-semibold text-[#f0f0f3] mt-3.5 mb-1.5">
            {renderInline(trimmed.slice(3))}
          </h3>
        )
      } else if (trimmed.startsWith('# ')) {
        blocks.push(
          <h2 key={`h2-${idx}`} className="text-base font-bold text-white mt-4 mb-2">
            {renderInline(trimmed.slice(2))}
          </h2>
        )
      } else {
        // Normal paragraph
        blocks.push(
          <p key={`p-${idx}`} className="text-xs text-[#dedee1] leading-relaxed my-2">
            {renderInline(trimmed)}
          </p>
        )
      }
    })

    if (currentList) flushList('final')
    if (tableRows.length > 0) flushTable('final')

    return blocks
  }

  return <div className={`space-y-1 font-sans ${className}`}>{renderBlocks()}</div>
}
