const { spawn } = require('child_process');
const path = require('path');

// Simulate exactly what the API does
const scriptPath = path.join('services', 'enhanced_compliance_api.py');
const pythonPath = path.join('venv_linux', 'Scripts', 'python.exe');
const args = [scriptPath, '--zone', 'R2', '--development-type', 'dual_occupancy', '--include-development-permissions', '--format', 'json'];

console.log('=== DEBUGGING API SPAWN ===');
console.log('Script path:', scriptPath);
console.log('Python path:', pythonPath);
console.log('Working directory:', path.join(process.cwd(), '..'));
console.log('Args:', args);
console.log('Full command:', `${pythonPath} ${args.join(' ')}`);

const pythonProcess = spawn(pythonPath, args, {
  cwd: path.join(process.cwd(), '..'),
  stdio: ['pipe', 'pipe', 'pipe']
});

let stdout = '';
let stderr = '';

pythonProcess.stdout.on('data', (data) => {
  stdout += data.toString();
  console.log('STDOUT chunk:', data.toString().substring(0, 100));
});

pythonProcess.stderr.on('data', (data) => {
  stderr += data.toString();
  console.log('STDERR chunk:', data.toString());
});

pythonProcess.on('close', (code) => {
  console.log(`Process exited with code: ${code}`);
  console.log(`Exit code hex: 0x${code.toString(16)}`);
  console.log('STDOUT length:', stdout.length);
  console.log('STDERR length:', stderr.length);
  if (stderr) console.log('STDERR:', stderr);
  if (stdout.length > 0) {
    console.log('First 200 chars of STDOUT:', stdout.substring(0, 200));
  }
});

pythonProcess.on('error', (error) => {
  console.log('Process error:', error);
});

// Kill after 10 seconds if it hangs
setTimeout(() => {
  console.log('Killing process due to timeout');
  pythonProcess.kill();
}, 10000);