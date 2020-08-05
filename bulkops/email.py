from threading import Thread
from flask_mail import Message
from bulkops import mail
from bulkops import bulk


def send_async_email(bulk, msg):
    with bulk.app_context():
        mail.send(msg)


def send_message(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(bulk, msg)).start()
