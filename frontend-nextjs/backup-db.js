const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: '.env.local' });

const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
const backupDir = path.join(__dirname, '..', 'backups');
const backupFile = path.join(backupDir, `compliance-engine-${timestamp}.sql`);

// Ensure backups directory exists
if (!fs.existsSync(backupDir)) {
  fs.mkdirSync(backupDir, { recursive: true });
}

// Parse connection string
const dbUrl = process.env.DATABASE_URL;
const match = dbUrl.match(/postgresql:\/\/([^:]+):([^@]+)@([^:]+):(\d+)\/(.+)/);
if (!match) {
  console.error('Invalid DATABASE_URL format');
  process.exit(1);
}

const [_, user, password, host, port, database] = match;

console.log(`🔄 Backing up database to: ${backupFile}`);
console.log(`   Host: ${host}`);
console.log(`   Database: ${database}`);

const command = `PGPASSWORD="${password}" pg_dump -h ${host} -p ${port} -U ${user} -d ${database} -F p -f "${backupFile}"`;

exec(command, (error, stdout, stderr) => {
  if (error) {
    console.error(`❌ Backup failed: ${error.message}`);
    console.error(stderr);
    process.exit(1);
  }

  const stats = fs.statSync(backupFile);
  const sizeMB = (stats.size / 1024 / 1024).toFixed(2);

  console.log(`✅ Backup complete!`);
  console.log(`   File: ${backupFile}`);
  console.log(`   Size: ${sizeMB} MB`);

  process.exit(0);
});
