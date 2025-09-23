const { spawn } = require('child_process');
const path = require('path');

const scriptPath = path.join(process.cwd(), 'services', 'enhanced_compliance_api.py');
const pythonPath = path.join(process.cwd(), 'venv_linux', 'Scripts', 'python.exe');
const args = [scriptPath, '--zone', 'R2', '--development-type', 'dual_occupancy', '--include-development-permissions', '--format', 'json'];

console.log(`Testing: ${pythonPath} ${args.join(' ')}`);
console.log(`Working directory: ${process.cwd()}`);

const python = spawn(pythonPath, args);

let stdout = '';
let stderr = '';

python.stdout.on('data', (data) => {
  stdout += data.toString();
});

python.stderr.on('data', (data) => {
  stderr += data.toString();
});

python.on('close', (code) => {
  console.log(`Exit code: ${code}`);
  console.log(`Stdout: ${stdout.substring(0, 200)}...`);
  console.log(`Stderr: ${stderr}`);
});

python.on('error', (error) => {
  console.log(`Error: ${error.message}`);
});