## Deploying CircusCircus with Docker & PostgreSQL

Heroku is no longer used. Follow these steps for local and production deployment using Docker:

## 1. Install Docker Desktop (macOS)

If you do not have Docker installed:
1. Download Docker Desktop from https://www.docker.com/products/docker-desktop/
2. Open the .dmg and drag Docker to Applications.
3. Launch Docker Desktop and wait for the whale icon in the menu bar.
4. Open a terminal and run `docker --version` to verify installation.

See `references/DockerInstall_macOS.md` for more details.

## 2. Start PostgreSQL with Docker

Run the following command (replace `<password>` with a secure password, e.g., `Elephant`):

```
docker run --name circuscircus-db -e POSTGRES_USER=ccuser -e POSTGRES_PASSWORD=<password> -e POSTGRES_DB=circuscircus -p 5432:5432 -d postgres
```

## 3. Install Python dependencies

For local development, install `psycopg2-binary`:
```
pip install psycopg2-binary
```
For production (in Docker), use `psycopg2` in your requirements.txt.

## 4. Update config.py for PostgreSQL

Edit `config.py` to use the following URI:
```
postgresql://ccuser:<password>@db/circuscircus
```
Load credentials from `.env` and set the host to `db` (the Docker service name).

## 5. Run the app with Docker Compose

Use `docker-compose.yml` to define both the web and db services. Example:
```
version: '3.8'
services:
	db:
		image: postgres
		environment:
			POSTGRES_USER: ccuser
			POSTGRES_PASSWORD: <password>
			POSTGRES_DB: circuscircus
		ports:
			- "5432:5432"
	web:
		build: .
		command: gunicorn forum.app:app
		depends_on:
			- db
		environment:
			- DATABASE_URL=postgresql://ccuser:<password>@db/circuscircus
		ports:
			- "8000:8000"
```

## 6. Set up environment variables

Add `DATABASE_URL` to your `.env` file and reference it in `docker-compose.yml`.

## 7. Test and Migrate Database

After running `docker compose up`, exec into the app container:
```
docker exec -it <container> bash
```
Then run your migration/init scripts (e.g., `db.create_all()`, seed data, etc.).

## 8. Push to Production

Build and push your image:
```
docker build -t circuscircus .
docker push <your-registry>/circuscircus
```
Deploy using your host (Railway, Render, Fly.io, etc.) and smoke test the live URL.

---

**Note:**
- Do NOT use 'whatever' as your database password.
- For more details, see the `references/DockerInstall_macOS.md` file.
pip install psycopg2-binary
```
For container builds, use `psycopg2` in requirements.txt.

## 3. Update config.py

Set the SQLAlchemy URI to:
```
postgresql://ccuser:<password>@db/circuscircus
```
Load credentials from `.env`. The host should be `db` (Docker service name), not `localhost`.

## 4. Add .env file

Create a `.env` file with:
```
DATABASE_URL=postgresql://ccuser:<password>@db/circuscircus
```

## 5. Docker Compose

Create or update `docker-compose.yml`:
```yaml
version: '3.8'
services:
	db:
		image: postgres
		environment:
			POSTGRES_USER: ccuser
			POSTGRES_PASSWORD: <password>
			POSTGRES_DB: circuscircus
		ports:
			- "5432:5432"
	web:
		build: .
		command: gunicorn forum.app:app
		environment:
			DATABASE_URL: postgresql://ccuser:<password>@db/circuscircus
		depends_on:
			- db
		ports:
			- "8000:8000"
```

## 6. Test the app

Run:
```
docker compose up
```
Then exec into the app container:
```
docker exec -it <container> bash
```
Run `db.create_all()`, seed subforums, and test CRUD for User, Post, Comment, and Subforum.

## 7. Deploy

Build and push your image:
```
docker build -t circuscircus .
docker push <your-registry>/circuscircus
```
Deploy to your host (Railway, Render, Fly.io, etc.) and smoke test the live URL.