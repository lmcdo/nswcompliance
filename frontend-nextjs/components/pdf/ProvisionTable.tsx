// PDF Provision Table Component - Scannable table format

import { Text, View, Link } from '@react-pdf/renderer';
import { ProvisionGroup } from '@/lib/pdf/types';
import { formatCitation, parseParagraphsWithHighlights, sanitizeForPdf } from '@/lib/pdf/formatProvisions';
import { styles } from './styles';

interface ProvisionTableProps {
  group: ProvisionGroup;
  sectionNumber: number;
  isFirst?: boolean;
  /** R2 public PDF URL for deep-linking — appends #page=N */
  councilPdfUrl?: string;
}

export function ProvisionTable({ group, sectionNumber, isFirst = false, councilPdfUrl }: ProvisionTableProps) {
  let provisionNumber = 1;

  /** Render inline citation — as a link if council PDF URL available, plain text otherwise */
  const renderCitation = (provision: ProvisionGroup['provisions'][0]) => {
    const citation = formatCitation(provision);
    if (!citation) return null;
    const pdfPage = provision.pdf_page || provision.pdf_printed_page;
    if (councilPdfUrl && pdfPage) {
      return (
        <Link src={`${councilPdfUrl}#page=${pdfPage}`} style={{ fontSize: 7, color: '#0c4a6e', marginTop: 3, textDecoration: 'underline' }}>
          {citation}
        </Link>
      );
    }
    return (
      <Text style={{ fontSize: 7, color: '#0c4a6e', marginTop: 3 }}>{citation}</Text>
    );
  };

  return (
    <View style={{ marginTop: isFirst ? 0 : 16 }}>
      {/* Section Title */}
      <Text style={styles.sectionTitle}>
        {(() => {
          const firstProv = group.provisions[0] || (group.subtopics?.[0]?.provisions[0]);
          const partName = firstProv?.v2_dcp_part;
          return partName
            ? `${sectionNumber}. ${partName.toUpperCase()}: ${group.topicLabel.toUpperCase()} (${group.count} PROVISIONS)`
            : `${sectionNumber}. ${group.topicLabel.toUpperCase()} (${group.count} PROVISIONS)`;
        })()}
      </Text>

      {/* Table Header */}
      <View style={styles.tableHeader}>
        <Text style={[styles.tableHeaderCell, styles.colNumber]}>#</Text>
        <Text style={[styles.tableHeaderCell, styles.colProvision]}>Provision Summary</Text>
        <Text style={[styles.tableHeaderCell, styles.colResponse]}>Compliance / Response</Text>
      </View>

      {/* Table Rows */}
      {group.subtopics && group.subtopics.length > 0 ? (
        // Heritage: Group by subtopic
        group.subtopics.map((subtopic, subIdx) => (
          <View key={subIdx}>
            {/* Subtopic Header Row */}
            <View style={styles.subtopicRow}>
              <Text style={styles.colNumber}> </Text>
              <Text style={{ flexGrow: 1, flexShrink: 1, flexBasis: 'auto', color: '#374151' }}>
                {(subtopic.subtopic || 'General').toUpperCase()} ({subtopic.count} provisions)
              </Text>
            </View>

            {/* Subtopic Provisions */}
            {subtopic.provisions.map((provision, pIdx) => {
              const sanitizedText = sanitizeForPdf(provision.provision_text || '');
              const paragraphs = parseParagraphsWithHighlights(sanitizedText);

              return (
                <View key={provision.id} style={styles.tableRow}>
                  <Text style={[styles.cellNumber, styles.colNumber]}>
                    {sectionNumber}.{provisionNumber++}
                  </Text>
                  <View style={[styles.colProvision]}>
                    {paragraphs.map((para, pIdx) => (
                      <View key={pIdx}>
                        {/* Control/Objective markers - styled as badges */}
                        {para.isControlMarker ? (
                          <View style={{
                            backgroundColor: para.paragraph.startsWith('C') ? '#0c4a6e' : '#92400e',
                            paddingVertical: 3,
                            paddingHorizontal: 8,
                            borderRadius: 10,
                            alignSelf: 'flex-start',
                            marginVertical: 4
                          }}>
                            <Text style={{
                              color: '#ffffff',
                              fontFamily: 'Helvetica-Bold',
                              fontSize: 8
                            }}>
                              {para.paragraph}
                            </Text>
                          </View>
                        ) : (
                          <Text style={[
                            styles.cellProvision,
                            para.isHeader ? { fontFamily: 'Helvetica-Bold', fontSize: 11 } : {},
                            (para.isList || para.isNestedList) ? {
                              marginLeft: para.isNestedList ? 20 : 10,
                              fontSize: 9
                            } : {}
                          ]}>
                            {para.segments.map((segment, sIdx) => {
                              if (segment.isNumeric) {
                                return (
                                  <Text key={sIdx} style={{ fontFamily: 'Helvetica-Bold', color: '#0f766e' }}>
                                    {segment.text}
                                  </Text>
                                );
                              } else if (segment.isControl) {
                                return (
                                  <Text key={sIdx} style={{ fontFamily: 'Helvetica-Bold', color: '#0c4a6e' }}>
                                    {segment.text}
                                  </Text>
                                );
                              } else if (para.isHeader) {
                                // Headers: wrap all text in Text component to inherit bold
                                return (
                                  <Text key={sIdx} style={{ fontFamily: 'Helvetica-Bold' }}>
                                    {segment.text}
                                  </Text>
                                );
                              } else {
                                return segment.text;
                              }
                            })}
                          </Text>
                        )}
                        {pIdx < paragraphs.length - 1 && (
                          <View style={{ height: para.isList ? 3 : 8 }} />
                        )}
                      </View>
                    ))}
                    {renderCitation(provision)}
                  </View>
                  <View style={styles.colResponse}>
                    {provision.da_response ? (
                      <View style={[styles.responseBox, {
                        backgroundColor: provision.da_status === 'complies' ? '#f0fdf4'
                          : provision.da_status === 'varies' ? '#fffbeb'
                          : '#f9fafb',
                        borderColor: provision.da_status === 'complies' ? '#86efac'
                          : provision.da_status === 'varies' ? '#fcd34d'
                          : '#e5e7eb',
                      }]}>
                        <Text style={{ fontSize: 8, color: '#374151', padding: 4 }}>
                          {provision.da_response}
                        </Text>
                      </View>
                    ) : (
                      <View style={styles.responseBox} />
                    )}
                    {provision.da_status === 'varies' && (
                      <View style={{ marginTop: 2, padding: '2 4' }}>
                        <Text style={{ fontSize: 6, color: '#92400e', fontStyle: 'italic', lineHeight: 1.3 }}>
                          Cl 4.6: State % variation, whether objectives of the standard are achieved, and consistency with zone objectives.
                        </Text>
                      </View>
                    )}
                  </View>
                </View>
              );
            })}
          </View>
        ))
      ) : (
        // Non-heritage: Flat list
        group.provisions.map((provision, pIdx) => {
          const sanitizedText = sanitizeForPdf(provision.provision_text || '');
          const paragraphs = parseParagraphsWithHighlights(sanitizedText);

          return (
            <View key={provision.id} style={styles.tableRow}>
              <Text style={[styles.cellNumber, styles.colNumber]}>
                {sectionNumber}.{provisionNumber++}
              </Text>
              <View style={[styles.colProvision]}>
                {paragraphs.map((para, pIdx) => {
                  // TEST: Computed style approach (spread operator)
                  const textStyle = {
                    ...styles.cellProvision,
                    ...(para.isHeader && { fontFamily: 'Helvetica-Bold', fontSize: 11 }),
                    ...((para.isList || para.isNestedList) && {
                      marginLeft: para.isNestedList ? 20 : 10,
                      fontSize: 9
                    })
                  };

                  return (
                  <View key={pIdx}>
                    {/* Control/Objective markers - styled as badges */}
                    {para.isControlMarker ? (
                      <View style={{
                        backgroundColor: para.paragraph.startsWith('C') ? '#0c4a6e' : '#92400e',
                        paddingVertical: 3,
                        paddingHorizontal: 8,
                        borderRadius: 10,
                        alignSelf: 'flex-start',
                        marginVertical: 4
                      }}>
                        <Text style={{
                          color: '#ffffff',
                          fontFamily: 'Helvetica-Bold',
                          fontSize: 8
                        }}>
                          {para.paragraph}
                        </Text>
                      </View>
                    ) : (
                      <Text style={textStyle}>
                        {para.segments.map((segment, sIdx) => {
                          if (segment.isNumeric) {
                            return (
                              <Text key={sIdx} style={{ fontFamily: 'Helvetica-Bold', color: '#0f766e' }}>
                                {segment.text}
                              </Text>
                            );
                          } else if (segment.isControl) {
                            return (
                              <Text key={sIdx} style={{ fontFamily: 'Helvetica-Bold', color: '#0c4a6e' }}>
                                {segment.text}
                              </Text>
                            );
                          } else if (para.isHeader) {
                            // Headers: wrap all text in Text component to inherit bold
                            return (
                              <Text key={sIdx} style={{ fontFamily: 'Helvetica-Bold' }}>
                                {segment.text}
                              </Text>
                            );
                          } else {
                            return segment.text;
                          }
                        })}
                      </Text>
                    )}
                    {pIdx < paragraphs.length - 1 && (
                      <View style={{ height: para.isList ? 3 : 8 }} />
                    )}
                  </View>
                  );
                })}
                {formatCitation(provision) && (
                  <Text style={{ fontSize: 7, color: '#0c4a6e', marginTop: 3 }}>
                    {formatCitation(provision)}
                  </Text>
                )}
              </View>
              <View style={styles.colResponse}>
                {provision.da_response ? (
                  <View style={[styles.responseBox, {
                    backgroundColor: provision.da_status === 'complies' ? '#f0fdf4'
                      : provision.da_status === 'varies' ? '#fffbeb'
                      : '#f9fafb',
                    borderColor: provision.da_status === 'complies' ? '#86efac'
                      : provision.da_status === 'varies' ? '#fcd34d'
                      : '#e5e7eb',
                  }]}>
                    <Text style={{ fontSize: 8, color: '#374151', padding: 4 }}>
                      {provision.da_response}
                    </Text>
                  </View>
                ) : (
                  <View style={styles.responseBox} />
                )}
                {provision.da_status === 'varies' && (
                  <View style={{ marginTop: 2, padding: '2 4' }}>
                    <Text style={{ fontSize: 6, color: '#92400e', fontStyle: 'italic', lineHeight: 1.3 }}>
                      Cl 4.6: State % variation, whether objectives of the standard are achieved, and consistency with zone objectives.
                    </Text>
                  </View>
                )}
              </View>
            </View>
          );
        })
      )}

    </View>
  );
}
