### Python Trio

1) Project overview.
   1) main.py - FastAPI.
   3) database.py - database engine.
   4) alembic/ - overview.
   2) models.py.
      1) Asset and Portfolio.
2) Run docker with postgresql. Generate and apply initial migration.
   ```bash
   # clean volume if you want fresh db
   # docker compose down -v
    docker compose up -d db
    ```
3) Create endpoints. Start server.
   1) Add BTC A.
4) Provide changes in model. 
   1) add Asset.code property.
   2) add Asset.created_at property and Portfolio.created_at.
   3) Generate migration. (there will be a problem with nulls for .code).
   4) Solve the problem with nulls by modifying migration. Put there UKNOWN for a moment.
   5) Mixin for created_at?
5) Add Price table.
6) Maybe JSON field instead of dedicated table?
7) Vibe coding - fill prices.
