'use client';

import { useState } from 'react';

type ViewMode = 'sepp' | 'lep' | 'dcp';

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

  // DA Mode
  isDaMode: boolean;
  setIsDaMode: (mode: boolean) => void;
}

/**
 * Hook for managing assessment page UI state.
 * Handles view mode tabs, modal visibility, and building height input.
 */
export function useAssessmentUI(): UseAssessmentUIReturn {
  const [viewMode, setViewMode] = useState<ViewMode>('sepp');
  const [showZoneInfo, setShowZoneInfo] = useState(false);
  const [buildingHeight, setBuildingHeight] = useState<number | null>(null);
  const [isDaMode, setIsDaMode] = useState(false);

  const toggleZoneInfo = () => setShowZoneInfo((prev) => !prev);

  return {
    viewMode,
    setViewMode,
    showZoneInfo,
    setShowZoneInfo,
    toggleZoneInfo,
    buildingHeight,
    setBuildingHeight,
    isDaMode,
    setIsDaMode,
  };
}
