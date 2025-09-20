import { useState, useCallback } from 'react';

interface VersionInfo {
  document_type: string;
  document_id: string;
  version: string;
  effective_date?: string;
  superseded_date?: string;
}

interface UseVersionReturn {
  selectedVersion: string;
  asAtDate: string | null;
  versionInfo: VersionInfo[];
  setSelectedVersion: (version: string) => void;
  setAsAtDate: (date: string | null) => void;
  addVersionInfo: (info: VersionInfo) => void;
  clearVersionInfo: () => void;
}

export const useVersion = (): UseVersionReturn => {
  const [selectedVersion, setSelectedVersion] = useState<string>('current');
  const [asAtDate, setAsAtDate] = useState<string | null>(null);
  const [versionInfo, setVersionInfo] = useState<VersionInfo[]>([]);

  const addVersionInfo = useCallback((info: VersionInfo) => {
    setVersionInfo(prev => {
      // Avoid duplicates
      const exists = prev.some(
        item => item.document_type === info.document_type &&
                item.document_id === info.document_id
      );

      if (exists) {
        return prev.map(item =>
          item.document_type === info.document_type &&
          item.document_id === info.document_id
            ? info
            : item
        );
      }

      return [...prev, info];
    });
  }, []);

  const clearVersionInfo = useCallback(() => {
    setVersionInfo([]);
  }, []);

  return {
    selectedVersion,
    asAtDate,
    versionInfo,
    setSelectedVersion,
    setAsAtDate,
    addVersionInfo,
    clearVersionInfo
  };
};

export default useVersion;