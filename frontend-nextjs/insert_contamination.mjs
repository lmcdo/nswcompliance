import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

const contaminationData = {
  title: "Preliminary Contamination Investigation Required",
  description: "Consent authority must consider contamination before approving development. Preliminary investigation mandatory for industrial/commercial to sensitive use conversions.",
  trigger_conditions: [
    "Change of use from industrial/commercial to residential, educational, recreational, child care, or hospital",
    "Land with unknown history in industrial zones proposing sensitive use",
    "Land within EPA-declared investigation areas"
  ],
  zone_risk_indicators: {
    high_risk_zones: ["IN1", "IN2", "B5", "B6", "B7"],
    medium_risk_zones: ["B4", "MU1", "RE1", "RE2"],
    note: "Industrial zones have higher likelihood of contaminating activities - investigation almost certain"
  },
  feasibility_impact: {
    cost_preliminary_investigation: {
      min_aud: 8000,
      max_aud: 15000,
      note: "Phase 1 contamination assessment by accredited consultant"
    },
    cost_if_contamination_found: {
      min_aud: 50000,
      max_aud: 200000,
      note: "Remediation costs highly variable - may exceed $500k for severe contamination"
    },
    timeline_investigation: "4-6 weeks",
    timeline_remediation: "3-12 months if contamination detected",
    approval_impact: "DA approval delayed pending investigation report",
    deal_breaker_risk: "High - severe contamination may make development unviable"
  },
  compliance_requirements: [
    "Engage accredited contamination consultant (NSW EPA or CEnvP)",
    "Submit preliminary investigation report with DA",
    "Category 1 remediation work requires separate development consent",
    "Land must be suitable (or remediated) before occupation"
  ],
  pdf_references: [
    {
      page: 20,
      section: "4.6",
      description: "Contamination consideration requirements",
      image_url: "/pdf-pages/sepp-resilience-hazards/page-20.png"
    },
    {
      page: 21,
      section: "4.6(4)",
      description: "When preliminary investigation required - trigger conditions",
      image_url: "/pdf-pages/sepp-resilience-hazards/page-21.png"
    },
    {
      page: 25,
      section: "4.8",
      description: "Category 1 remediation work requiring consent",
      image_url: "/pdf-pages/sepp-resilience-hazards/page-25.png"
    }
  ],
  external_resources: [
    {
      title: "NSW Contaminated Land Planning Guidelines",
      url: "https://www.epa.nsw.gov.au/your-environment/contaminated-land",
      description: "EPA guidance on contamination assessment and Table 1 contaminating activities"
    }
  ]
};

async function insertContamination() {
  try {
    console.log('Inserting contamination requirements...');
    const insertResult = await pool.query(`
      INSERT INTO sepp_structured_requirements (
        sepp_id, sepp_name, schedule, schedule_name, section, section_name,
        development_type_category, requirement_data, source_provision_id
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      RETURNING id, sepp_id, section, section_name
    `, [
      'resilience_hazards_2021',
      'State Environmental Planning Policy (Resilience and Hazards) 2021',
      null, 'Chapter 4: Remediation of Land', '4.6',
      'Contamination Assessment Requirements', 'residential',
      JSON.stringify(contaminationData), null
    ]);
    console.log('✅ INSERT successful:', insertResult.rows[0]);
    console.log('\nVerifying with SELECT...');
    const verifyResult = await pool.query(`
      SELECT sepp_id, section, section_name,
        requirement_data->'feasibility_impact'->>'timeline_investigation' as timeline,
        requirement_data->'feasibility_impact'->'cost_preliminary_investigation'->>'min_aud' as cost_min,
        requirement_data->'feasibility_impact'->'cost_preliminary_investigation'->>'max_aud' as cost_max
      FROM sepp_structured_requirements
      WHERE sepp_id = 'resilience_hazards_2021' AND section = '4.6'
    `);
    console.log('✅ VERIFICATION:', verifyResult.rows[0]);
  } catch (error) {
    console.error('❌ Error:', error.message);
    if (error.code === '23505') {
      console.log('Row already exists - fetching...');
      const existing = await pool.query(`
        SELECT sepp_id, section, section_name, 
          requirement_data->'feasibility_impact'->>'timeline_investigation' as timeline
        FROM sepp_structured_requirements
        WHERE sepp_id = 'resilience_hazards_2021' AND section = '4.6'
      `);
      console.log('Existing:', existing.rows[0]);
    }
  } finally {
    await pool.end();
  }
}

insertContamination();
