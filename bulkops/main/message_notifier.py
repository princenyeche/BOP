from bulkops.database import Messages
from bulkops import db


def send_message(subject, sender, recipients, text_body, notify):
    msg = Messages(subject=subject, body=text_body, receiver_id=recipients, sender_id=sender)
    notify.add_notification("unread_msg_count", notify.new_messages())
    db.session.add(msg)
    db.session.commit()
