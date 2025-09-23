import Link from 'next/link'

export default function Home() {
 return (
 <div className="compliance-checker">
 <h1>NSW Development Compliance MVP</h1>
 <div style={{ textAlign: 'center', padding: '50px 20px' }}>
 <h2>Welcome to the NSW Development Compliance System</h2>
 <p style={{ margin: '20px 0', fontSize: '18px', color: '#cbd5e1' }}>
 Check your development proposal against Inner West Council setback requirements
 </p>
 
 <div style={{ 
 background: '#1e293b', 
 border: '1px solid #334155', 
 borderRadius: '8px', 
 padding: '30px',
 maxWidth: '600px',
 margin: '30px auto'
 }}>
 <h3 style={{ marginBottom: '20px', color: '#0ea5e9' }}>System Status</h3>
 <div style={{ textAlign: 'left' }}>
 <div style={{ marginBottom: '10px' }}>
 <strong>Processing Pipeline:</strong> Active
 </div>
 <div style={{ marginBottom: '10px' }}>
 <strong>Council Areas:</strong> Ashfield, Leichhardt
 </div>
 <div style={{ marginBottom: '10px' }}>
 <strong>Documents Processed:</strong> 13 DCP files
 </div>
 <div style={{ marginBottom: '10px' }}>
 <strong>API Integration:</strong> Ready
 </div>
 <div style={{ marginBottom: '10px' }}>
 🆕 <strong>Semantic Processing:</strong> Available
 </div>
 </div>
 </div>

 <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', flexWrap: 'wrap' }}>
 <Link 
 href="/property" 
 style={{
 display: 'inline-block',
 padding: '15px 30px',
 backgroundColor: '#3182ce',
 color: 'white',
 textDecoration: 'none',
 borderRadius: '8px',
 fontSize: '16px',
 fontWeight: '600',
 }}
 >
 Standard Compliance Check
 </Link>
 
 <Link 
 href="/property/enhanced" 
 style={{
 display: 'inline-block',
 padding: '15px 30px',
 backgroundColor: '#10b981',
 color: 'white',
 textDecoration: 'none',
 borderRadius: '8px',
 fontSize: '16px',
 fontWeight: '600',
 position: 'relative'
 }}
 >
 Enhanced Compliance Check
 <span style={{ 
 position: 'absolute',
 top: '-8px',
 right: '-8px',
 background: '#ef4444',
 color: 'white',
 fontSize: '10px',
 padding: '2px 6px',
 borderRadius: '10px',
 fontWeight: '700'
 }}>NEW</span>
 </Link>
 </div>

 <div style={{ marginTop: '40px', fontSize: '14px', color: '#718096' }}>
 <p>
 This system processes official DCP documents from Ashfield, Leichhardt, and Marrickville 
 to provide real-time development compliance checking for Inner West LGA properties.
 </p>
 <div style={{ 
 marginTop: '20px', 
 padding: '15px', 
 background: '#0f172a', 
 border: '1px solid #10b981',
 borderRadius: '6px',
 fontSize: '13px',
 color: '#10b981'
 }}>
 <strong>🆕 Enhanced Version:</strong> Features dual semantic processing with LangExtract + AutoSchemaKG 
 for complex conditional rule understanding, source text grounding, and three-tier compliance classification.
 </div>
 </div>
 </div>
 </div>
 )
}