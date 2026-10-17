import React from 'react'

interface BrandMarkProps {
  size?: number
  className?: string
  strokeWidth?: number
  strokeColor?: string
  animated?: boolean
}

export const BrandMark: React.FC<BrandMarkProps> = ({
  size = 32,
  className = '',
  strokeWidth = 2.65,
  strokeColor = '#e8e9ee',
  animated = false,
}) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 48 48"
      width={size}
      height={size}
      role="img"
      aria-label="HospitalOps open H bridge monogram"
      className={`overflow-visible flex-shrink-0 ${className}`}
    >
      <path
        d="M13 10V38M35 10V38M13 24H18.5C22.5 24 22.5 16.5 26.5 16.5S30.5 24 35 24"
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        style={
          animated
            ? {
                strokeDasharray: 120,
                strokeDashoffset: 120,
                animation: 'drawMark 0.82s cubic-bezier(0.25, 0.7, 0.2, 1) 0.06s forwards',
              }
            : undefined
        }
      />
    </svg>
  )
}
