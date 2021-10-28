import re
import requests
import string
import random
from flask import render_template, flash, redirect, url_for
from bulkops.database import User, Messages
from flask_login import current_user, login_user, login_required
from flask import request
from flask_login import logout_user
from werkzeug.urls import url_parse
from bulkops import db
from bulkops.secure.forms import RegistrationForm, LoginForm, ResetPasswordForm, ForgetEmailForm, ContactForm
from bulkops.secure.notifier import send_reset_password, send_contact_form, login_alert, pre_config, \
    send_welcome_email, send_confirm_email
from bulkops import bulk
from datetime import datetime as dt
from time import sleep

# display Fri, 10 Jul 2020 - 05:22 PM
date = dt.now().strftime("%a, %d %b %Y - %I:%M %p")
copy = dt.now().strftime("%Y")


def stringer(n: int = 15):
    char = string.ascii_lowercase
    return "".join(random.choice(char) for j in range(n))


x = f"{stringer(19)}"


@bulk.route("/signin", methods=["GET", "POST"])
def signin():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    error = None
    form = LoginForm()
    # Check if a default user exist, if not create one
    default = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    ipaddress = form.ipaddress.data
    if default is None:
        default_user()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            error = "Invalid username or password"
            flash(error, category="alert-danger")
            return redirect(url_for("signin"))
        login_user(user, remember=form.remember_me.data)
        # Check if the app version is not the latest, then send a notification
        version_checker()
        # send a notification for successful login if option is chosen in config
        if user.notify_me == "Yes":
            date = form.datetime.data
            login_alert(user, ipaddress, date)
        # Use if you want the user to always be redirected to login page or the link provided
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)
    # else  return redirect(url_for('index'))
    return render_template("/secure/signin.html", title="Sign In to your Account", form=form,
                           error=error, copy=copy)


@bulk.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@bulk.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    # Check if a default user exist, if not create one
    default = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    if default is None:
        default_user()
    if form.validate_on_submit():
        s = form.password.data
        a = re.search("[!@#$%&*]", s)
        y = form.instances.data
        i = len(s)
        k = form.username.data
        mistake = {"validate": e for e in string.punctuation if y.startswith(e)}
        valid = {"validate": e for e in string.punctuation if k.startswith(e) or k.endswith(e)}
        # Additional mechanism, to check reserved usernames
        if k.lower() in bulk.config["APP_RESERVED_KEYWORDS"]:
            flash("This username is already taken, choose another")
        elif len(k) < 4:
            flash("Your username must be minimum 4 characters in length")
        elif len(k) > 30:
            flash("Your username is too long, it must be within 30 characters in length")
        elif "validate" in valid:
            if valid.get('validate') is not None:
                flash("Your username must not start or end with a special character.")
        elif " " in k:
            flash("Please do not use space characters in your username.")
        elif y.startswith("http") or y.startswith("www"):
            flash("Please remove the \"http://\" or \"https://\" or \"www\" from the URL")
            # return redirect(request.url) - this clears the form
        elif i < 8:
            flash("Your password must be equal or greater than 8 characters in length")
        elif i > 64:
            flash("Your password is too long, it must be within 64 characters in length")
        elif a is None:
            flash("You must use at least one of this special characters (!, @, #, $, %, &, or *) in your password!")
        elif "validate" in mistake:
            if mistake.get('validate') is not None:
                flash(f"Your URL \"{y}\" is not the expected value. Do you mean {y.lstrip(string.punctuation)} instead?")
        elif y.endswith("atlassian.net") or y.endswith("jira-dev.com") \
                or y.endswith("jira.com"):
            pattern = r"[^\w\d\|\|\.\|\|-]"
            sanity_url = re.findall(pattern, y)
            if len(sanity_url) > 0:
                # The URL must contain an invalid character here, so we don't accept it.
                flash(f"Your URL \"{y}\" doesn't seem valid, please check it again.")
            elif len(sanity_url) == 0:
                # Sanity check for valid urls
                user = User(username=form.username.data.lower(),
                        email=form.email.data.lower(), instances=form.instances.data.lower())
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                token = User.create_user_confirmation(user.email)
                confirm_url = url_for("confirmation_email", token=token, _external=True)
                subject = "Confirm Your Email Address"
                success = "Congratulations, you have been registered successfully. we also sent you a welcome message!😉" \
                      " and please verify your email as we sent a verification link too. "
                flash(success, category="alert-success")
                welcome_message(extract=form.username.data.lower())
                sleep(1.0)
                send_confirm_email(user, subject, confirm_url)
                return redirect(url_for("signin"))
        else:
            flash("Instance URL must end with \"atlassian.net\", \"jira.com\" or \"jira-dev.com\"")
            # return redirect(request.url) - this clears the form
    return render_template("/secure/signup.html", title="Register for an Account",
                           form=form, copy=copy)


@bulk.route("/reset_request", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ForgetEmailForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_password(user)
        success = "Check your email for Password reset details..."
        flash(success, category="alert-success")
        return redirect(url_for("signin"))
    return render_template("secure/reset_request.html", title="Forgot Password", form=form, copy=copy)


@bulk.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("index"))
    form = ResetPasswordForm()
    error = None
    if form.validate_on_submit():
        s = form.password.data
        a = re.search("[!@#$%&*]", s)
        y = len(s)
        if y < 8:
            error = "Your password must be equal or greater than 8 characters in length"
            flash(error)
        elif y > 64:
            flash("Your password is too long, it must be within 64 characters in length")
        elif a is None:
            error = "You must use at least one of this special characters (!, @, #, $, %, &, or *) in your password!"
            flash(error)
        else:
            user.set_password(form.password.data)
            db.session.commit()
            success = "Your Password has been reset"
            flash(success, category="alert-success")
            return redirect(url_for("signin"))
    return render_template("secure/password_reset.html", title="Recover Password", form=form, error=error, copy=copy)


@bulk.route("/confirm_email/<token>", methods=["GET", "POST"])
@login_required
def confirmation_email(token):
    try:
        email = User.getuser_confirmation_token(token)
        user = User.query.filter_by(email=email).first_or_404()
        user.confirm_period = dt.utcnow()
        user.confirm_user = True
        db.session.add(user)
        db.session.commit()
    except:
        error = "Your activation link isn't valid or it has expired."
        flash(error, "alert-danger")
    return redirect(url_for("index"))


@bulk.route("/unconfirmed", methods=["GET", "POST"])
@login_required
def unconfirmed():
    if current_user.confirm_user is True:
        return redirect(url_for("index"))
    return render_template("secure/unconfirmed.html", Messages=Messages, title="Verification of your account!")


@bulk.route("/resend", methods=["GET", "POST"])
@login_required
def resend():
    token = User.create_user_confirmation(current_user.email)
    confirm_url = url_for("confirmation_email", token=token, _external=True)
    subject = "Resending verification link"
    send_confirm_email(current_user, subject, confirm_url)
    success = "A new confirmation email has been sent!"
    flash(success, "alert-success")
    return redirect(url_for("unconfirmed"))


@bulk.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if request.method == "POST":
        send_contact_form(form)
        success = "Your Message was sent successfully..."
        flash(success, category="alert-success")
    else:
        error = "We're unable to send your Message..."
        flash(error, category="alert-danger")
    return redirect(url_for("signin"))


def default_user():
    # create the default user always
    default = User(username=f"{bulk.config['APP_ADMIN_USERNAME']}".lower(),
                   email=f"{bulk.config['CONTACT_EMAIL'][0]}".lower(),
                   instances=f"{bulk.config['APP_DEFAULT_INSTANCE']}".lower())
    default.set_password(x)
    db.session.add(default)
    db.session.commit()
    default = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    # send the admin user the account notification details
    pre_config(default, date, x)

                   
# send a message to the user only once, if the version is not the latest.
def version_checker():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    current_version = bulk.config["APP_VERSION"]
    lookup_version = requests.get(bulk.config["APP_VERSION_URL"]).text
    message_exist = user.received_messages.order_by(Messages.subject.desc()).all()
    check_sub = [m.subject for m in message_exist]
    phrase = f"You need to Upgrade to {lookup_version}!"
    if current_version < lookup_version and phrase not in check_sub \
            and user.username != admin.username:
        upgrade_url = bulk.config["APP_UPGRADE_URL"]
        head_subject = phrase
        upgrade = f"""Hi {user.username.capitalize()},\n
                  It seems that you are probably using a lower version of this App\n
                  Please upgrade by visiting this URL {upgrade_url}\n 
                  Thanks {admin.username.capitalize()}"""
        send = Messages(subject=head_subject, body=upgrade, receiver_id=user.id, sender_id=admin.id)
        db.session.add(send)
        db.session.commit()

   
# sends a welcome message & email upon new sign up
def welcome_message(extract):
    user = User.query.filter_by(username=extract).first_or_404()
    admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    phrase = f"Thanks for Signing up {user.username.capitalize()}!"
    subject = phrase
    message = f"""
              Hi {user.username.capitalize()},\n 
              Thanks for signing up for {bulk.config["APP_NAME"]}.\n 
              You can start by using any one of our features on the home screen; also don't\n
              forget to update your API token before you begin.\n
              Cheers, {admin.username.capitalize()}."""
    send = Messages(subject=subject, body=message, receiver_id=user.id, sender_id=admin.id)
    db.session.add(send)
    db.session.commit()
    send_welcome_email(user)
