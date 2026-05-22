"""
REFERENCE COPY: Messaging Routes (routes.py)

ROUTES ADDED:

1. GET /inbox
   - Protected by @login_required
   - Queries all received messages (recipient_id = current_user.id) ordered by sent_at DESC
   - Queries all sent messages (sender_id = current_user.id) ordered by sent_at DESC
   - Displays inbox.html with received and sent lists

2. GET /compose
   - Protected by @login_required
   - Optional query param: ?to=<username> (pre-fills recipient field)
   - Displays compose.html form

3. POST /compose
   - Protected by @login_required
   - Takes: recipient (username), content (message text)
   - Validates:
     * Content is not empty and not > 5000 chars
     * Recipient user exists
     * Cannot send to self
   - Creates Message object with sender_id=current_user.id
   - Saves to DB and redirects to /inbox

4. GET /message/<message_id>
   - Protected by @login_required
   - Fetches message and verifies access (must be sender or recipient)
   - If recipient viewing and message not read: marks message.read = True
   - Displays message.html with full content

VALIDATION:
- Content length validated (1-5000 chars)
- Recipient existence checked
- Self-message prevention
- Permission checks on view (only sender/recipient can view)
"""

@login_required
@rt.route('/inbox')
def inbox():
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
		
		if not content or len(content) < 1:
			errors.append("Message cannot be empty!")
		if len(content) > 5000:
			errors.append("Message cannot exceed 5000 characters!")
		
		recipient = User.query.filter(User.username == recipient_username).first()
		if not recipient:
			errors.append("User not found!")
		
		if recipient and recipient.id == current_user.id:
			errors.append("You cannot send messages to yourself!")
		
		if errors:
			return render_template("compose.html", to_username=recipient_username, errors=errors)
		
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
	
	if message.sender_id != current_user.id and message.recipient_id != current_user.id:
		return error("You don't have permission to view this message!")
	
	if message.recipient_id == current_user.id and not message.read:
		message.read = True
		db.session.commit()
	
	return render_template("message.html", message=message)
