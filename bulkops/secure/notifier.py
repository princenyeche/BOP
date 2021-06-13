from flask import render_template
from bulkops.email import send_message
from bulkops import bulk


def send_reset_password(user):
    token = user.get_reset_password_token()
    send_message(f"[{bulk.config['APP_NAME']}] Reset Your Password",
                 sender=bulk.config["ADMINS"][0],
                 recipients=[user.email],
                 text_body=render_template("email/reset_password.txt", user=user, token=token),
                 html_body=render_template("email/reset_password.html", user=user, token=token)
                 )


def send_contact_form(form):
    send_message(f"[{bulk.config['APP_NAME']}] Message from Contact Form",
                 sender=bulk.config["ADMINS"][0],
                 recipients=bulk.config["CONTACT_EMAIL"],
                 text_body=render_template("email/contact_form.txt", form=form),
                 html_body=render_template("email/contact_form.html", form=form)
                 )


def login_alert(user, ip_address, date):
    send_message(f"[{bulk.config['APP_NAME']}] Login Alert on your Account",
                 sender=bulk.config["ADMINS"][0],
                 recipients=[user.email],
                 text_body=render_template("email/login_alert.txt", user=user, ip_address=ip_address,
                                           date=date),
                 html_body=render_template("email/login_alert.html", user=user, ip_address=ip_address,
                                           date=date)
                 )


def pre_config(default, date, x):
    send_message(f"[{bulk.config['APP_NAME']}] Automatic Account Creation",
                 sender=bulk.config["ADMINS"][0],
                 recipients=[default.email],
                 text_body=render_template("email/auto_create.txt", default=default, date=date, x=x),
                 html_body=render_template("email/auto_create.html", default=default, date=date, x=x)
                 )
    
    
def send_welcome_email(user):
    send_message(f"[{bulk.config['APP_NAME']}] Thank You for Signing Up!",
                 sender=bulk.config["ADMINS"][0],
                 recipients=[user.email],
                 text_body=render_template("email/app_welcome_email.txt", user=user),
                 html_body=render_template("email/app_welcome_email.html", user=user)
                 )

    
def send_confirm_email(user, subject, confirm_url):
    send_message(f"[{bulk.config['APP_NAME']}] {subject}",
                 sender=bulk.config["ADMINS"][0],
                 recipients=[user.email],
                 text_body=render_template("email/email_activation.txt", user=user, confirm_url=confirm_url),
                 html_body=render_template("email/email_activation.html", user=user, confirm_url=confirm_url))
