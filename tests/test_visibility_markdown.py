import datetime

import pytest
from flask_login import LoginManager

import config
from forum import create_app
from forum.models import Comment, Post, Subforum, User, db


@pytest.fixture()
def app(tmp_path):
    db_file = tmp_path / "test.db"
    original_uri = config.Config.SQLALCHEMY_DATABASE_URI
    config.Config.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_file}"

    app = create_app()
    app.config.update(TESTING=True)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()

    config.Config.SQLALCHEMY_DATABASE_URI = original_uri


@pytest.fixture()
def client(app):
    return app.test_client()


def _seed_user(username="alice", email="alice@example.com"):
    user = User(email, username, "password123")
    db.session.add(user)
    db.session.commit()
    return user.id


def _seed_subforum(title="General", description="General discussion"):
    subforum = Subforum(title, description)
    db.session.add(subforum)
    db.session.commit()
    return subforum.id


def _seed_post(subforum, user, title, content, is_public):
    post = Post(title, content, datetime.datetime.now())
    post.is_public = is_public
    post.subforum_id = subforum
    post.user_id = user
    db.session.add(post)
    db.session.commit()
    return post.id


def _log_in(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user)
        session["_fresh"] = True


def test_subforum_hides_private_posts_for_anonymous_users(client, app):
    with app.app_context():
        user = _seed_user()
        subforum = _seed_subforum()
        _seed_post(subforum, user, "Public Post", "Visible to everyone", True)
        _seed_post(subforum, user, "Private Post", "Visible to logged in only", False)

    response = client.get(f"/subforum?sub={subforum}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Public Post" in body
    assert "Private Post" not in body
    assert "visibilitybadge" not in body


def test_subforum_shows_private_badge_for_authenticated_users(client, app):
    with app.app_context():
        user = _seed_user()
        subforum = _seed_subforum()
        _seed_post(subforum, user, "Members Only", "Private content", False)

    _log_in(client, user)
    response = client.get(f"/subforum?sub={subforum}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Members Only" in body
    assert "Private" in body
    assert "visibilitybadge" in body


def test_viewpost_blocks_private_post_for_anonymous_users(client, app):
    with app.app_context():
        user = _seed_user()
        subforum = _seed_subforum()
        post = _seed_post(subforum, user, "Secret", "Hidden", False)

    response = client.get(f"/viewpost?post={post}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "That post does not exist!" in body


def test_viewpost_renders_markdown_and_escapes_html(client, app):
    with app.app_context():
        user = _seed_user()
        subforum = _seed_subforum()
        content = "**bold** and *italic* <script>alert('x')</script>"
        post = _seed_post(subforum, user, "Markdown", content, True)

    response = client.get(f"/viewpost?post={post}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<strong>bold</strong>" in body
    assert "<em>italic</em>" in body
    assert "&lt;script&gt;alert('x')&lt;/script&gt;" in body


def test_viewpost_shows_private_badge_for_authenticated_users(client, app):
    with app.app_context():
        user = _seed_user()
        subforum = _seed_subforum()
        post = _seed_post(subforum, user, "Staff Note", "Private body", False)
        comment = Comment("hello", datetime.datetime.now())
        comment.user_id = user
        comment.post_id = post
        db.session.add(comment)
        db.session.commit()

    _log_in(client, user)
    response = client.get(f"/viewpost?post={post}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Staff Note" in body
    assert "Private" in body
    assert "visibilitybadge" in body


def test_action_post_sets_visibility_from_checkbox(client, app):
    with app.app_context():
        user = _seed_user("poster", "poster@example.com")
        subforum = _seed_subforum("Posting", "Posting tests")

    _log_in(client, user)

    response_private = client.post(
        f"/action_post?sub={subforum}",
        data={
            "title": "Private From Form",
            "content": "This content is long enough to be accepted.",
        },
    )
    assert response_private.status_code == 302

    response_public = client.post(
        f"/action_post?sub={subforum}",
        data={
            "title": "Public From Form",
            "content": "This content is also long enough to be accepted.",
            "is_public": "on",
        },
    )
    assert response_public.status_code == 302

    with app.app_context():
        private_post = Post.query.filter(Post.title == "Private From Form").first()
        public_post = Post.query.filter(Post.title == "Public From Form").first()

        assert private_post is not None
        assert public_post is not None
        assert private_post.is_public is False
        assert public_post.is_public is True
