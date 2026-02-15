// Test with actual grouping logic from formatProvisions.ts
import { pdf } from '@react-pdf/renderer';
import { createElement } from 'react';
import React from 'react';
import { Page, Text, View, Document, StyleSheet } from '@react-pdf/renderer';

const response = await fetch('http://localhost:3003/api/provisions/for-property?groupBy=toc&former_council=Marrickville&zone=R2&heritage=true&hca=Llewellyn+Estate+Heritage+Conservation+Area&precinct_id=15_');
const data = await response.json();

const allProvisions = [];
if (data.success && data.data.by_layer) {
  for (const layer of data.data.by_layer) {
    allProvisions.push(...layer.provisions);
  }
}

const numericProvisions = allProvisions.filter(p => {
  const text = p.provision_text || '';
  const hasNumeric = /\d+(\.\d+)?\s*(m²|m|mm|cm|km|%|metres?|meters?|centimetres?|centimeters?)/i.test(text);
  const isObjective = /^O\d+|objective|principle|aim/i.test(text);
  return hasNumeric && !isObjective;
});

console.log(`Testing grouping with ${numericProvisions.length} provisions\n`);

// Replicate grouping logic
function groupProvisions(provisions) {
  const byMarker = provisions.reduce((acc, p) => {
    const marker = (p.v2_marker && p.v2_marker.trim())
      ? p.v2_marker.toLowerCase().trim()
      : 'other';
    if (!acc[marker]) acc[marker] = [];
    acc[marker].push(p);
    return acc;
  }, {});

  const groups = Object.entries(byMarker).map(([marker, provs]) => ({
    topic: marker,
    topicLabel: marker.toUpperCase(),
    count: provs.length,
    provisions: provs,
    // For heritage, create subtopics
    subtopics: marker === 'heritage' ? createSubtopics(provs) : undefined
  }));

  return groups;
}

function createSubtopics(provisions) {
  const bySubtopic = provisions.reduce((acc, p) => {
    const subtopic = p.v2_topic || 'General';
    if (!acc[subtopic]) acc[subtopic] = [];
    acc[subtopic].push(p);
    return acc;
  }, {});

  return Object.entries(bySubtopic).map(([subtopic, provs]) => ({
    subtopic,
    count: provs.length,
    provisions: provs
  }));
}

const groups = groupProvisions(numericProvisions);

console.log(`Created ${groups.length} groups:`);
groups.forEach(g => {
  console.log(`  ${g.topicLabel}: ${g.count} provisions${g.subtopics ? ` (${g.subtopics.length} subtopics)` : ''}`);
});

const styles = StyleSheet.create({
  page: { padding: '10mm 12mm', fontSize: 9 },
  section: { marginBottom: 16 },
  sectionTitle: { fontSize: 14, fontWeight: 'bold', marginBottom: 8 },
  tableRow: { flexDirection: 'row', padding: 6 },
  subtopicRow: { flexDirection: 'row', backgroundColor: '#fafafa', padding: 5, fontWeight: 'bold' },
  col1: { width: 30 },
  col2: { width: 80 },
  col3: { flex: 1 },
  col4: { width: 70 },
});

function sanitize(text) {
  return (text || '').replace(/-?\d+\.?\d*e[+-]?\d+/gi, '[num]');
}

function truncate(text) {
  const words = sanitize(text).trim().split(/\s+/);
  return words.length <= 100 ? sanitize(text) : words.slice(0, 100).join(' ') + '...';
}

console.log('\nTest: Rendering with grouping and subtopics...');
try {
  let provisionNumber = 0;

  const doc = createElement(Document, {},
    createElement(Page, { size: 'A4', style: styles.page, wrap: true },
      ...groups.map((group, gIdx) => {
        const groupElements = [];

        // Section title
        groupElements.push(
          createElement(Text, { key: `title-${gIdx}`, style: styles.sectionTitle },
            `${gIdx + 1}. ${group.topicLabel} (${group.count})`
          )
        );

        // If heritage with subtopics
        if (group.subtopics) {
          group.subtopics.forEach((subtopic, sIdx) => {
            // Subtopic header
            groupElements.push(
              createElement(View, { key: `sub-${gIdx}-${sIdx}`, style: styles.subtopicRow },
                createElement(Text, {}, `${subtopic.subtopic} (${subtopic.count})`)
              )
            );
            // Subtopic provisions
            subtopic.provisions.forEach((p, pIdx) => {
              provisionNumber++;
              groupElements.push(
                createElement(View, { key: `prov-${gIdx}-${sIdx}-${pIdx}`, style: styles.tableRow },
                  createElement(Text, { style: styles.col1 }, String(provisionNumber)),
                  createElement(Text, { style: styles.col2 }, subtopic.subtopic),
                  createElement(Text, { style: styles.col3 }, truncate(p.provision_text || '')),
                  createElement(Text, { style: styles.col4 }, `p.${p.pdf_printed_page || p.pdf_page || 1}`)
                )
              );
            });
          });
        } else {
          // Flat list
          group.provisions.forEach((p, pIdx) => {
            provisionNumber++;
            groupElements.push(
              createElement(View, { key: `prov-${gIdx}-${pIdx}`, style: styles.tableRow },
                createElement(Text, { style: styles.col1 }, String(provisionNumber)),
                createElement(Text, { style: styles.col2 }, p.v2_topic || '—'),
                createElement(Text, { style: styles.col3 }, truncate(p.provision_text || '')),
                createElement(Text, { style: styles.col4 }, `p.${p.pdf_printed_page || p.pdf_page || 1}`)
              )
            );
          });
        }

        return createElement(View, { key: `group-${gIdx}`, style: styles.section }, ...groupElements);
      })
    )
  );

  await pdf(doc).toBlob();
  console.log('✓ PASSED - Grouping works fine!\n');
  console.log('Issue must be in ContextSection or how React components are composed');
} catch (e) {
  console.log(`✗ FAILED: ${e.message}`);
  console.log(`Stack: ${e.stack}`);
}
