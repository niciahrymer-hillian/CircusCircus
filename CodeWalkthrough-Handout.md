# CircusCircus Code Walkthrough Handout (1-Page)

Use this sheet while reading the code together.

## Goal

By the end, everyone should be able to explain:

- how the app starts,
- how requests are handled,
- how DB models connect,
- how routes map to templates.

## Read Order (Follow Exactly)

1. config.py
2. forum/__init__.py
3. forum/app.py
4. forum/models.py
5. forum/routes.py
6. templates in this order:
   - layout.html
   - header.html
   - subforums.html
   - subforum.html
   - viewpost.html
   - createpost.html
   - login.html

## What To Find In Each File

## 1) config.py

- SECRET_KEY
- SQLALCHEMY_DATABASE_URI
- FLASK_APP

Ask:

- Which values are dev-only?
- Which should come from environment variables?

## 2) forum/__init__.py

- create_app()
- blueprint registration
- db.init_app(app)

Ask:

- Where is app-wide wiring done?
- Where are routes attached?

## 3) forum/app.py

- app = create_app()
- login manager and user_loader
- seed logic: init_site() and add_subforum()
- index route: /

Ask:

- Why is seed logic running at startup?
- Should seeding be moved to a command?

## 4) forum/models.py (4 Schemas)

- User: auth fields + posts/comments relationships
- Post: title/content/date + user/subforum foreign keys
- Subforum: parent/child structure + posts
- Comment: content/date + user/post foreign keys

Also review:

- valid_title(), valid_content()
- generateLinkPath()

Ask:

- Are helpers in the best layer?
- Is breadcrumb HTML generation in the right place?

## 5) forum/routes.py (HTTP Handlers)

Auth/account:

- POST /action_login
- GET /action_logout
- POST /action_createaccount
- GET /loginform

Subforums/posts/comments:

- GET /subforum
- GET /addpost
- POST /action_post
- GET /viewpost
- POST/GET /action_comment

Ask:

- Which routes mutate DB data?
- Which routes require login?
- Where is input validation done?

## 6) Templates (Rendering Flow)

Base:

- layout.html wraps all pages
- header.html shows auth state and site info

Pages:

- subforums.html (home list)
- subforum.html (subforum + posts)
- viewpost.html (single post + comments)
- createpost.html (new post form)
- login.html (login + register)

Route map:

- / -> subforums.html
- /loginform -> login.html
- /subforum -> subforum.html
- /addpost -> createpost.html
- /viewpost -> viewpost.html

## One Full Request/Response Trace

Example: GET /subforum?sub=1

1. Browser sends HTTP request for /subforum?sub=1.
2. Flask's WSGI loop receives it and matches route to subforum() in routes.py.
3. Route runs SQLAlchemy queries:
   - load selected subforum,
   - load posts in that subforum,
   - load child subforums.
4. Route calls render_template("subforum.html", ...) with context data.
5. Jinja2 renders subforum.html, which extends layout.html and includes header.html.
6. Flask returns rendered HTML in HTTP response.
7. Browser renders page and fetches static CSS.

Black box vs your code:

- Flask/WSGI black box: socket/request parsing, route dispatch internals, response transport.
- Your code: handler logic, ORM queries, validation, template selection, context values.

## 30-Minute Fast Agenda

1. 0-5 min: config + factory
2. 5-10 min: app.py startup + seed
3. 10-18 min: models and relationships
4. 18-25 min: routes and DB writes
5. 25-30 min: templates and final Q&A

## End-of-Session Check

Each person should answer all 4:

1. Where does the app get config values?
2. Which route creates a post and where is validation?
3. How does a comment connect to both user and post?
4. Which template is the base wrapper for all pages?
