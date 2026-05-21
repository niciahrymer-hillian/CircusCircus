import datetime

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import current_user
from flask_login.utils import login_required

from forum.models import Post, Subforum, Comment, valid_content, valid_title, db, generateLinkPath, error

posts = Blueprint('posts', __name__, template_folder='templates')


@posts.route('/addpost')
@login_required
def addpost():
	subforum_id = int(request.args.get("sub"))
	subforum = Subforum.query.filter(Subforum.id == subforum_id).first()
	if not subforum:
		return error("That subforum does not exist!")

	return render_template("createpost.html", subforum=subforum)


@posts.route('/viewpost')
def viewpost():
	postid = int(request.args.get("post"))
	post = Post.query.filter(Post.id == postid).first()
	if not post:
		return error("That post does not exist!")
	if not post.subforum.path:
		subforumpath = generateLinkPath(post.subforum.id)
	comments = Comment.query.filter(Comment.post_id == postid).order_by(Comment.id.desc())
	return render_template("viewpost.html", post=post, path=subforumpath, comments=comments)


@posts.route('/action_post', methods=['POST'])
@login_required
def action_post():
	subforum_id = int(request.args.get("sub"))
	subforum = Subforum.query.filter(Subforum.id == subforum_id).first()
	if not subforum:
		return redirect(url_for("subforums"))

	user = current_user
	title = request.form['title']
	content = request.form['content']
	errors = []
	retry = False
	if not valid_title(title):
		errors.append("Title must be between 4 and 140 characters long!")
		retry = True
	if not valid_content(content):
		errors.append("Post must be between 10 and 5000 characters long!")
		retry = True
	if retry:
		return render_template("createpost.html", subforum=subforum, errors=errors)
	post = Post(title, content, datetime.datetime.now())
	subforum.posts.append(post)
	user.posts.append(post)
	db.session.commit()
	return redirect("/viewpost?post=" + str(post.id))
