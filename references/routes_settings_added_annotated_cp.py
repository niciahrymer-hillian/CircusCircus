"""
REFERENCE COPY: User Settings Routes
Added to forum/routes.py

ROUTES ADDED:

1. GET /settings
   - Protected by @login_required
   - Displays settings.html form
   - Accessible to authenticated users only

2. POST /action_update_email
   - Protected by @login_required
   - Takes: new_email, password
   - Validates:
     * Current password matches (using check_password)
     * New email not already in use (using email_taken)
   - Updates User.email on success
   - Returns settings page with success message

3. POST /action_change_password
   - Protected by @login_required
   - Takes: current_password, new_password, confirm_password
   - Validates:
     * Current password is correct
     * New passwords match each other
     * Password meets format requirements (using valid_password)
   - Updates User.password_hash using generate_password_hash
   - Returns settings page with success message

VALIDATION FLOW:
- Password validation uses check_password_hash via User.check_password()
- New password hashed using generate_password_hash from werkzeug.security
- Email uniqueness checked with email_taken() helper
- Password format checked with valid_password() from user.py
"""

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
