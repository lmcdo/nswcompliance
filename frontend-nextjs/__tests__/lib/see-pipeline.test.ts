import { SEEDocumentData } from '@/lib/see/types';
import { ProvisionForPDF, PropertyContext } from '@/lib/pdf/types';

function makeProvision(id, da_status) {
  return { id, provision_text: "Provision " + id, v2_marker: "control", v2_topic: "setbacks",
    document_name: "DCP", v2_dcp_part: "Part 2", pdf_printed_page: id, da_status };
}

function makeProperty(overrides = {}) {
  return { address: "1 Test St", zone: "R2 Low Density Residential", former_council: "marrickville",
    heritage_status: { in_hca: false }, ...overrides };
}

function determineDevelopmentPathway(zone, heritage_in_hca, heritage_item) {
  if (heritage_item) return { pathway: "Development Application (DA)", reason: "Heritage item" };
  if (heritage_in_hca) return { pathway: "Development Application (DA)", reason: "Heritage conservation area" };
  const HOUSING_SEPP_ZONES = ["R1","R2","R3","R4","B1","B2","B4"];
  const zoneCode = zone.split(" ")[0];
  if (HOUSING_SEPP_ZONES.includes(zoneCode)) return { pathway: "Complying Development (CDC)", reason: zoneCode + " zone — Housing SEPP 2021 CDC pathway available" };
  return { pathway: "Development Application (DA)", reason: zoneCode + " zone — check exempt development criteria" };
}

describe('SEEDocumentData shape', () => {
  test('annotated_provisions only contains provisions with da_status', () => {
    const all = [makeProvision(1,"complies"), makeProvision(2,"varies"), makeProvision(3,"not_applicable"), makeProvision(4), makeProvision(5)];
    const annotated = all.filter(p => p.da_status);
    const data = { property: makeProperty(), development_description: "Rear extension", annotated_provisions: annotated, all_provisions: all, generated_date: "27 Feb 2026" };
    expect(data.annotated_provisions).toHaveLength(3);
    expect(data.all_provisions).toHaveLength(5);
    expect(data.annotated_provisions.every(p => p.da_status !== undefined)).toBe(true);
  });

  test('annotated provision ids all exist in all_provisions', () => {
    const all = [1,2,3,4,5].map(id => makeProvision(id, id <= 3 ? "complies" : undefined));
    const annotated = all.filter(p => p.da_status);
    const data = { property: makeProperty(), development_description: "", annotated_provisions: annotated, all_provisions: all, generated_date: "" };
    const allIds = new Set(data.all_provisions.map(p => p.id));
    data.annotated_provisions.forEach(p => expect(allIds.has(p.id)).toBe(true));
  });
});

describe('provision bucketing', () => {
  const provisions = [makeProvision(1,"complies"), makeProvision(2,"complies"), makeProvision(3,"varies"), makeProvision(4,"not_applicable"), makeProvision(5,"varies"), makeProvision(6)];
  const annotated = provisions.filter(p => p.da_status);

  test('varies bucket correct', () => {
    const varies = annotated.filter(p => p.da_status === "varies");
    expect(varies).toHaveLength(2);
    expect(varies.every(p => p.da_status === "varies")).toBe(true);
  });

  test('complies bucket correct', () => {
    const complies = annotated.filter(p => p.da_status === "complies");
    expect(complies).toHaveLength(2);
  });

  test('not_applicable bucket correct', () => {
    const na = annotated.filter(p => p.da_status === "not_applicable");
    expect(na).toHaveLength(1);
    expect(na[0].id).toBe(4);
  });

  test('unannotated provisions excluded from all buckets', () => {
    const all = [...annotated.filter(p => p.da_status === "varies"), ...annotated.filter(p => p.da_status === "complies"), ...annotated.filter(p => p.da_status === "not_applicable")];
    expect(all.find(p => p.id === 6)).toBeUndefined();
  });

  test('buckets exhaustive over annotated set', () => {
    const v = annotated.filter(p => p.da_status === "varies").length;
    const c = annotated.filter(p => p.da_status === "complies").length;
    const n = annotated.filter(p => p.da_status === "not_applicable").length;
    expect(v + c + n).toBe(annotated.length);
  });
});

describe('determineDevelopmentPathway', () => {
  test('heritage item forces DA regardless of zone', () => {
    expect(determineDevelopmentPathway("R2 Low Density Residential", false, true).pathway).toBe("Development Application (DA)");
  });
  test('HCA forces DA pathway', () => {
    expect(determineDevelopmentPathway("R2 Low Density Residential", true, false).pathway).toBe("Development Application (DA)");
  });
  test('R2 zone gets CDC pathway', () => {
    const r = determineDevelopmentPathway("R2 Low Density Residential", false, false);
    expect(r.pathway).toBe("Complying Development (CDC)");
    expect(r.reason).toContain("R2");
    expect(r.reason).toContain("Housing SEPP 2021");
  });
  test('all Housing SEPP zones get CDC', () => {
    ["R1","R2","R3","R4","B1","B2","B4"].forEach(code => {
      expect(determineDevelopmentPathway(code + " Zone", false, false).pathway).toBe("Complying Development (CDC)");
    });
  });
  test('E3, RE1, SP2 get DA pathway', () => {
    ["E3 Environmental Management","RE1 Public Recreation","SP2 Infrastructure"].forEach(zone => {
      expect(determineDevelopmentPathway(zone, false, false).pathway).toBe("Development Application (DA)");
    });
  });
  test('heritage item takes priority over HCA', () => {
    expect(determineDevelopmentPathway("R2", true, true).reason).toContain("Heritage item");
  });
});