# Base de données

- SGBD : **PostgreSQL** (SQLite accepté en développement et pour les tests).
- ORM : SQLAlchemy 2 — modèles dans `backend/models/__init__.py`.
- Migrations : Alembic — `backend/alembic/versions/`.

```bash
cd backend
alembic upgrade head                              # appliquer les migrations
alembic revision --autogenerate -m "description"  # après modification des modèles
```

`schema.sql` est le SQL généré par la migration initiale (`alembic upgrade head --sql`), fourni pour référence.

Tables : `users`, `projects`, `analysis_steps`, `scenes`, `frames`, `characters`, `dialogue_lines`.
Toutes les données d'un projet sont supprimées en cascade avec lui.
