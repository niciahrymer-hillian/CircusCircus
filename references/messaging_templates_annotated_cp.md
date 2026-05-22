"""
REFERENCE COPY: Messaging Templates

Three templates created for private messaging feature:

1. inbox.html
   - Lists received and sent messages in two sections
   - Received messages show:
     * Sender username
     * "NEW" badge if unread
     * Message preview (first 100 chars)
     * Timestamp (relative: "5 minutes ago")
     * "View Full Message" link to /message/<id>
     * "Reply" link pre-fills /compose?to=<sender>
   - Sent messages show same layout without NEW badge
   - Each section shows "No messages" if empty
   - "Compose New Message" button at top

2. compose.html
   - Form with two fields: recipient (text input) and content (textarea)
   - Recipient field pre-filled from query param ?to=<username>
   - Content limited to 5000 chars (noted in form)
   - Errors displayed in red box if validation fails
   - Submit button sends POST to /compose
   - Cancel button returns to /inbox

3. message.html
   - Displays single message with:
     * Header showing "From:" or "To:" depending on sender/recipient
     * Relative timestamp
     * Full message content in pre-wrapped format
     * Action buttons: "Reply" or "Send Message" + "Back to Inbox"
   - Permission check ensures only sender/recipient can view
   - Read status auto-set when recipient opens

STYLING:
- Bootstrap-compatible responsive layout
- Unread messages (received) have light blue background (#e8f4f8)
- Read messages have light gray background (#f9f9f9)
- Sent messages consistently light gray
- Link to reply/send is embedded in each message card
"""
