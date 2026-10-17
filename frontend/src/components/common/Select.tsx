import React, { useState, useRef, useEffect, useId } from 'react'
import { ChevronDown, Check } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface SelectOption {
  value: string
  label: string
  description?: string
}

export interface SelectProps {
  value: string
  onChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  label?: string
  className?: string
  triggerClassName?: string
  disabled?: boolean
  width?: string
  align?: 'left' | 'right'
}

export const Select: React.FC<SelectProps> = ({
  value,
  onChange,
  options,
  placeholder = 'Select an option',
  label,
  className,
  triggerClassName,
  disabled = false,
  width = 'w-auto',
  align = 'left'
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const listboxId = useId()

  const selectedOption = options.find((opt) => opt.value === value)

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick)
    }

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
    }
  }, [isOpen])

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return

    if (e.key === 'Escape') {
      setIsOpen(false)
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      setIsOpen((prev) => !prev)
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (!isOpen) {
        setIsOpen(true)
      } else {
        const currentIndex = options.findIndex((opt) => opt.value === value)
        const nextIndex = currentIndex < options.length - 1 ? currentIndex + 1 : 0
        onChange(options[nextIndex].value)
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (!isOpen) {
        setIsOpen(true)
      } else {
        const currentIndex = options.findIndex((opt) => opt.value === value)
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : options.length - 1
        onChange(options[prevIndex].value)
      }
    }
  }

  return (
    <div className={cn("relative inline-block text-left", width, className)} ref={containerRef}>
      {label && (
        <label className="block text-xs font-semibold text-[#52635B] uppercase tracking-wider mb-1">
          {label}
        </label>
      )}

      {/* Trigger Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        className={cn(
          "h-9 px-3 py-1.5 bg-[#F7F9F7] hover:bg-white text-[#192923] border border-[#DCE4DE] hover:border-[#C5D1C9] rounded-lg text-xs font-medium transition-all flex items-center justify-between gap-2.5 focus:outline-none focus:ring-1 focus:ring-[#3D8C79] focus:border-[#3D8C79] shadow-2xs disabled:opacity-50 disabled:cursor-not-allowed",
          isOpen && "bg-white border-[#3D8C79] ring-1 ring-[#3D8C79]",
          triggerClassName
        )}
      >
        <span className="truncate text-left font-medium">
          {selectedOption ? selectedOption.label : <span className="text-[#77847D]">{placeholder}</span>}
        </span>
        <ChevronDown 
          className={cn(
            "w-3.5 h-3.5 text-[#77847D] flex-shrink-0 transition-transform duration-150",
            isOpen && "rotate-180 text-[#176B57]"
          )} 
        />
      </button>

      {/* Custom Designed Dropdown Popover */}
      {isOpen && (
        <div
          id={listboxId}
          role="listbox"
          tabIndex={-1}
          style={{
            scrollbarWidth: 'none',
            msOverflowStyle: 'none'
          }}
          className={cn(
            "dropdown-options no-scrollbar absolute mt-1 min-w-[200px] min-w-full max-h-80 overflow-y-auto bg-white border border-[#DCE4DE] rounded-lg shadow-[0_8px_24px_rgba(22,42,32,0.12)] p-1 z-50 text-xs text-[#192923] focus:outline-none animate-in fade-in-50 zoom-in-95 duration-100",
            "[scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden",
            align === 'right' ? 'right-0' : 'left-0'
          )}
        >
          {options.map((option) => {
            const isSelected = option.value === value
            return (
              <div
                key={option.value}
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  onChange(option.value)
                  setIsOpen(false)
                }}
                className={cn(
                  "group flex items-center justify-between px-2.5 py-2 rounded-md cursor-pointer transition-colors select-none text-left",
                  isSelected
                    ? "bg-[#E8F2ED] text-[#155B49] font-semibold"
                    : "text-[#52635B] hover:text-[#192923] hover:bg-[#F0F3F0]"
                )}
              >
                <div className="flex flex-col min-w-0 pr-2">
                  <span className="truncate">{option.label}</span>
                  {option.description && (
                    <span className="text-2xs text-[#77847D] group-hover:text-[#52635B] truncate mt-0.5 font-normal">
                      {option.description}
                    </span>
                  )}
                </div>

                {isSelected && (
                  <Check className="w-3.5 h-3.5 text-[#176B57] flex-shrink-0 ml-2 stroke-[2.5]" />
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
