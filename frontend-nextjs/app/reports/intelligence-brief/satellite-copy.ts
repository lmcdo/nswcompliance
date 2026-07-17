// Flood-card copy helpers (satellite pass-through parity). Pure string
// builders so the exact wording is unit-testable. Register: these sentences
// state what a mapping source recorded at this location — mapped-extent facts
// only, never a conclusion about the property itself.

export interface EmsActivation {
  activation_id?: string | null;
  event_name?: string | null;
  event_date?: string | null;
  flood_type?: string | null;
}

// The engine's computed screening signal — presented as a screening output
// with its provenance, never a bare verdict.
export function floodSignalLine(signal: string): string {
  return `Flood screening signal: ${signal} — computed from the sources below.`;
}

// Copernicus EMS point-in-polygon result. true = a mapped flood extent
// intersected this location during the named activation ("mapped extent"
// wording — never a claim that the property flooded). false = checked, no
// mapped extent recorded here. Callers treat null/undefined as "don't render".
export function emsLine(detected: boolean, activations?: EmsActivation[] | null): string {
  if (!detected) {
    return 'No Copernicus emergency-mapping flood extent recorded at this location.';
  }
  const events = (activations ?? [])
    .map((a) => {
      const name = a.event_name || a.activation_id;
      if (!name) return null;
      return a.event_date ? `${name} (${a.event_date})` : String(name);
    })
    .filter((e): e is string => Boolean(e));
  if (events.length === 0) {
    return 'Copernicus emergency mapping recorded flood extent intersecting this location.';
  }
  return `Copernicus emergency mapping recorded flood extent intersecting this location during ${events.join('; ')}.`;
}
