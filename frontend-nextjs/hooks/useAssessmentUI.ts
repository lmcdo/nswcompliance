'use client';

import { useState } from 'react';

type ViewMode = 'sepp' | 'lep' | 'dcp';

const DA_MODE_KEY = 'ce_isDaMode';

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
 * isDaMode persists to localStorage so it survives page refresh.
 */
export function useAssessmentUI(): UseAssessmentUIReturn {
  const [viewMode, setViewMode] = useState<ViewMode>('sepp');
  const [showZoneInfo, setShowZoneInfo] = useState(false);
  const [buildingHeight, setBuildingHeight] = useState<number | null>(null);
  const [isDaMode, setIsDaModeState] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(DA_MODE_KEY) === 'true';
  });

  const toggleZoneInfo = () => setShowZoneInfo((prev) => !prev);

  const setIsDaMode = (mode: boolean) => {
    setIsDaModeState(mode);
    if (typeof window !== 'undefined') {
      localStorage.setItem(DA_MODE_KEY, String(mode));
    }
  };

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
