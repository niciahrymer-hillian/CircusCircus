"""
REFERENCE COPY: Message Model (models.py)

STRUCTURE:
- id: primary key
- sender_id: FK to User.id
- recipient_id: FK to User.id
- content: Text field for message body
- sent_at: DateTime timestamp (auto-set to now() on creation)
- read: Boolean flag (default False, set to True when recipient opens message)

RELATIONSHIPS:
- User model updated with:
  * sent_messages: relationship to Message where sender_id = user.id
  * received_messages: relationship to Message where recipient_id = user.id

METHODS:
- __init__(sender_id, recipient_id, content): Initialize new message with sender, recipient, and content. Sets sent_at to current time.
- get_time_string(): Returns human-readable relative time (e.g., "5 minutes ago", "2 days ago")

KEY FEATURES:
- Timestamps auto-generated on creation
- Foreign key constraints enforce data integrity
- read flag tracks if recipient has opened message
- Reuses get_time_string pattern from Post and Comment models
"""

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=False)
    read = db.Column(db.Boolean, default=False)

    def __init__(self, sender_id, recipient_id, content):
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.content = content
        self.sent_at = datetime.datetime.now()
        self.read = False
    
    def get_time_string(self):
        now = datetime.datetime.now()
        diff = now - self.sent_at
        seconds = diff.total_seconds()
        if seconds / (60 * 60 * 24 * 30) > 1:
            return " " + str(int(seconds / (60 * 60 * 24 * 30))) + " months ago"
        elif seconds / (60 * 60 * 24) > 1:
            return " " + str(int(seconds / (60 * 60 * 24))) + " days ago"
        elif seconds / (60 * 60) > 1:
            return " " + str(int(seconds / (60 * 60))) + " hours ago"
        elif seconds / (60) > 1:
            return " " + str(int(seconds / 60)) + " minutes ago"
        else:
            return "Just a moment ago!"
