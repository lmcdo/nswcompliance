'use client';

import { useState, useEffect } from 'react';

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
 * isDaMode is per-address: stored as ce_isDaMode_${address} so enabling DA mode
 * for one property does not bleed into a different property.
 */
export function useAssessmentUI(address?: string | null): UseAssessmentUIReturn {
  const [viewMode, setViewMode] = useState<ViewMode>('sepp');
  const [showZoneInfo, setShowZoneInfo] = useState(false);
  const [buildingHeight, setBuildingHeight] = useState<number | null>(null);
  const [isDaMode, setIsDaModeState] = useState<boolean>(false);

  const toggleZoneInfo = () => setShowZoneInfo((prev) => !prev);

  // Load per-address DA mode state whenever address changes.
  // Defaults to false for any address that hasn't explicitly had DA mode enabled.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!address) {
      setIsDaModeState(false);
      return;
    }
    const stored = localStorage.getItem(`ce_isDaMode_${address}`) === 'true';
    setIsDaModeState(stored);
  }, [address]);

  const setIsDaMode = (mode: boolean) => {
    setIsDaModeState(mode);
    if (typeof window !== 'undefined' && address) {
      localStorage.setItem(`ce_isDaMode_${address}`, String(mode));
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
