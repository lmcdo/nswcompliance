'use client';

export default function TestPage() {
 return (
 <div style={{ padding: '50px' }}>
 <h1>Input Test Page</h1>
 
 <div style={{ marginTop: '20px' }}>
 <label>Basic HTML Input:</label><br/>
 <input 
 type="text" 
 placeholder="Type here..."
 style={{ padding: '10px', fontSize: '16px', width: '300px' }}
 />
 </div>

 <div style={{ marginTop: '20px' }}>
 <label>Textarea:</label><br/>
 <textarea 
 placeholder="Type here..."
 style={{ padding: '10px', fontSize: '16px', width: '300px', height: '100px' }}
 />
 </div>

 <div style={{ marginTop: '20px' }}>
 <label>Contenteditable DIV:</label><br/>
 <div 
 contentEditable
 style={{ 
 padding: '10px', 
 fontSize: '16px', 
 width: '300px', 
 border: '1px solid #ccc',
 minHeight: '40px'
 }}
 >
 Click and type here...
 </div>
 </div>
 </div>
 );
}