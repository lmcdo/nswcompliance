'use client';

import { useState } from 'react';

type ViewMode = 'sepp-lep' | 'dcp';

interface UseAssessmentUIReturn {
  // View mode
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;

  // Zone info modal
  showZoneInfo: boolean;
  setShowZoneInfo: (show: boolean) => void;
  toggleZoneInfo: () => void;

  // Building height input
  buildingHeight: number | null;
  setBuildingHeight: (height: number | null) => void;
}

/**
 * Hook for managing assessment page UI state.
 * Handles view mode tabs, modal visibility, and building height input.
 */
export function useAssessmentUI(): UseAssessmentUIReturn {
  const [viewMode, setViewMode] = useState<ViewMode>('sepp-lep');
  const [showZoneInfo, setShowZoneInfo] = useState(false);
  const [buildingHeight, setBuildingHeight] = useState<number | null>(null);

  const toggleZoneInfo = () => setShowZoneInfo((prev) => !prev);

  return {
    viewMode,
    setViewMode,
    showZoneInfo,
    setShowZoneInfo,
    toggleZoneInfo,
    buildingHeight,
    setBuildingHeight,
  };
}
