from flask import render_template
from bulkops.main.message_notifier import send_user_message
from bulkops.email import send_message
from bulkops import bulk


def send_app_messages(admin, user, form):
    send_user_message(f"[{bulk.config['APP_NAME']}] {form.get('job')}",
                      sender=admin.id,
                      recipients=user.id,
                      text_body=render_template("email/app_notice_form.txt", user=user, form=form),
                      notify=user)


def send_error_messages(admin, user, form):
    send_user_message(f"[{bulk.config['APP_NAME']}] {form.get('job')}",
                      sender=admin.id,
                      recipients=user.id,
                      text_body=render_template("email/app_error_form.txt", user=user, form=form),
                      notify=user)


def send_admin_message(admin, user, form):
    send_message(f"[{bulk.config['APP_NAME']}] {user.username.capitalize()} sent you a Message!",
                 sender=bulk.config["ADMINS"][0],
                 recipients=[admin.email],
                 text_body=render_template("email/send_admin_message.txt", user=user, form=form),
                 html_body=render_template("email/send_admin_message.html", user=user, form=form)
                 )


def send_goodbye_message(user):
    send_message(f"[{bulk.config['APP_NAME']}] account deletion confirmation!",
                 sender=bulk.config["ADMINS"][0],
                 recipients=[user.email],
                 text_body=render_template("email/app_goodbye_email.txt", user=user),
                 html_body=render_template("email/app_goodbye_email.html", user=user)
                 )

    
def send_user_exit(user, admin, date):
    send_message(f"[{bulk.config['APP_NAME']}] user deletion confirmation!",
                 sender=bulk.config["ADMINS"][0],
                 recipients=[admin.email],
                 text_body=render_template("email/notify_user_exit.txt", user=user, admin=admin, date=date),
                 html_body=render_template("email/notify_user_exit.html", user=user, admin=admin, date=date)
                 )
