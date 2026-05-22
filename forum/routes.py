from flask import render_template, request, redirect, url_for
from flask_login import current_user, login_user, logout_user
from flask_login.utils import login_required
import datetime
import re
from sqlalchemy import func
from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash
from forum.models import User, Post, Comment, Subforum, Message, Reaction, valid_content, valid_title, db, generateLinkPath, error
from forum.user import username_taken, email_taken, valid_username, valid_password

##
# This file needs to be broken up into several, to make the project easier to work on.
##

rt = Blueprint('routes', __name__, template_folder='templates')
REACTION_OPTIONS = (
	("like", "👍", "Like"),
	("dislike", "👎", "Dislike"),
	("heart", "❤️", "Heart"),
	("laugh", "😂", "Laugh"),
	("celebrate", "🎉", "Celebrate"),
	("fire", "🔥", "Fire"),
	("thinking", "🤔", "Thinking"),
	("sad", "😢", "Sad"),
)
ALLOWED_REACTIONS = {reaction_type for reaction_type, _, _ in REACTION_OPTIONS}

VIDEO_EXTENSIONS = (".mp4", ".webm", ".ogg")

def extract_youtube_id(url):
	patterns = (
		r'youtu\.be/([A-Za-z0-9_-]{11})',
		r'youtube\.com/watch\?(?:[^\s]*&)?v=([A-Za-z0-9_-]{11})',
		r'youtube\.com/shorts/([A-Za-z0-9_-]{11})',
		r'youtube\.com/embed/([A-Za-z0-9_-]{11})',
	)
	for pattern in patterns:
		match = re.search(pattern, url, flags=re.IGNORECASE)
		if match:
			return match.group(1)
	return None

def parse_video_url(video_url):
	if not video_url:
		return None

	url = video_url.strip()
	lower_url = url.lower()

	if lower_url.startswith("/static/") and lower_url.endswith(VIDEO_EXTENSIONS):
		return {"kind": "file", "src": url}

	if lower_url.startswith("http://") or lower_url.startswith("https://"):
		youtube_id = extract_youtube_id(url)
		if youtube_id:
			watch_url = "https://www.youtube.com/watch?v=" + youtube_id
			embed_url = "https://www.youtube.com/embed/" + youtube_id
			return {"kind": "youtube", "watch_url": watch_url, "embed_url": embed_url}
		if lower_url.endswith(VIDEO_EXTENSIONS):
			return {"kind": "file", "src": url}

	return None

def extract_post_video(content):
	marker_match = re.search(r'(?im)^\[video\]\s+(\S+)\s*$', content)
	if marker_match:
		video_url = marker_match.group(1)
		clean_content = re.sub(r'(?im)^\[video\]\s+\S+\s*$', '', content).strip()
		return clean_content, parse_video_url(video_url)

	trimmed_content = content.rstrip()
	if not trimmed_content:
		return content, None

	lines = trimmed_content.splitlines()
	last_line = lines[-1].strip()
	url_candidate = None

	if re.fullmatch(r'(?:https?://\S+|/static/\S+)', last_line):
		url_candidate = last_line
	else:
		markdown_link_match = re.fullmatch(r'\[[^\]]+\]\(([^)]+)\)', last_line)
		if markdown_link_match:
			url_candidate = markdown_link_match.group(1).strip()

	video_data = parse_video_url(url_candidate)
	if video_data:
		clean_content = "\n".join(lines[:-1]).strip()
		return clean_content, video_data

	return content, None

def valid_video_url(video_url):
	if not video_url:
		return True
	return parse_video_url(video_url) is not None

def get_reaction_data(post_ids):
	default_counts = {reaction_type: 0 for reaction_type, _, _ in REACTION_OPTIONS}
	counts_by_post = {}
	for post_id in post_ids:
		counts_by_post[post_id] = default_counts.copy()

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

@rt.route('/subforum')
def subforum():
	subforum_id = int(request.args.get("sub"))
	subforum = Subforum.query.filter(Subforum.id == subforum_id).first()
	if not subforum:
		return error("That subforum does not exist!")
	post_query = Post.query.filter(Post.subforum_id == subforum_id)
	if not current_user.is_authenticated:
		post_query = post_query.filter(Post.is_public == True)
	posts = post_query.order_by(Post.id.desc()).limit(50).all()
	subforumpath = subforum.path
	if not subforumpath:
		subforumpath = generateLinkPath(subforum.id)
		subforum.path = subforumpath

	subforums = Subforum.query.filter(Subforum.parent_id == subforum_id).all()
	post_ids = [post.id for post in posts]
	reaction_counts, user_reactions = get_reaction_data(post_ids)
	return render_template("subforum.html", subforum=subforum, posts=posts, subforums=subforums, path=subforumpath, reaction_counts=reaction_counts, user_reactions=user_reactions, reaction_options=REACTION_OPTIONS, current_path="/subforum?sub=" + str(subforum.id))

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
	if not post or (not post.is_public and not current_user.is_authenticated):
		return error("That post does not exist!")
	comment_error = request.args.get("comment_error")
	subforumpath = post.subforum.path
	if not subforumpath:
		subforumpath = generateLinkPath(post.subforum.id)
		post.subforum.path = subforumpath
	post_content, post_video = extract_post_video(post.content)
	comments = Comment.query.filter(Comment.post_id == postid).order_by(Comment.id.desc()) # no need for scalability now
	reaction_counts, user_reactions = get_reaction_data([post.id])
	return render_template("viewpost.html", post=post, path=subforumpath, post_content=post_content, post_video=post_video, comments=comments, comment_error=comment_error, post_reaction_counts=reaction_counts.get(post.id), user_reaction=user_reactions.get(post.id), reaction_options=REACTION_OPTIONS, current_path="/viewpost?post=" + str(post.id))

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
	video_url = request.form.get('video_url', '').strip()
	#check for valid posting
	errors = []
	retry = False
	if not valid_title(title):
		errors.append("Title must be between 4 and 140 characters long!")
		retry = True
	if not valid_content(content):
		errors.append("Post must be between 10 and 5000 characters long!")
		retry = True
	if video_url and not valid_video_url(video_url):
		errors.append("Video URL must be a YouTube link, direct .mp4/.webm/.ogg link, or /static/... video path.")
		retry = True
	if retry:
		return render_template("createpost.html",subforum=subforum,  errors=errors)
	if video_url:
		content = content.rstrip() + "\n\n[video] " + video_url
	post = Post(title, content, datetime.datetime.now())
	post.is_public = request.form.get("is_public") == "on"
	subforum.posts.append(post)
	user.posts.append(post)
	db.session.commit()
	return redirect("/viewpost?post=" + str(post.id))

@login_required
@rt.route('/settings')
def settings():
	return render_template("settings.html")

@login_required
@rt.route('/action_update_email', methods=['POST'])
def action_update_email():
	new_email = request.form.get('new_email')
	password = request.form.get('password')
	errorrs = []
	
	# Validate password
	if not current_user.check_password(password):
		errorrs.append("Password is incorrect!")
		return render_template("settings.html", errors=errorrs)
	
	# Check if email is already taken
	if email_taken(new_email):
		errorrs.append("This email is already in use!")
		return render_template("settings.html", errors=errorrs)
	
	# Update email
	current_user.email = new_email
	db.session.commit()
	return render_template("settings.html", success_message="Email updated successfully!")

@login_required
@rt.route('/action_change_password', methods=['POST'])
def action_change_password():
	current_password = request.form.get('current_password')
	new_password = request.form.get('new_password')
	confirm_password = request.form.get('confirm_password')
	errorrs = []
	
	# Validate current password
	if not current_user.check_password(current_password):
		errorrs.append("Current password is incorrect!")
		
	# Validate new passwords match
	if new_password != confirm_password:
		errorrs.append("New passwords do not match!")
		
	# Validate password format
	if not valid_password(new_password):
		errorrs.append("Password must be 6-40 characters with letters, numbers, and special characters (!@#%&)!")
		
	if errorrs:
		return render_template("settings.html", errors=errorrs)
	
	# Update password
	current_user.password_hash = generate_password_hash(new_password)
	db.session.commit()
	return render_template("settings.html", success_message="Password changed successfully!")

@login_required
@rt.route('/inbox')
def inbox():
	# Get all messages for current user (sent and received)
	received = Message.query.filter(Message.recipient_id == current_user.id).order_by(Message.sent_at.desc()).all()
	sent = Message.query.filter(Message.sender_id == current_user.id).order_by(Message.sent_at.desc()).all()
	return render_template("inbox.html", received=received, sent=sent)

@login_required
@rt.route('/compose', methods=['GET', 'POST'])
def compose():
	if request.method == 'GET':
		to_username = request.args.get('to', '')
		return render_template("compose.html", to_username=to_username)
	
	if request.method == 'POST':
		recipient_username = request.form.get('recipient')
		content = request.form.get('content')
		errors = []
		
		# Validate content
		if not content or len(content) < 1:
			errors.append("Message cannot be empty!")
		if len(content) > 5000:
			errors.append("Message cannot exceed 5000 characters!")
		
		# Find recipient
		recipient = User.query.filter(User.username == recipient_username).first()
		if not recipient:
			errors.append("User not found!")
		
		# Prevent self-messages
		if recipient and recipient.id == current_user.id:
			errors.append("You cannot send messages to yourself!")
		
		if errors:
			return render_template("compose.html", to_username=recipient_username, errors=errors)
		
		# Create and save message
		message = Message(current_user.id, recipient.id, content)
		db.session.add(message)
		db.session.commit()
		return redirect("/inbox")

@login_required
@rt.route('/message/<int:message_id>')
def view_message(message_id):
	message = Message.query.filter(Message.id == message_id).first()
	if not message:
		return error("Message not found!")
	
	# Verify user is either sender or recipient
	if message.sender_id != current_user.id and message.recipient_id != current_user.id:
		return error("You don't have permission to view this message!")
	
	# Mark as read if recipient is viewing it
	if message.recipient_id == current_user.id and not message.read:
		message.read = True
		db.session.commit()
	
	return render_template("message.html", message=message)

