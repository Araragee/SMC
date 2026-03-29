sqlite3 /tmp/smc_sql_app.db "ALTER TABLE sessions ADD COLUMN proof_justification VARCHAR;" 2>/dev/null
sqlite3 /tmp/smc_sql_app.db "ALTER TABLE sessions ADD COLUMN rejection_reason VARCHAR;" 2>/dev/null
sqlite3 backend/sql_app.db "ALTER TABLE sessions ADD COLUMN proof_justification VARCHAR;" 2>/dev/null
sqlite3 backend/sql_app.db "ALTER TABLE sessions ADD COLUMN rejection_reason VARCHAR;" 2>/dev/null
