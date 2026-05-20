from flask import render_template, request, redirect, url_for
from flask_login import current_user, login_user, logout_user
from flask_login.utils import login_required
import datetime
from sqlalchemy import func
from flask import Blueprint, render_template, request, redirect, url_for
from forum.models import User, Post, Comment, Subforum, Reaction, valid_content, valid_title, db, generateLinkPath, error
from forum.user import username_taken, email_taken, valid_username

##
# This file needs to be broken up into several, to make the project easier to work on.
##

rt = Blueprint('routes', __name__, template_folder='templates')
ALLOWED_REACTIONS = {"like", "dislike", "heart"}

def get_reaction_data(post_ids):
	counts_by_post = {}
	for post_id in post_ids:
		counts_by_post[post_id] = {"like": 0, "dislike": 0, "heart": 0}

	if not post_ids:
		return counts_by_post, {}

	counts = db.session.query(
		Reaction.post_id,
		Reaction.reaction_type,
		func.count(Reaction.id)
	).filter(
		Reaction.post_id.in_(post_ids)
	).group_by(
		Reaction.post_id,
		Reaction.reaction_type
	).all()

	for post_id, reaction_type, total in counts:
		if reaction_type in ALLOWED_REACTIONS:
			counts_by_post[post_id][reaction_type] = total

	user_reactions = {}
	if current_user.is_authenticated:
		reactions = Reaction.query.filter(
			Reaction.user_id == current_user.id,
			Reaction.post_id.in_(post_ids)
		).all()
		for reaction in reactions:
			user_reactions[reaction.post_id] = reaction.reaction_type

	return counts_by_post, user_reactions

@rt.route('/action_login', methods=['POST'])
def action_login():
	username = request.form['username']
	password = request.form['password']
	user = User.query.filter(User.username == username).first()
	if user and user.check_password(password):
		login_user(user)
	else:
		errors = []
		errors.append("Username or password is incorrect!")
		return render_template("login.html", errors=errors)
	return redirect("/")


@login_required
@rt.route('/action_logout')
def action_logout():
	#todo
	logout_user()
	return redirect("/")

@rt.route('/action_createaccount', methods=['POST'])
def action_createaccount():
	username = request.form['username']
	password = request.form['password']
	email = request.form['email']
	errors = []
	retry = False
	if username_taken(username):
		errors.append("Username is already taken!")
		retry=True
	if email_taken(email):
		errors.append("An account already exists with this email!")
		retry = True
	if not valid_username(username):
		errors.append("Username is not valid!")
		retry = True
	# if not valid_password(password):
	# 	errors.append("Password is not valid!")
	# 	retry = True
	if retry:
		return render_template("login.html", errors=errors)
	user = User(email, username, password)
	if user.username == "admin":
		user.admin = True
	db.session.add(user)
	db.session.commit()
	login_user(user)
	return redirect("/")


@rt.route('/subforum')
def subforum():
	subforum_id = int(request.args.get("sub"))
	subforum = Subforum.query.filter(Subforum.id == subforum_id).first()
	if not subforum:
		return error("That subforum does not exist!")
	posts = Post.query.filter(Post.subforum_id == subforum_id).order_by(Post.id.desc()).limit(50).all()
	subforumpath = subforum.path
	if not subforumpath:
		subforumpath = generateLinkPath(subforum.id)
		subforum.path = subforumpath

	subforums = Subforum.query.filter(Subforum.parent_id == subforum_id).all()
	post_ids = [post.id for post in posts]
	reaction_counts, user_reactions = get_reaction_data(post_ids)
	return render_template("subforum.html", subforum=subforum, posts=posts, subforums=subforums, path=subforumpath, reaction_counts=reaction_counts, user_reactions=user_reactions, current_path="/subforum?sub=" + str(subforum.id))

@rt.route('/loginform')
def loginform():
	return render_template("login.html")


@login_required
@rt.route('/addpost')
def addpost():
	subforum_id = int(request.args.get("sub"))
	subforum = Subforum.query.filter(Subforum.id == subforum_id).first()
	if not subforum:
		return error("That subforum does not exist!")

	return render_template("createpost.html", subforum=subforum)

@rt.route('/viewpost')
def viewpost():
	postid = int(request.args.get("post"))
	post = Post.query.filter(Post.id == postid).first()
	if not post:
		return error("That post does not exist!")
	comment_error = request.args.get("comment_error")
	subforumpath = post.subforum.path
	if not subforumpath:
		subforumpath = generateLinkPath(post.subforum.id)
		post.subforum.path = subforumpath
	comments = Comment.query.filter(Comment.post_id == postid).order_by(Comment.id.desc()) # no need for scalability now
	reaction_counts, user_reactions = get_reaction_data([post.id])
	return render_template("viewpost.html", post=post, path=subforumpath, comments=comments, comment_error=comment_error, post_reaction_counts=reaction_counts.get(post.id), user_reaction=user_reactions.get(post.id), current_path="/viewpost?post=" + str(post.id))

@login_required
@rt.route('/action_react', methods=['POST'])
def action_react():
	post_id = int(request.args.get("post"))
	reaction_type = request.args.get("type", "").strip().lower()
	post = Post.query.filter(Post.id == post_id).first()
	if not post:
		return error("That post does not exist!")
	if reaction_type not in ALLOWED_REACTIONS:
		return error("Invalid reaction type!")

	reaction = Reaction.query.filter(
		Reaction.user_id == current_user.id,
		Reaction.post_id == post.id
	).first()

	if not reaction:
		reaction = Reaction(reaction_type)
		reaction.user_id = current_user.id
		reaction.post_id = post.id
		db.session.add(reaction)
	elif reaction.reaction_type == reaction_type:
		db.session.delete(reaction)
	else:
		reaction.reaction_type = reaction_type

	db.session.commit()
	redirect_target = request.form.get("next", "").strip()
	if not redirect_target.startswith("/"):
		redirect_target = "/viewpost?post=" + str(post.id)
	return redirect(redirect_target)

@login_required
@rt.route('/action_comment', methods=['POST'])
def comment():
	post_id = int(request.args.get("post"))
	post = Post.query.filter(Post.id == post_id).first()
	if not post:
		return error("That post does not exist!")
	content = request.form.get('content', '').strip()
	if len(content) < 1:
		return redirect("/viewpost?post=" + str(post_id) + "&comment_error=empty")
	postdate = datetime.datetime.now()
	comment = Comment(content, postdate)
	current_user.comments.append(comment)
	post.comments.append(comment)
	db.session.commit()
	return redirect("/viewpost?post=" + str(post_id))

@login_required
@rt.route('/action_post', methods=['POST'])
def action_post():
	subforum_id = int(request.args.get("sub"))
	subforum = Subforum.query.filter(Subforum.id == subforum_id).first()
	if not subforum:
		return redirect(url_for("subforums"))

	user = current_user
	title = request.form['title']
	content = request.form['content']
	#check for valid posting
	errors = []
	retry = False
	if not valid_title(title):
		errors.append("Title must be between 4 and 140 characters long!")
		retry = True
	if not valid_content(content):
		errors.append("Post must be between 10 and 5000 characters long!")
		retry = True
	if retry:
		return render_template("createpost.html",subforum=subforum,  errors=errors)
	post = Post(title, content, datetime.datetime.now())
	subforum.posts.append(post)
	user.posts.append(post)
	db.session.commit()
	return redirect("/viewpost?post=" + str(post.id))

