// prior-art-checked: lib/see/devTypes.ts holds the picker vocabulary and
// /api/dcp/structured-controls holds the controls vocabulary; no module joined
// them. This file is that join (data only) plus the one shared "picked project"
// value, so the "Your project" summary and the DCP tab agree.

import { useSyncExternalStore } from 'react';
import { DEV_TYPE_OPTIONS } from '@/lib/see/devTypes';

/**
 * DEV_TYPE_OPTIONS value -> the dev_type key used by /api/dcp/structured-controls.
 * `null` means "we hold no key controls for this project type": the summary then
 * says so and shows nothing. A type missing from this table is also treated as
 * unmapped, never guessed (see projectTypeToControlsDevType).
 */
export const PROJECT_TYPE_TO_CONTROLS_DEV_TYPE: Record<string, string | null> = {
  new_dwelling: 'dwelling_house',
  extension_single: 'dwelling_house',
  extension_double: 'dwelling_house',
  alterations: 'dwelling_house',
  secondary_dwelling: 'secondary_dwelling',
  dual_occupancy: 'dual_occupancy',
  change_of_use: null,
  subdivision: null,
  other: null,
};

export const DEFAULT_PROJECT_TYPE = DEV_TYPE_OPTIONS[0].value;

export function projectTypeToControlsDevType(projectType: string): string | null {
  return Object.prototype.hasOwnProperty.call(PROJECT_TYPE_TO_CONTROLS_DEV_TYPE, projectType)
    ? PROJECT_TYPE_TO_CONTROLS_DEV_TYPE[projectType]
    : null;
}

// ── Shared picked project type (module-level store) ──────────────────────────
let picked: string | null = null;
const listeners = new Set<() => void>();

export function setSharedProjectType(value: string | null): void {
  if (picked === value) return;
  picked = value;
  listeners.forEach((l) => l());
}

export function getSharedProjectType(): string | null {
  return picked;
}

function subscribe(l: () => void): () => void {
  listeners.add(l);
  return () => { listeners.delete(l); };
}

/** The raw shared value: null until someone (summary or DCP tab) has picked one. */
export function useSharedProjectTypeRaw(): string | null {
  return useSyncExternalStore(subscribe, getSharedProjectType, () => null);
}
