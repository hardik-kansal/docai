# keeping it empty have no bt


"""
for my own knowledge


sudo systemctl start/stop postgresql
sudo -u postgres psql -> run psql cli with postgres as user(default, no pwd asked)
CREATE USER hardik WITH PASSWORD 'mypassword';
GRANT ALL PRIVILEGES ON DATABASE project1 TO hardik;
\q
psql -h localhost -U hardik -d project1 ->talk with connection


Postgres Server <-> postgres user root requires sudo password
 └── Database: project1  <-> hardik user "all privileges" permission
      ├── Schema: public          ← default, always exists
      │    ├── Table: users
      │    ├── Table: alembic_version
      │    └── ...
      ├── Schema: auth            ← you could create this
      │    └── Table: sessions
      └── Schema: analytics
           └── Table: query_logs

to access a table
-need url for each db
- acess via public.users though for public not req explicitly to tell
GRANT ALL PRIVILEGES ON DATABASE only grants connect/create-schema
we need to give
sudo -u postgres psql
GRANT USAGE, CREATE ON SCHEMA public TO hardik; -> by postgres user
\q



uv add alembic -- for migrations
if venv activated -> dont require uv run

uv run alembic init backend/db/migrations
-> creates env.py,script.py.mako inside migrations folder
env.py-> configure db_url using config.set_main_option("sqlalchemy.url",db_url from config)
script.py.mako -> python template which are used by alembic to create version template on running

alembic revision -m "filename"
alembic upgrade head -> to migrate all not done yet in order
alembic current -> to get version
alembic downgrade -1

psql -h localhost -U hardik -d project1
\d users -> list structure of table
\dt -> list all tables

"""
