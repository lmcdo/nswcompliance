import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

// Restructured contamination data to match expected format
const contaminationData = {
  title: "Preliminary Contamination Investigation Required",
  description: "Consent authority must consider contamination before approving development. Preliminary investigation mandatory for industrial/commercial to sensitive use conversions.",
  categories: [
    {
      name: "When Investigation is Required",
      reference: "SEPP R&H 2021, Section 4.6(4)",
      legal_citation: "Development on land that has been used for industrial, commercial or agricultural purposes requires preliminary contamination assessment before residential, educational, recreational, child care, or hospital use.",
      requirements: [
        {
          trigger: "Change of use from industrial/commercial to residential",
          action: "Preliminary contamination investigation mandatory"
        },
        {
          trigger: "Change to educational, recreational, child care, or hospital use",
          action: "Contamination assessment required if land has industrial/commercial history"
        },
        {
          trigger: "Land within EPA-declared investigation areas",
          action: "Contamination report required with DA"
        },
        {
          high_risk_zones: "IN1, IN2, E4, E5, B5, B6, B7",
          note: "Industrial zones - investigation almost certain for residential conversion"
        }
      ]
    },
    {
      name: "Cost & Timeline Impact",
      reference: "Feasibility Assessment",
      requirements: [
        {
          cost_type: "Preliminary Investigation (Phase 1)",
          cost_range: "$8,000 - $15,000",
          timeline: "4-6 weeks",
          deliverable: "Report by accredited consultant (NSW EPA or CEnvP)"
        },
        {
          cost_type: "Remediation (if contamination found)",
          cost_range: "$50,000 - $200,000+",
          timeline: "3-12 months",
          note: "May exceed $500k for severe contamination - potential deal breaker"
        },
        {
          approval_impact: "DA approval delayed pending investigation report",
          risk_level: "HIGH - severe contamination may make development unviable"
        }
      ]
    },
    {
      name: "Compliance Requirements",
      reference: "SEPP R&H 2021, Sections 4.6-4.8",
      requirements: [
        {
          requirement: "Engage accredited contamination consultant",
          standard: "NSW EPA approved or CEnvP (Certified Environmental Practitioner)"
        },
        {
          requirement: "Submit preliminary investigation report with DA",
          standard: "Report must address Table 1 contaminating activities"
        },
        {
          requirement: "Category 1 remediation work",
          standard: "Requires separate development consent (Section 4.8)"
        },
        {
          requirement: "Land suitability",
          standard: "Must be suitable (or remediated) before occupation certificate"
        }
      ]
    }
  ]
};

try {
  console.log('Updating contamination requirement structure...');
  
  const result = await pool.query(`
    UPDATE sepp_structured_requirements
    SET requirement_data = $1,
        updated_at = NOW()
    WHERE sepp_id = 'resilience_hazards_2021'
    AND section = '4.6'
    RETURNING id, sepp_id, section, section_name
  `, [JSON.stringify(contaminationData)]);
  
  if (result.rowCount > 0) {
    console.log('[OK] Updated contamination requirement:', result.rows[0]);
    console.log('');
    console.log('Structure now matches expected format:');
    console.log('  - title:', contaminationData.title);
    console.log('  - categories:', contaminationData.categories.length);
    contaminationData.categories.forEach(cat => {
      console.log('    -', cat.name, ':', cat.requirements.length, 'requirements');
    });
  } else {
    console.log('[WARNING] No rows updated - contamination record may not exist yet');
    console.log('Run insert_contamination.mjs first to create the record');
  }
  
} catch (error) {
  console.error('[ERROR]', error.message);
} finally {
  await pool.end();
}
