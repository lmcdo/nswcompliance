# PostgreSQL Database Configuration

## CRITICAL: Port Configuration

**PostgreSQL MUST run on port 5432 (standard port) for this codebase to work.**

### Current Configuration
- **PostgreSQL Version**: 17.6
- **Port**: 5432 (standard)
- **Database**: nsw_planning
- **User**: postgres
- **Password**: postgres
- **Authentication**: scram-sha-256

### Configuration Files
- **postgresql.conf**: `C:\Program Files\PostgreSQL\17\data\postgresql.conf`
 - `port = 5432` (line 64)
- **pg_hba.conf**: `C:\Program Files\PostgreSQL\17\data\pg_hba.conf`
 - Authentication method: `scram-sha-256`

### Why Port 5432 is Required
The entire codebase (100+ files) expects PostgreSQL on port 5432:
- All Python scripts use default psycopg2 connections
- All JavaScript/Node.js scripts use default pg connections
- All shell scripts use default psql connections
- Migration scripts, backup scripts, and test scripts all assume port 5432

### If Port Changes Are Needed
**DO NOT change the PostgreSQL port.** Instead:
1. If port 5432 is occupied, stop the conflicting service
2. If using multiple PostgreSQL versions, uninstall older versions
3. If absolutely necessary to use a different port, update ALL these locations:
 - `.env` file (PGPORT variable)
 - All Python scripts with psycopg2.connect() calls
 - All JavaScript scripts with pg.Pool() connections
 - All shell scripts with psql commands
 - All Docker configurations
 - All environment variable defaults in code

### Common Issues and Solutions

#### Issue: "Connection refused on port 5432"
**Solution**: Check if PostgreSQL is running
```bash
sc query postgresql-x64-17
netstat -an | findstr 5432
```

#### Issue: "Password authentication failed"
**Solution**: Reset password using trust authentication
1. Edit pg_hba.conf: Change `scram-sha-256` to `trust` for local connections
2. Reload: `pg_ctl reload -D "C:\Program Files\PostgreSQL\17\data"`
3. Connect and set password: `psql -U postgres -c "ALTER USER postgres PASSWORD 'postgres';"`
4. Change pg_hba.conf back to `scram-sha-256`
5. Reload configuration again

#### Issue: "Database nsw_planning does not exist"
**Solution**: Create the database
```python
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, database='postgres', user='postgres', password='postgres')
conn.autocommit = True
cursor = conn.cursor()
cursor.execute('CREATE DATABASE nsw_planning')
conn.close()
```

### Installation Notes
- PostgreSQL 17 may default to port 5433 during installation
- **ALWAYS change postgresql.conf to use port 5432 immediately after installation**
- **ALWAYS set the postgres user password to 'postgres' for development**
- **ALWAYS create the nsw_planning database**

### Backup and Restore
- Database backups are in: `nsw_planning_backup_*.sql`
- Restore: `psql -U postgres -d nsw_planning -f backup_file.sql`

### Environment Variables (.env)
```bash
PGHOST=localhost
PGPORT=5432
PGDATABASE=nsw_planning
PGUSER=postgres
PGPASSWORD=postgres
```

---
** REMEMBER: Any deviation from port 5432 will break the entire application!**