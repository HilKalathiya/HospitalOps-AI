import React from 'react'
import {
  CheckCircle2,
  AlertTriangle,
  Info,
  ShieldAlert,
  Clock,
  XCircle,
} from 'lucide-react'
import { AnswerStatus, AnswerType } from '../../api/knowledge'

interface AnswerStatusBadgeProps {
  status: AnswerStatus
  answerType?: AnswerType
  confidence?: string
  className?: string
}

export const AnswerStatusBadge: React.FC<AnswerStatusBadgeProps> = ({
  status,
  answerType,
  confidence,
  className = '',
}) => {
  const getBadgeConfig = () => {
    switch (status) {
      case 'ANSWERED':
        return {
          icon: CheckCircle2,
          label: 'Grounded Answer · Verified Citations',
          colorClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
          iconColor: 'text-emerald-400',
        }
      case 'PARTIAL_ANSWER':
        return {
          icon: AlertTriangle,
          label: 'Partial Answer · Limited Evidence',
          colorClass: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
          iconColor: 'text-amber-400',
        }
      case 'INSUFFICIENT_EVIDENCE':
        return {
          icon: Info,
          label: 'Abstained · Insufficient Document Evidence',
          colorClass: 'bg-white/5 text-[#a5a5ac] border-white/10',
          iconColor: 'text-[#a5a5ac]',
        }
      case 'CONFLICTING_EVIDENCE':
        return {
          icon: AlertTriangle,
          label: 'Conflicting Evidence Across Sources',
          colorClass: 'bg-purple-500/10 text-purple-400 border-purple-500/25',
          iconColor: 'text-purple-400',
        }
      case 'OUT_OF_SCOPE':
        return {
          icon: ShieldAlert,
          label: 'Clinical Query Rejected · Operational Scope Only',
          colorClass: 'bg-red-500/10 text-red-400 border-red-500/25',
          iconColor: 'text-red-400',
        }
      case 'GENERATION_UNAVAILABLE':
        return {
          icon: Clock,
          label: 'Generation Subsystem Unavailable',
          colorClass: 'bg-gray-500/10 text-gray-400 border-gray-500/25',
          iconColor: 'text-gray-400',
        }
      case 'FAILED':
      default:
        return {
          icon: XCircle,
          label: 'Answer Synthesis Failed',
          colorClass: 'bg-red-500/10 text-red-400 border-red-500/25',
          iconColor: 'text-red-400',
        }
    }
  }

  const { icon: Icon, label, colorClass, iconColor } = getBadgeConfig()

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border ${colorClass}`}
        role="status"
      >
        <Icon className={`w-3.5 h-3.5 ${iconColor}`} />
        <span>{label}</span>
      </span>

      {answerType && (
        <span className="px-2 py-0.5 rounded text-[10.5px] font-mono bg-white/5 text-[#8e8e96] border border-line">
          Type: {answerType.replace(/_/g, ' ')}
        </span>
      )}

      {confidence && (
        <span
          className={`px-2 py-0.5 rounded text-[10.5px] font-mono border ${
            confidence.toUpperCase() === 'HIGH'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : confidence.toUpperCase() === 'MODERATE'
              ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
              : confidence.toUpperCase() === 'LOW'
              ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
              : 'bg-white/5 text-[#8e8e96] border-line'
          }`}
        >
          Confidence: {confidence}
        </span>
      )}
    </div>
  )
}
