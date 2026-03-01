### Python Trio

1) Project overview.
   1) main.py - FastAPI
   2) models.py
   3) database.py
   4) alembic/
2) Run docker with postgresql. Generate and apply initial migration.
   ```bash
   # clean volume if you want fresh db
   # docker compose down -v
    docker compose up -d db
    ```
3) Provide changes in model. Add new table and add new column to one of existing tables. Generate and apply migration.
4) Build endpoint returning assets. 
