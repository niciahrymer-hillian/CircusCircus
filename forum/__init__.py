from flask import Flask
from markupsafe import Markup
import mistune
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

    app.jinja_env.filters['markdown'] = render_markdown

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
