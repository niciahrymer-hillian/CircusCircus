from flask import Flask
from markupsafe import Markup
import mistune
import re
from forum.routes import rt
from forum.auth import auth
from forum.posts import posts
from forum.comments import comments

def create_app():
    """Construct the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')

    markdown_renderer = mistune.create_markdown(escape=True)

    def render_markdown(text):
        if not text:
            return ""
        return Markup(markdown_renderer(text))

    def regex_replace(text, pattern, replacement="", flags=""):
        if not text:
            return ""

        re_flags = 0
        if "i" in flags:
            re_flags |= re.IGNORECASE
        if "m" in flags:
            re_flags |= re.MULTILINE
        if "s" in flags:
            re_flags |= re.DOTALL

        return re.sub(pattern, replacement, text, flags=re_flags)

    app.jinja_env.filters['markdown'] = render_markdown
    app.jinja_env.filters['regex_replace'] = regex_replace

    # I think more blueprints might be used to break routes up into things like
    # post_routes
    # subforum_routes
    # etc
    app.register_blueprint(rt)
    app.register_blueprint(auth)
    app.register_blueprint(posts)
    app.register_blueprint(comments)
    # Set globals
    from forum.models import db
    db.init_app(app)
    
    with app.app_context():
        # Add some routes
        db.create_all()
        return app
