# CircusCircus Startup & Runtime Mental Model

Use this to explain the system boot and request-handling loop to teammates. Reference actual code locations for deep dives.

---

## Part 1: The Startup Sequence (Before Listening)

### Phase 1: You run `./run.sh` from the terminal

```
$ ./run.sh
```

What happens:

1. Shell script finds a free port (starting at 5006).
2. Sets environment: export SECRET_KEY="kristofer"
3. Calls: cd ./forum && flask run --port=5007

### Phase 2: Flask CLI bootstrap

Flask's built-in CLI:

1. Reads FLASK_APP env var (set in config.py).
2. Flask imports forum.app module.
3. Python executes top-level code in forum/app.py.

**Key insight:** At this point, nothing is listening yet. We're still in startup/initialization.

---

## Part 2: App Initialization (Code runs sequentially, once)

### Step 1: Config loads (config.py)

```python
class Config:
    SECRET_KEY = 'kristofer'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///circuscircus.db'
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

Flask reads these into app.config dictionary.

**File:** config.py (lines 1-19)

### Step 2: App factory runs (forum/__init__.py → create_app())

```python
def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')
    app.register_blueprint(rt)  # attach routes
    db.init_app(app)
    with app.app_context():
        db.create_all()
    return app
```

What happens:

1. Flask app object created.
2. Config injected into app.config.
3. Routes blueprint registered (all handlers from routes.py attached).
4. SQLAlchemy db object initialized against app.
5. **Inside app context:** db.create_all() tells SQLAlchemy to create all table schemas if they don't exist.

**File:** forum/__init__.py (lines 1-18)

**What gets created in DB:**
- User table (id, username, password_hash, email, admin)
- Post table (id, title, content, user_id, subforum_id, postdate)
- Subforum table (id, title, description, parent_id, hidden)
- Comment table (id, content, postdate, user_id, post_id)

### Step 3: Post-factory setup in forum/app.py

```python
app = create_app()  # <- Factory returns configured app

app.config['SITE_NAME'] = 'Schooner'
app.config['SITE_DESCRIPTION'] = 'a schooner forum'
app.config['FLASK_DEBUG'] = 1

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(userid):
    return User.query.get(userid)

with app.app_context():
    db.create_all()  # Redundant but safe; creates tables if missing
    if not Subforum.query.all():
        init_site()  # Seed default subforums only on first run
```

What happens:

1. Site-specific config values applied.
2. LoginManager wired up (Flask-Login auth framework).
3. user_loader callback registered (Flask knows how to load a User from session).
4. **Inside app context (second time):**
   - Tables ensured to exist (again, safe).
   - **If no subforums exist, seed them:**
     - Create "Forum" parent subforum.
     - Create children: "Announcements", "Bug Reports", "General Discussion", "Other".
     - All inserted into DB and committed.

**File:** forum/app.py (lines 1-42)

### Step 4: Routes are now available

At this point:

- All route handlers from forum/routes.py are registered:
  - POST /action_login
  - GET /action_logout
  - POST /action_createaccount
  - GET /subforum
  - GET /loginform
  - GET /addpost
  - POST /action_post
  - GET /viewpost
  - POST/GET /action_comment
  - GET / (from app.py)

**File:** forum/routes.py (all handlers)

---

## Part 3: Flask Enters the Listening Loop (App Settles)

### What Flask does next

After initialization completes, Flask CLI calls:

```python
app.run(host='127.0.0.1', port=5007, debug=False)
```

Flask now:

1. **Binds a TCP socket** to 127.0.0.1:5007.
2. **Calls listen()** on the socket (OS kernel puts socket in listening state).
3. **Enters an event loop** (WSGI server's run loop).
4. **Prints:**
   ```
   * Running on http://127.0.0.1:5007
   Press CTRL+C to quit
   ```
5. **Blocks forever** waiting for incoming TCP connections.

This is the **listening phase**. The process is now idle, consuming minimal CPU, waiting for browser requests.

---

## Part 4: A Request Arrives (Event Triggers Handler)

### Scenario: User opens browser to http://127.0.0.1:5007/

Browser sends HTTP request:

```
GET / HTTP/1.1
Host: 127.0.0.1:5007
```

### What happens inside Flask's listening loop:

1. **OS kernel receives TCP packet** on port 5007.
2. **Flask's WSGI server wakes up** (event notification from OS).
3. **Server reads HTTP request** from socket.
4. **WSGI server parses:**
   - HTTP method: GET
   - URL path: /
   - Query string: (none)
   - Headers: (all headers)
5. **Flask route dispatcher searches** for matching handler:
   - Checks registered routes in order.
   - Finds `@app.route('/')` in forum/app.py.
6. **Handler executes:** `index()`
   ```python
   @app.route('/')
   def index():
       subforums = Subforum.query.filter(Subforum.parent_id == None).order_by(Subforum.id)
       return render_template("subforums.html", subforums=subforums)
   ```
7. **Inside handler:**
   - SQLAlchemy query runs against SQLite DB.
   - Returns list of top-level subforums.
   - render_template() loads subforums.html, extends layout.html, includes header.html.
   - Jinja2 renders HTML string.
8. **Handler returns** HTML string to WSGI server.
9. **WSGI server wraps it** as HTTP response:
   ```
   HTTP/1.1 200 OK
   Content-Type: text/html
   Content-Length: ...

   <html>...rendered page...</html>
   ```
10. **Response sent** back to browser over socket.
11. **Socket connection closes**.
12. **Flask server goes back to sleep** waiting for next request.

**This loop repeats** for every request until you press CTRL+C.

---

## Part 5: Steady State (Listening Loop Diagram)

```
┌─────────────────────────────────────────────────────────────┐
│  FLASK LISTENING LOOP (WSGI Server)                         │
│                                                              │
│  while True:                                                │
│      connection = socket.accept()  # <- BLOCKS HERE        │
│                                                              │
│      request = parse_http(connection)                       │
│      route_handler = match_route(request.path)              │
│                                                              │
│      ┌─────────────────────────────────────┐                │
│      │  HANDLER EXECUTION (YOUR CODE)      │                │
│      │  - Query DB via SQLAlchemy          │                │
│      │  - Validate input                   │                │
│      │  - Modify DB (commits done here)    │                │
│      │  - Render template                  │                │
│      │  - Return HTML/redirect             │                │
│      └─────────────────────────────────────┘                │
│                                                              │
│      response = wrap_in_http(handler_result)               │
│      connection.send(response)                              │
│      connection.close()                                     │
│                                                              │
│  # Loop continues; blocks at socket.accept() again         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

Key insight:

- **Socket.accept() blocks** the entire process.
- OS kernel wakes process when a connection arrives.
- Handler runs, response sent, socket closes.
- Process goes back to sleep.

---

## Part 6: DB Persistence Across Requests

SQLite DB file: `instance/circuscircus.db`

1. **First run:** db.create_all() creates file and schema.
2. **Every request:** SQLAlchemy connection pool manages DB connections.
3. **On write (POST /action_post, etc.):** db.session.commit() persists to disk.
4. **Process exits:** DB file remains on disk for next run.

**No separate DB server needed.** SQLite is a file-based DB that runs in the same process.

---

## Part 7: Shutdown (Press CTRL+C)

You press CTRL+C in terminal.

```
OS sends SIGINT signal to process
↓
Flask receives signal
↓
Flask stops accepting connections on socket
↓
Flask closes socket
↓
Flask exits main loop
↓
Process terminates
↓
Database file remains intact on disk
```

---

## Whiteboard Mental Model Summary

Draw this on a whiteboard in layers:

```
┌───────────────────────────────────────────────────────────────┐
│  TERMINAL: $ ./run.sh                                         │
└───────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│  STARTUP PHASE (one-time, sequential)                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 1. Config loads (config.py)                             │ │
│  │ 2. App factory creates app (forum/__init__.py)          │ │
│  │ 3. DB tables created if missing (db.create_all)         │ │
│  │ 4. Post-factory setup (forum/app.py)                    │ │
│  │ 5. Seed subforums if DB empty (init_site)               │ │
│  │ 6. Routes registered (from forum/routes.py)             │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│  LISTENING PHASE (runs forever until CTRL+C)                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ App listening on http://127.0.0.1:5007                  │ │
│  │                                                         │ │
│  │  for each request:                                      │ │
│  │    1. Socket receives TCP connection from browser       │ │
│  │    2. HTTP request parsed                               │ │
│  │    3. Route handler matched                             │ │
│  │    4. Handler executes (YOUR CODE)                      │ │
│  │       - Queries DB                                      │ │
│  │       - Validates, modifies                             │ │
│  │       - Renders template                                │ │
│  │    5. HTML response sent to browser                     │ │
│  │    6. Socket closes                                     │ │
│  │    7. Loop returns to listening                         │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│  SHUTDOWN (CTRL+C)                                            │
│  - DB file closed                                             │
│  - Process exits                                              │
│  - Data persists in instance/circuscircus.db                  │
└───────────────────────────────────────────────────────────────┘
```

---

## Quick Reference: File Responsibilities

| File | Purpose |
|------|---------|
| config.py | Database URI, secret key, Flask config |
| forum/__init__.py | App factory: config loading, DB init, blueprint registration |
| forum/app.py | Post-factory: LoginManager, seed logic, / route |
| forum/models.py | SQLAlchemy schemas (User, Post, Subforum, Comment) |
| forum/routes.py | HTTP handler functions (all routes except /) |
| forum/templates/* | Jinja2 templates rendered by handlers |
| instance/circuscircus.db | SQLite database file (persists data) |

---

## Key Takeaways for Whiteboard

1. **Startup is one-time, sequential:** Config → Factory → Seed → Listen.
2. **Listening is an event loop:** Blocks on socket, wakes on request, executes handler, sleeps again.
3. **Your code lives in handlers:** Every handler gets one chance to query, validate, render, return.
4. **DB persists across restarts:** SQLite file stays on disk; db.create_all() is safe to call repeatedly.
5. **Flask WSGI is the black box:** Socket binding, request parsing, response transport. You fill in the handler logic.
