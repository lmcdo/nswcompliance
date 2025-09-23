console.log('Frontend working directory:', process.cwd());
console.log('Parent directory:', require('path').join(process.cwd(), '..'));
console.log('Script path:', require('path').join(process.cwd(), '..', 'services', 'enhanced_compliance_api.py'));
console.log('Python path:', require('path').join(process.cwd(), '..', 'venv_linux', 'Scripts', 'python.exe'));

// Test if files exist
const fs = require('fs');
const path = require('path');

const scriptPath = path.join(process.cwd(), '..', 'services', 'enhanced_compliance_api.py');
const pythonPath = path.join(process.cwd(), '..', 'venv_linux', 'Scripts', 'python.exe');

console.log('Script exists:', fs.existsSync(scriptPath));
console.log('Python exists:', fs.existsSync(pythonPath));