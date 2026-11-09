/**
 * The clause label printed beside a rule in the clause lists. Real stored rows (production, 2026-11-09), proven clauses
 * whose heading carries no plain number: before this, they printed the page only.
 */
import { briefClauseLabel } from '@/lib/plan-brief';

describe('briefClauseLabel', () => {
  test('a numeric heading keeps the label it always had', () => {
    expect(briefClauseLabel('3.2.3 Side setbacks', 'Blacktown_DCP_2015__x__3_2_3')).toBe('3.2.3');
  });
  test('Hornsby: heading is not a number, ref_number tail is the clause', () => {
    expect(briefClauseLabel('Prescriptive Measures', 'Hornsby_DCP_2024__hornsby_dcp_2024_part3_residential__3_1_2 a')).toBe('3.1.2 a');
  });
  test('Waverley: letter-prefixed clause keeps its chapter letter', () => {
    expect(briefClauseLabel('C1 1.2.1 a 1.2.1 Front and rear building line', 'Waverley_DCP_2022__waverley_dcp_2022__C1 1_2_1 a')).toBe('C1 1.2.1 a');
    expect(briefClauseLabel('B8 8.7.1 a 8.7.1 All Development', 'Waverley_DCP_2022__waverley_dcp_2022__B8 8_7_1 a')).toBe('B8 8.7.1 a');
  });
  test('Northern Beaches: objective codes', () => {
    expect(briefClauseLabel('O17 Objectives and Requirements', 'Warringah_DCP_2011__warringah_dcp_2011_full__O17')).toBe('O17');
  });
  test('Ashfield: the ref tail is "Part 1" (not a clause), so the heading code is used', () => {
    expect(briefClauseLabel('DS3.3', 'Inner_West_Ashfield_DCP_2016__chapter_f_dev_category__Part 1')).toBe('DS3.3');
  });
  test('Ku-ring-gai: digit-letter section codes', () => {
    expect(briefClauseLabel('4A.2 1.5m side setback single storey building', 'KDCP__section_a_part_4_dwelling_houses__4A_2 1.5m side setback single storey building')).toBe('4A.2');   // not the whole ref text
    expect(briefClauseLabel('14B.10 Controls Controls', null)).toBe('14B.10');
  });
  test('descriptive text after the clause identifier is never part of the label', () => {
    expect(briefClauseLabel('Prescriptive Measures', 'Hornsby_DCP__x__3_1_2 a Minimum side setback is 1.5m')).toBe('3.1.2 a');
    expect(briefClauseLabel('Prescriptive Measures', 'H__x__4_5 Minimum setback applies to all lots')).toBe('4.5');
    expect(briefClauseLabel('Prescriptive Measures', 'H__x__3_1_2 (a) Setbacks')).toBe('3.1.2 (a)');
  });
  test('a duplicate marker on the ref is dropped', () => {
    expect(briefClauseLabel('Prescriptive Measures', 'H__h__3_1_1 d~2')).toBe('3.1.1 d');
  });
  test('nothing that reads as a clause: no label (never a guess)', () => {
    expect(briefClauseLabel('Part 8', 'Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous__Part 8')).toBeNull();
    expect(briefClauseLabel('', 'Parramatta_DCP_2023_(Amendment_4)__parramatta_dcp_2023_full_')).toBeNull();
    expect(briefClauseLabel(null, null)).toBeNull();
    expect(briefClauseLabel('Prescriptive Measures', null)).toBeNull();
  });
});
