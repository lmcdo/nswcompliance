import { assembleDescription, DEV_TYPE_OPTIONS } from '@/lib/see/devTypes';

describe('assembleDescription', () => {
  describe('expected use', () => {
    it('assembles type + works into a readable string', () => {
      const result = assembleDescription('pergola', 'open-sided timber, 4.2m x 3.6m, within the front setback');
      expect(result).toBe('Pergola / shade structure — open-sided timber, 4.2m x 3.6m, within the front setback');
    });

    it('uses the label from DEV_TYPE_OPTIONS not the key', () => {
      const result = assembleDescription('extension_single', 'rear addition');
      expect(result).toBe('Single-storey extension — rear addition');
    });

    it('trims works text whitespace', () => {
      const result = assembleDescription('deck', '  timber deck, 3m x 4m  ');
      expect(result).toBe('Deck / terrace — timber deck, 3m x 4m');
    });
  });

  describe('edge cases', () => {
    it('returns just the type label when works is empty', () => {
      expect(assembleDescription('pool', '')).toBe('Swimming pool or spa');
    });

    it('returns just works text when type is empty', () => {
      expect(assembleDescription('', 'rear extension, 4m x 6m')).toBe('rear extension, 4m x 6m');
    });

    it('returns empty string when both fields are empty', () => {
      expect(assembleDescription('', '')).toBe('');
    });

    it('returns empty string when works is only whitespace and type is empty', () => {
      expect(assembleDescription('', '   ')).toBe('');
    });

    it('falls back to raw type value when not in DEV_TYPE_OPTIONS', () => {
      const result = assembleDescription('unknown_type', 'some works');
      expect(result).toBe('unknown_type — some works');
    });
  });

  describe('DEV_TYPE_OPTIONS integrity', () => {
    it('every option has a non-empty value and label', () => {
      for (const opt of DEV_TYPE_OPTIONS) {
        expect(opt.value).toBeTruthy();
        expect(opt.label).toBeTruthy();
      }
    });

    it('no duplicate values', () => {
      const values = DEV_TYPE_OPTIONS.map(o => o.value);
      expect(new Set(values).size).toBe(values.length);
    });
  });
});
