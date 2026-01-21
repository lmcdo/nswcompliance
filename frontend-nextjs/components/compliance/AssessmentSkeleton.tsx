'use client';

/**
 * Assessment Loading Skeletons
 *
 * Show content structure while data loads.
 * Research shows skeleton screens feel 20-30% faster than spinners.
 *
 * @see https://blog.logrocket.com/ux-design/skeleton-loading-screen-design/
 */

import { Skeleton } from '@/components/ui/skeleton';

/**
 * Skeleton for text lines
 */
export function SkeletonText({
  lines = 3,
  className = ''
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-4 ${i === lines - 1 ? 'w-3/5' : 'w-full'}`}
        />
      ))}
    </div>
  );
}

/**
 * Skeleton for a card with header and content
 */
export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-white border rounded-lg p-4 ${className}`}>
      <Skeleton className="h-5 w-1/3 mb-4" />
      <SkeletonText lines={3} />
    </div>
  );
}

/**
 * Skeleton for the SEPP/LEP tab content
 */
export function SkeletonSeppContent() {
  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      {/* Header skeleton */}
      <div className="bg-white border rounded-lg p-4">
        <Skeleton className="h-6 w-48 mb-2" />
        <Skeleton className="h-4 w-64" />
      </div>

      {/* Cards skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>

      {/* List skeleton */}
      <div className="bg-white border rounded-lg p-4">
        <Skeleton className="h-5 w-40 mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-start gap-3">
              <Skeleton className="h-4 w-4 rounded-full flex-shrink-0 mt-0.5" />
              <Skeleton className="h-4 flex-1" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton for the DCP provisions tab (TOC structure)
 */
export function SkeletonDcpContent() {
  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      {/* TOC header */}
      <div className="bg-white border rounded-lg p-4">
        <Skeleton className="h-6 w-56 mb-2" />
        <Skeleton className="h-4 w-32" />
      </div>

      {/* TOC sections */}
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="bg-white border rounded-lg overflow-hidden">
          {/* Section header */}
          <div className="p-4 border-b bg-gray-50">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-5 w-16" />
            </div>
          </div>
          {/* Section content */}
          <div className="p-4">
            <div className="space-y-3">
              {Array.from({ length: 2 }).map((_, j) => (
                <div key={j} className="flex items-start gap-3">
                  <Skeleton className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-full mb-1" />
                    <Skeleton className="h-3 w-3/4" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton for property details panel
 */
export function SkeletonPropertyDetails() {
  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      {/* Zone badge */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-6 w-12 rounded-full" />
        <Skeleton className="h-6 w-32" />
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Skeleton className="h-3 w-16 mb-1" />
          <Skeleton className="h-5 w-24" />
        </div>
        <div>
          <Skeleton className="h-3 w-20 mb-1" />
          <Skeleton className="h-5 w-28" />
        </div>
        <div>
          <Skeleton className="h-3 w-12 mb-1" />
          <Skeleton className="h-5 w-20" />
        </div>
        <div>
          <Skeleton className="h-3 w-14 mb-1" />
          <Skeleton className="h-5 w-24" />
        </div>
      </div>

      {/* Constraints */}
      <div className="pt-2 border-t">
        <Skeleton className="h-4 w-24 mb-2" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      </div>
    </div>
  );
}

/**
 * Inline loading indicator for tabs
 */
export function TabLoadingIndicator({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-gray-500">
      <div className="flex items-center gap-3">
        <div className="h-5 w-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
        <span className="text-sm">Loading {label}...</span>
      </div>
    </div>
  );
}
