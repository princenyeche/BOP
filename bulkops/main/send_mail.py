from flask import render_template
from bulkops.main.message_notifier import send_message
from bulkops import bulk


def send_app_messages(admin, user, form):
    send_message(f"[{bulk.config['APP_NAME']}] Requested Jobs Completed",
                 sender=admin.id,
                 recipients=user.id,
                 text_body=render_template("email/app_notice_form.txt", user=user, form=form),
                 notify=user)


def send_error_messages(admin, user, form):
    send_message(f"[{bulk.config['APP_NAME']}] Requested Jobs Failed",
                 sender=admin.id,
                 recipients=user.id,
                 text_body=render_template("email/app_error_form.txt", user=user, form=form),
                 notify=user)
