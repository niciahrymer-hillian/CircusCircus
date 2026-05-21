# CircusCircus — Request/Response Cycle Walkthrough

A guided tour of the codebase for new team members. Read this before writing any code.

---

## The Black Box

Flask's WSGI loop is the engine you never touch. It:
1. Listens on a port (5001)
2. Receives an HTTP request from the browser
3. Finds the matching route function in your code
4. Calls it, gets back a response
5. Sends that response to the browser

**Your job as a developer is only to write the route functions.** Flask handles everything else.

---

## Canonical Request/Response Cycle

Use this exact mental model for every feature:

```
browser request
  -> Flask route handler
  -> SQLAlchemy query/create/update
  -> render_template(...) with Jinja2
  -> HTML response sent back to browser
```

For one full page load:
1. Browser sends a GET request (for example, `/viewpost?post=3`).
2. Flask matches the URL to a route function in `routes.py`.
3. The route uses SQLAlchemy models in `models.py` to read/write data.
4. The route calls `render_template(...)` and passes Python objects to a Jinja2 template.
5. Jinja2 renders final HTML.
6. Flask returns that HTML response to the browser.

Flask's WSGI loop is the black box around this flow; your code fills in the route handlers around it.

---

## Layer 1 — Startup: `config.py` + `forum/__init__.py`

When you run `flask run`, this happens **once**:

```
config.py              →  defines SECRET_KEY, DB path (sqlite), debug flags
forum/__init__.py      →  create_app() factory:
                            1. creates the Flask object
                            2. loads config.py settings
                            3. registers the routes Blueprint (rt)
                            4. attaches SQLAlchemy (db.init_app)
                            5. calls db.create_all() → builds DB tables if missing
forum/app.py           →  seeds initial Subforum rows if DB is empty
                           sets up Flask-Login's user_loader callback
                           registers the index "/" route
```

After this, the app sits idle — waiting for a browser to knock.

---

## Layer 2 — The Database: `models.py` (4 schemas)

SQLAlchemy maps Python classes to database tables. Each class **is** a table:

```
User          → users table
  id, username, email, password_hash, admin
  ↓ has many
Post          → posts table
  id, title, content, postdate, user_id (FK), subforum_id (FK)
  ↓ has many
Comment       → comments table
  id, content, postdate, user_id (FK), post_id (FK)

Subforum      → subforum table
  id, title, description, parent_id (FK → itself, for nesting)
  ↓ has many Posts, has many child Subforums
```

**Relationships in plain English:**
- A `User` writes many `Post`s and many `Comment`s
- A `Post` belongs to one `Subforum` and one `User`, and has many `Comment`s
- A `Subforum` can have a parent `Subforum` (that's how "Forum → Announcements" nesting works)

`models.py` also contains helper functions:
- `valid_title()` / `valid_content()` — enforce length rules before saving
- `generateLinkPath()` — builds the breadcrumb trail (e.g. Forum Index / Forum / Announcements)
- `error()` — returns a red HTML error string for simple inline errors

---

## Layer 3 — Route Handlers: `routes.py` + `user.py`

This is where a browser request meets your code. Every route follows the same pattern:

```
@rt.route('/path', methods=['GET'|'POST'])
def handler():
    1. Read input  (request.args for URL params, request.form for POST data)
    2. Query DB    (Model.query.filter(...).first() or .all())
    3. Do logic    (validate, create objects, append relationships)
    4. Write DB    (db.session.add(), db.session.commit())
    5. Return      (render_template(...) or redirect(...))
```

### Route Map

| Route | Method | What it does |
|---|---|---|
| `/` | GET | List all top-level subforums → `subforums.html` |
| `/subforum?sub=<id>` | GET | Show one subforum + its posts → `subforum.html` |
| `/loginform` | GET | Show login/register form → `login.html` |
| `/action_login` | POST | Check username+password → redirect `/` or show errors |
| `/action_logout` | GET | Clear session → redirect `/` |
| `/action_createaccount` | POST | Validate + create `User` → redirect `/` |
| `/addpost?sub=<id>` | GET | Show post creation form → `createpost.html` |
| `/action_post?sub=<id>` | POST | Validate + save new `Post` → redirect `/viewpost` |
| `/viewpost?post=<id>` | GET | Show one post + its comments → `viewpost.html` |
| `/action_comment?post=<id>` | POST | Save new `Comment` → redirect `/viewpost` |

`user.py` is a helper module — `username_taken()`, `email_taken()`, `valid_username()` — called by `action_createaccount`.

---

## Layer 4 — Templates (the Front End)

Templates are HTML files with **Jinja2** — Flask's templating language.
- `{{ variable }}` — outputs a value into the HTML
- `{% for x in list %}` / `{% if condition %}` — runs logic

### Template Hierarchy

```
layout.html          ← base shell: loads CSS, renders header, shows errors block
  └─ header.html     ← nav bar (included into layout on every page)
  └─ subforums.html  ← extends layout → loops over subforums, renders links
  └─ subforum.html   ← extends layout → shows one subforum + post list
  └─ login.html      ← extends layout → login form + register form
  └─ createpost.html ← extends layout → title + content textarea form
  └─ viewpost.html   ← extends layout → post body + comment list + comment form
```

**No JavaScript logic** — all interactivity is server-side. The one JS snippet in
`viewpost.html` is just a `toggle()` call to show/hide the comment box.

---

## A Complete Example: Posting a Comment

```
1. Browser visits /viewpost?post=3
   → Flask calls viewpost() in routes.py
   → Queries Post WHERE id=3
   → Queries Comments WHERE post_id=3
   → render_template("viewpost.html", post=..., comments=...)
   → Jinja2 fills in the HTML
   → Browser receives the finished page

2. User types a comment, clicks "Comment"
   → Browser POSTs to /action_comment?post=3
   → Flask calls comment() in routes.py
   → Reads request.form['content']
   → Creates Comment(content, now)
   → current_user.comments.append(comment)   ← links Comment to User in DB
   → post.comments.append(comment)           ← links Comment to Post in DB
   → db.session.commit()                     ← writes to SQLite
   → redirect("/viewpost?post=3")            ← browser reloads page with new comment visible
```

---

## What's Front End vs Back End?

| Front End | Back End |
|---|---|
| `templates/*.html` — page structure | `routes.py` — handles every request |
| `static/bootstrap.min.css` — Bootstrap styles | `models.py` — DB schema + queries |
| `static/style.css` — custom styles | `user.py` — validation helpers |
| Jinja2 `{{ }}` tags — fills in data | `app.py` — wires everything together |
| One small JS `toggle()` in viewpost | `config.py` — app settings |

### Where is the Business Logic?

- **`routes.py`** — input validation, auth checks, relationship wiring between models
- **`models.py`** — `get_time_string()` cache, `generateLinkPath()` breadcrumb builder, `valid_title/content()` rules

---

## Known Issues to Fix (see GitHub Issues)

- `SECRET_KEY = 'kristofer'` in `config.py` — must move to `.env` before any public push (security risk)
- `@login_required` is placed *above* `@rt.route(...)` on some routes — decorator order is wrong; correct order is `@rt.route(...)` first, then `@login_required`
- `routes.py` needs to be split into `auth.py`, `posts.py`, `comments.py` — see Epic 2 on GitHub
- Port 5000 is blocked on macOS by AirPlay Receiver — run on port 5001 instead

  # CircusCircus PostgreSQL migration and Docker workflow

  ## Step-by-step workflow

  1. **Switch to Docker**: All Heroku instructions and configs are deprecated. Use Docker Compose for local and production workflows.
  2. **Install dependencies**:
    - Local: `pip install psycopg2-binary`
    - Container: `psycopg2-binary` in requirements.txt
  3. **.env setup**:
    - Add `DATABASE_URL=postgresql://ccuser:Elephant@db/circuscircus` (replace `Elephant` with your password)
  4. **config.py**:
    - Loads DB URI from .env using python-dotenv
    - Host is `db` (Docker service name)
    - Fallbacks to SQLite for local dev if env var is missing
  5. **docker-compose.yml**:
    - Defines `db` (Postgres) and `web` (app) services
    - Healthcheck ensures app waits for DB readiness
    - Uses custom Docker network for isolation
    - Links services, sets env vars, exposes ports
  6. **Testing**:
    - `docker compose up`
    - `docker exec -it <container> bash`
    - Run `python` shell:
      ```python
      from forum.models import db
      db.create_all()
      # Seed subforums, test CRUD for User, Post, Comment, Subforum
      ```
  7. **Deploy**:
    - `docker build -t circuscircus .`
    - `docker push <your-registry>/circuscircus`
    - Deploy to Railway, Render, Fly.io, etc.
    - Smoke test live URL

  ---

  # [WHY] This workflow ensures local and production environments match, with secure credential handling and persistent data.
  # [EFFECT] Simplifies onboarding, testing, and deployment for all contributors.
