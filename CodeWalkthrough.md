# CircusCircus Group Code Walkthrough

This guide is designed for a team read-through of the codebase. It follows request flow from config -> app startup -> models -> routes -> templates.

## 1. Session Goal

By the end of this walkthrough, everyone should be able to explain:

- how the app boots,
- where data is stored,
- how each HTTP handler works,
- how template rendering maps to route data,
- where to make common changes safely.

## 2. Quick Prep (5 minutes)

1. Start the app from project root:
   - source .venv/bin/activate
   - ./run.sh
2. Open the app in browser at:
   - http://127.0.0.1:5006
3. Keep these files open side-by-side:
   - config.py
   - forum/__init__.py
   - forum/app.py
   - forum/models.py
   - forum/routes.py
   - forum/templates/*

## 3. Architecture Map (2 minutes)

High-level flow:

1. Flask app config loads from Config in config.py.
2. App is created in forum/__init__.py via create_app().
3. SQLAlchemy db object is defined in forum/models.py and initialized on app startup.
4. Extra startup work in forum/app.py creates seed subforums if DB is empty.
5. Requests hit route handlers in forum/routes.py and forum/app.py.
6. Routes render templates in forum/templates.

## 3.1 One Full Request/Response Trace (Browser -> Route -> Query -> Template -> HTML)

Use GET /subforum?sub=1 as the concrete example.

1. Browser sends HTTP request
  - Example request line: GET /subforum?sub=1
  - Flask's WSGI server receives this and dispatches it to your app.

2. Flask route matching (your code starts here)
  - Handler: subforum() in forum/routes.py
  - The handler reads sub from request.args and loads the target subforum id.

3. SQLAlchemy queries execute
  - Query 1: find subforum by id.
  - Query 2: load recent posts for that subforum.
  - Query 3: load child subforums for nested navigation.
  - Optional helper call: generateLinkPath(...) builds breadcrumb HTML.

4. Route prepares template context
  - Context keys passed to render_template:
    - subforum
    - posts
    - subforums
    - path

5. Jinja2 renders HTML
  - Template selected: subforum.html
  - subforum.html extends layout.html
  - layout.html includes header.html
  - Jinja injects context values into template blocks and loops.

6. Flask returns HTTP response
  - render_template(...) returns a fully rendered HTML string.
  - Flask wraps it as an HTTP 200 response and sends it back to the browser.

7. Browser paints the page
  - Browser parses returned HTML.
  - It requests static CSS files referenced by layout.html.
  - User sees the subforum page with posts and navigation.

Where your team writes code vs Flask black box:

- Flask/WSGI black box:
  - socket listening, request parsing, route dispatch internals, response transport.
- Your code:
  - route handlers, model queries, business rules, template selection, context shaping.

Mini variant (home page):

1. GET /
2. index() in forum/app.py
3. Subforum.query.filter(Subforum.parent_id == None).order_by(Subforum.id)
4. render_template("subforums.html", subforums=subforums)
5. HTML response rendered through layout.html + header.html

## 4. File-by-File Walkthrough

## 4.1 config.py (Configuration Source)

What to read together:

- Config class values:
  - SECRET_KEY
  - FLASK_APP
  - SQLALCHEMY_DATABASE_URI
  - SQLALCHEMY_ECHO
  - SQLALCHEMY_TRACK_MODIFICATIONS

Talk through:

- This project is configured for SQLite by default.
- SECRET_KEY is hardcoded for local/dev use.
- Changing DB backend starts here (plus dependency + migration work).

Group questions:

- Should secrets move to environment variables?
- Do we want SQL echo enabled for debugging sessions?

## 4.2 forum/__init__.py (Factory)

What to read together:

- create_app()
- app.register_blueprint(rt)
- db.init_app(app)
- db.create_all() inside app context

Talk through:

- The app factory pattern is present here.
- Routes are attached as a blueprint from routes.py.
- DB tables are created at startup via db.create_all().

Important note:

- The factory lives in forum/__init__.py, while forum/app.py imports it and adds seed/setup behavior.

## 4.3 forum/app.py (App Wiring + Seeding + Index Route)

What to read together:

- app = create_app()
- app.config SITE_NAME, SITE_DESCRIPTION, FLASK_DEBUG
- init_site()
- add_subforum(...)
- login_manager setup + user loader
- startup block under with app.app_context()
- index() route

Talk through:

- Seed logic runs once when no subforums exist.
- add_subforum avoids duplicate creation under same parent/root.
- login manager loads users by ID for session auth.
- Root page / renders top-level subforums.

Group questions:

- Should seeding be moved to a CLI command instead of startup?
- Should FLASK_DEBUG be environment-driven?

## 4.4 forum/models.py (4 DB Schemas + Helpers)

Read in this order:

1. User
2. Post
3. Subforum
4. Comment

Schema checklist:

- User:
  - id, username, password_hash, email, admin
  - relationships: posts, comments
  - password hashing via werkzeug

- Post:
  - id, title, content, user_id, subforum_id, postdate
  - relationship: comments
  - get_time_string() for relative timestamps

- Subforum:
  - id, title, description, parent_id, hidden
  - relationships: subforums (self-referential), posts

- Comment:
  - id, content, postdate, user_id, post_id
  - get_time_string() for relative timestamps

Support helpers:

- generateLinkPath(subforumid) builds breadcrumb HTML.
- valid_title(title) and valid_content(content) enforce post constraints.
- error(errormessage) returns inline HTML error message.

Group questions:

- Should breadcrumb creation return data instead of raw HTML strings?
- Should validation helpers live in a separate validators module?
- Should model methods avoid print/debug side effects?

## 4.5 forum/routes.py (All HTTP Handlers)

Walk handler-by-handler and classify each as auth/public and read/write.

- POST /action_login
  - Auth check, login_user, redirect home or rerender login with errors.

- GET /action_logout (login required)
  - logout_user and redirect home.

- POST /action_createaccount
  - Username/email validation, create user, auto-login, redirect home.

- GET /subforum
  - Reads subforum by query param sub, fetches child subforums + posts, renders subforum view.

- GET /loginform
  - Renders login/register page.

- GET /addpost (login required)
  - Loads subforum and renders create-post form.

- GET /viewpost
  - Loads post + comments, renders post details.

- POST/GET /action_comment (login required)
  - Creates comment for given post and current user, commits, redirects to post view.

- POST /action_post (login required)
  - Validates title/content, creates post, links to user and subforum, commits, redirects to viewpost.

Cross-cutting things to discuss:

- Query params are directly cast to int; malformed values can raise exceptions.
- Error handling is mostly manual and page-specific.
- Route module is monolithic and already marked for splitting.

## 4.6 Templates (UI Flow)

Read templates in render hierarchy order:

1. layout.html
2. header.html
3. subforums.html
4. subforum.html
5. viewpost.html
6. createpost.html
7. login.html

Template responsibilities:

- layout.html
  - Base shell, CSS includes, header include, global error display block, body slot.

- header.html
  - Site title/description, current auth state, login/logout links.

- subforums.html
  - Home page list of top-level subforums.

- subforum.html
  - Breadcrumb path, subforum metadata, child subforums, post list, create-post CTA.

- viewpost.html
  - Full post display, add-comment form toggle, comment list.

- createpost.html
  - Post creation form with title/content fields.

- login.html
  - Login form and registration form.

Template-to-route map:

- / -> subforums.html
- /loginform -> login.html
- /subforum -> subforum.html
- /addpost -> createpost.html
- /viewpost -> viewpost.html

## 5. Suggested Group Reading Timeline (60 minutes)

1. 0-10 min: config.py + factory in __init__.py
2. 10-20 min: app.py startup + seeding
3. 20-35 min: models.py schemas + relationships
4. 35-50 min: routes.py handlers
5. 50-60 min: template flow + UI route mapping

## 6. Good First Refactors After Walkthrough

1. Split routes.py into auth routes, post routes, subforum routes.
2. Move breadcrumb HTML generation out of models layer.
3. Add route-level input guards for missing/invalid query params.
4. Replace startup seeding with explicit CLI command.
5. Add tests for login, create account, create post, add comment.
