import json
import os
import re
import csv
import sys
import time
import string
import typing as t
from copy import deepcopy
from flask import render_template, flash, redirect, url_for, current_app, request, \
    jsonify, Response
from bulkops.database import User, Audit, Messages, Notification, Jobs
from flask_login import current_user, login_required, fresh_login_required
from bulkops import db, bulk
from bulkops.main.forms import SettingsForm, TokenForm, CreateGroupForm, \
    DeleteUserForm, CreateUsersForm, AddUserGroupForm, RemoveUserGroupForm, DeleteGroupForm, \
    ChangeProjectLeadForm, DeleteProjectForm, DeleteIssuesForm, UploadForm, MessageForm, \
    OrgForm
from datetime import datetime
from werkzeug.utils import secure_filename
from bulkops.tasks.jobs import set_job_progress
from bulkops.main.send_mail import send_app_messages, send_error_messages, send_admin_message, send_goodbye_message, \
    send_user_exit
from bulkops.secure.user_checker import validate_account
from collections import deque, namedtuple
from jiraone import LOGIN, endpoint

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = "Files"
our_dir = os.path.join(basedir, UPLOAD_FOLDER)

if not os.path.exists(our_dir):
    os.mkdir(our_dir)


@bulk.route("/", methods=["GET", "POST"])
@bulk.route("/index", methods=["GET", "POST"])
@login_required
@validate_account
def index():
    data = None
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    if request.method == "GET":
        data = LOGIN.get(endpoint.myself())
        if data.status_code != 200:
            flash("Your API Token is invalid, please go to the Settings > Configurations page to have it sorted")
    return render_template("/users/layout.html", title=f"Home page :: {bulk.config['APP_NAME_SINGLE']}",
                           Messages=Messages, data=data)


@bulk.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bulk.route("/settings", methods=["GET", "POST"])
@fresh_login_required
@validate_account
def settings():
    form = SettingsForm()
    success = None
    error = None
    v = current_user.instances
    if form.validate_on_submit() and request.method == "POST":
        s = form.password.data
        a = re.search("[!@#$%&*]", s)
        y = form.instances.data
        i = len(s)
        mistake = {"validate": e for e in string.punctuation if y.startswith(e)}
        if y.startswith("http") or y.startswith("www"):
            error = "Please remove the \"http://\" or \"https://\" or \"www\" from the URL"
            flash(error)
        elif i < 8:
            error = "Your password must be equal or greater than 8 characters in length"
            flash(error)
        elif i > 64:
            error = "Your password is too long, it must be within 64 characters in length"
            flash(error)
        elif a is None:
            error = "You must use at least one of this special characters (!, @, #, $, %, &, or *) in your password!"
            flash(error)
        elif "validate" in mistake:
            if mistake.get("validate") is not None:
                error = f"Your URL \"{y}\" is not the expected value. Do you mean {y.lstrip(string.punctuation)} " \
                        f"instead?"
                flash(error)
        elif y.endswith("atlassian.net") or y.endswith("jira-dev.com") \
                or y.endswith("jira.com"):
            pattern = r"[^\w\d\|\|\.\|\|-]"
            sanity_url = re.findall(pattern, y)
            if len(sanity_url) > 0:
                # The URL must contain an invalid character here, so we don't accept it.
                error = f"Your URL \"{y}\" doesn't seem valid, please check it again."
                flash(error)
            elif len(sanity_url) == 0:
                # Sanity check for valid urls
                capture = y.split(".")
                if len(capture) == 3:
                    if capture[1].startswith("atlassian") or capture[1].startswith("jira") \
                            or capture[1].startswith("jira-dev"):
                        user = User.query.filter_by(username=current_user.username).first()
                        current_user.instances = form.instances.data
                        user.set_password(form.password.data)
                        display_name = f"{current_user.username}".capitalize()
                        activity = f"Changes made to settings from:{v}  To:{current_user.instances}"
                        audit_log = f"CHANGES: Configuration"
                        ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                                   user_id=current_user.id)
                        db.session.add(ad)
                        db.session.add(user)
                        db.session.commit()
                        success = "Your changes have been saved."
                        flash(success)
                    else:
                        error = "You're still typing the wrong URL."
                        flash(error)
                elif len(capture) != 3:
                    error = f"Please you need to thoroughly review what you type as URL. This URL: {y} is incorrect."
                    flash(error)
        else:
            error = "Instance URL must end with \"atlassian.net\", \"jira.com\" or \"jira-dev.com\""
            flash(error)
    elif request.method == "GET":
        form.email.data = current_user.email
        form.instances.data = current_user.instances
    return render_template("/config/settings.html", title=f"Edit Settings :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/users", methods=["GET", "POST"])
@login_required
@validate_account
def users():
    form = CreateUsersForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        if form.users_opt.data == "JIRA":
            payload = (
                {
                    "emailAddress": form.users_email.data,
                    "displayName": form.users_name.data

                }
            )
            data = LOGIN.post(endpoint.jira_user(), payload=payload)
            if data.status_code != 201:
                error = "Unable to create user, probably due to an error"
                display_name = f"{current_user.username}".capitalize()
                activity = "Failure creating JIRA user"
                audit_log = "ERROR: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(error)
            else:
                success = "User created successfully,please check your admin hub to confirm."
                display_name = f"{current_user.username}".capitalize()
                activity = "Created JIRA user successfully"
                audit_log = "SUCCESS: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(success)
        elif form.users_opt.data == "JSD":
            payload = (
                {
                    "email": form.users_email.data,
                    "displayName": form.users_name.data

                }
            )
            data = LOGIN.post(endpoint.create_customer(), payload=payload)
            if data.status_code != 201:
                error = "Unable to create customer, check the audit log."
                display_name = f"{current_user.username}".capitalize()
                activity = "Failure creating JSM User"
                audit_log = "ERROR: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(error)
            else:
                success = "Customer user created successfully."
                display_name = f"{current_user.username}".capitalize()
                activity = "JSM user created"
                audit_log = "SUCCESS: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(success)
    return render_template("pages/users.html", title=f"User Creation :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/users/bulk_users", methods=["GET", "POST"])
@login_required
@validate_account
def bulk_users():
    form = UploadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    create_dir(our_dir, save_path)
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect.Please check it out"
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        form_selection = form.upload_opt.data
        if current_user.get_job_in_progress("bulk_users_creation"):
            error = "A bulk user job is in progress, please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |displayName | email|
                loop_count = [u for u in reader]
                another_read = deepcopy(loop_count)
                width = [len(k) for k in another_read if k]  # get the number of columns
                number_of_loops = len(loop_count)
                if width[0] > 3:
                    error = "Expecting a CSV file with max 3 columns not more."
                    flash(error)
                elif width[0] < 2:
                    error = "Invalid number of columns received, please click the \"Need help\" " \
                            "button to see the expected format."
                    flash(error)
                elif width[0] == 2:
                    # for CSV is |displayName | email|
                    # Format for CSV is |displayName | email|
                    if 1 < number_of_loops < 10:
                        if form_selection == "JSD":
                            for u in loop_count:
                                payload = (
                                    {
                                        "email": u[1],
                                        "displayName": u[0]

                                    }
                                )
                                data = LOGIN.post(endpoint.create_customer(), payload=payload)
                            if data.status_code != 201:
                                error = "Unable to create multiple customer, an error occurred."
                                display_name = f"{current_user.username}".capitalize()
                                activity = "Failure creating bulk JSM users {}".format(u[0])
                                audit_log = "ERROR: {}".format(data.status_code)
                                auto_commit(display_name, activity, audit_log)
                                os.remove(o)
                                flash(error)
                            else:
                                success = "Multiple customer users created successfully."
                                display_name = f"{current_user.username}".capitalize()
                                activity = "Success in creating bulk JSM users"
                                audit_log = "SUCCESS: {}".format(data.status_code)
                                auto_commit(display_name, activity, audit_log)
                                os.remove(o)
                                flash(success)
                        elif form_selection == "JIRA":
                            for u in loop_count:
                                payload = (
                                    {
                                        "emailAddress": u[1],
                                        "displayName": u[0]

                                    }
                                )
                                data = LOGIN.post(endpoint.jira_user(), payload=payload)
                            if data.status_code != 201:
                                error = "Unable to create multiple Jira users, something went wrong."
                                display_name = f"{current_user.username}".capitalize()
                                activity = "Failure in creating bulk Jira users {}".format(u[0])
                                audit_log = "ERROR: {}".format(data.status_code)
                                auto_commit(display_name, activity, audit_log)
                                os.remove(o)
                                flash(error)
                            else:
                                success = "Multiple Jira users created successfully."
                                display_name = f"{current_user.username}".capitalize()
                                activity = "Success in creating bulk Jira users"
                                audit_log = "SUCCESS: {}".format(data.status_code)
                                auto_commit(display_name, activity, audit_log)
                                os.remove(o)
                                flash(success)
                    elif number_of_loops > 10:
                        current_user.launch_jobs("bulk_users_creation", "Bulk creation of users", loop_count,
                                                 form_selection)
                        success = "A Job has been submitted for bulk user creation, please check the audit log page " \
                                  "for the updated result."
                        db.session.commit()
                        os.remove(o)
                        flash(success)
                elif width[0] == 3:
                    if form_selection == "JSD":
                        error = "You cannot add JSM customers to a group, add them to organization from " \
                                "your JSM project interface."
                        flash(error)
                    else:
                        # your CSV should be |displayName|email| groupname|
                        """
                        displayName,email,groupname
                        Prince Nyeche,prince.nyeche@example.com,star-trek~>Managers~>group-managers
                        Prince Crown,prince.crown@example.com,project-admin~>HR Groups~>IT Managers
                        """
                        current_user.launch_jobs("bulk_users_group_creation", "Bulk creation of users and groups",
                                                 loop_count, form_selection)
                        success = "A Job has been submitted for bulk users and groups creation, please check " \
                                  "the audit log page for the updated result."
                        db.session.commit()
                        os.remove(o)
                        flash(success)
    return render_template("users/sub_pages/_create_jira_user.html",
                           title=f"Bulk User Creation :: {bulk.config['APP_NAME_SINGLE']}", error=error,
                           success=success, form=form, Messages=Messages)


@bulk.route("/bulk_users_creation")
def bulk_users_creation(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            i = 0
            set_job_progress(0)
            if args[1] == "JSD":
                count = len(args[0])
                for u in args[0]:
                    payload = (
                        {
                            "email": u[1],
                            "displayName": u[0]

                        }
                    )
                    data = LOGIN.post(endpoint.create_customer(), payload=payload)
                    i += 1
                    set_job_progress(100 * i // count)
                    if data.status_code != 201:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure creating bulk JSM users {}".format(u[0])
                        audit_log = "ERROR: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Success in creating bulk JSM users"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
            elif args[1] == "JIRA":
                count = len(args[0])
                for u in args[0]:
                    payload = (
                        {
                            "emailAddress": u[1],
                            "displayName": u[0]

                        }
                    )
                    data = LOGIN.post(endpoint.jira_user(), payload=payload)
                    i += 1
                    set_job_progress(100 * i // count)
                    if data.status_code != 201:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure in creating bulk JIRA users {}".format(u[0])
                        audit_log = "ERROR: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Success in creating bulk JIRA users"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                send_app_messages(admin, user, {"success": "Successful", "job": "Bulk creation of Jira users"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in bulk creation of Jira users"})
        finally:
            set_job_progress(100)


@bulk.route("/bulk_users_group_creation")
def bulk_users_group_creation(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            i = 0
            set_job_progress(0)
            if args[1] == "JIRA":
                count = len(args[0])
                for u in args[0]:
                    payload = (
                        {
                            "emailAddress": u[1],
                            "displayName": u[0]

                        }
                    )
                    data = LOGIN.post(endpoint.jira_user(), payload=payload)
                    i += 1
                    set_job_progress(100 * i // count)
                    if data.status_code < 300:
                        retrieve = data.json()
                        display_name = f"{user.username}".capitalize()
                        activity = "Success in creating bulk Jira users"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                        if "accountId" in retrieve:
                            account_id = retrieve.get('accountId')
                            group_names = u[2].split("~>")
                            for names in group_names:
                                payload = (
                                    {
                                        "accountId": account_id

                                    }
                                )
                                sub_data = LOGIN.post(endpoint.group_jira_users(group_name="{}".format(names)),
                                                      payload=payload)
                                if sub_data.status_code != 201:
                                    display_name = f"{user.username}".capitalize()
                                    activity = "Failure adding user {} to group {} in bulk".format(u[0], names)
                                    audit_log = "ERROR: {}".format(sub_data.status_code)
                                    auto_commit_jobs(display_name, activity, audit_log, user)
                                else:
                                    display_name = f"{user.username}".capitalize()
                                    activity = "Bulk addition of user {} to group {} successful".format(u[0], names)
                                    audit_log = "SUCCESS: {}".format(sub_data.status_code)
                                    auto_commit_jobs(display_name, activity, audit_log, user)
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure in creating bulk Jira user {}".format(u[0])
                        audit_log = "ERROR: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                send_app_messages(admin, user,
                                  {"success": "Successful", "job": "Bulk creation of Jira users and groups"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in bulk creation of Jira "
                                                                      "users and group"})
        finally:
            set_job_progress(100)


@bulk.route("/delete_users", methods=["GET", "POST"])
@login_required
@validate_account
def delete_users():
    form = DeleteUserForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        data = LOGIN.delete(endpoint.jira_user(account_id="{}".format(form.aaid.data)))
        if data.status_code != 204:
            error = "Unable to delete user as we encountered a blocker."
            display_name = f"{current_user.username}".capitalize()
            activity = "Failure in deleting user"
            audit_log = "ERROR: {}".format(data.status_code)
            auto_commit(display_name, activity, audit_log)
            flash(error)
        else:
            success = "User deletion has been completed."
            display_name = f"{current_user.username}".capitalize()
            activity = "Successfully deleted user"
            audit_log = "SUCCESS: {}".format(data.status_code)
            auto_commit(display_name, activity, audit_log)
            flash(success)
    return render_template("pages/delete.html", title=f"Delete User :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/delete_users/bulk_delete", methods=["GET", "POST"])
@login_required
@validate_account
def bulk_delete():
    form = UploadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    create_dir(our_dir, save_path)
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect. Please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_users_deletion"):
            error = "A bulk user deletion job is in progress, please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |id | displayName |
                loop_count = [u for u in reader]
                another_read = deepcopy(loop_count)
                width = [len(k) for k in another_read if k]  # get the number of columns
                number_of_loop = len(loop_count)
                if width[0] < 2:
                    error = "Please check the format for the required file upload, incorrect column detected."
                    flash(error)
                elif width[0] > 2:
                    error = "Your column length is not expected, please check the required format by clicking" \
                            " the \"Need help\" button above."
                    flash(error)
                elif width[0] == 2:
                    if 1 < number_of_loop < 10:
                        for u in loop_count:
                            data = LOGIN.delete(endpoint.jira_user(account_id="{}".format(u[0])))
                        if data.status_code != 204:
                            error = "Unable to  delete multiple users, check the audit log for the cause."
                            display_name = f"{current_user.username}".capitalize()
                            activity = "Failure in bulk user deletion of {}".format(u[1])
                            audit_log = "ERROR: {}".format(data.status_code)
                            auto_commit(display_name, activity, audit_log)
                            os.remove(o)
                            flash(error)
                        else:
                            success = "Multiple user deletion completed."
                            display_name = f"{current_user.username}".capitalize()
                            activity = "Executed successfully, bulk user deletion."
                            audit_log = "SUCCESS: {}".format(data.status_code)
                            auto_commit(display_name, activity, audit_log)
                            os.remove(o)
                            flash(success)
                    elif number_of_loop > 10:
                        current_user.launch_jobs("bulk_users_deletion", "Bulk deletion of users", loop_count)
                        success = "A Job has been submitted for bulk user deletion"
                        db.session.commit()
                        os.remove(o)
                        flash(success)
    return render_template("users/sub_pages/_delete_user.html",
                           title=f"Bulk User Deletion :: {bulk.config['APP_NAME_SINGLE']}", error=error,
                           success=success, form=form, Messages=Messages)


@bulk.route("/bulk_users_deletion")
def bulk_users_deletion(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for u in args[0]:
                data = LOGIN.delete(endpoint.jira_user(account_id="{}".format(u[0])))
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 204:
                    display_name = f"{user.username}".capitalize()
                    activity = "Failure in bulk user deletion of {}".format(u[1])
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Executed successfully, bulk user deletion"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user, {"success": "Successful", "job": "Bulk user deletion"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in bulk user deletion"})
        finally:
            set_job_progress(100)


@bulk.route("/create_groups", methods=["GET", "POST"])
@login_required
@validate_account
def create_groups():
    form = CreateGroupForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect. please check it out"
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        # an abritary statement to ensure our with statement works
        s_file = "sometext.txt"
        s_path = os.path.join(our_dir, s_file)
        sa_path = open(s_path, "w+")
        sa_path.close()
        k = form.group.data.split(",")
        p = len(k)
        if p == 1:
            payload = (
                {
                    "name": form.group.data

                }
            )
            data = LOGIN.post(endpoint.jira_group(), payload=payload)
            if data.status_code != 201:
                error = "Cannot Create Group \"{}\", failure encountered".format(form.group.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Failure in creating user group"
                audit_log = "ERROR: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(error)
            else:
                success = "Group \"{}\" created successfully.".format(form.group.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Successfully created user group"
                audit_log = "SUCCESS: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(success)
        elif 1 < p < 10:
            with open(s_path, "r") as _opr:
                for uc in k:
                    payload = (
                        {
                            "name": uc

                        }
                    )
                    data = LOGIN.post(endpoint.jira_group(), payload=payload)
                if data.status_code != 201:
                    error = "Cannot create multiple groups, check the audit log for more detail."
                    display_name = f"{current_user.username}".capitalize()
                    activity = "Failure in creating groups {} in bulk".format(uc)
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(error)
                else:
                    success = "Multiple groups created successfully."
                    display_name = f"{current_user.username}".capitalize()
                    activity = "Bulk group creation successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(success)
        elif p > 10:
            if current_user.get_job_in_progress("bulk_create_groups"):
                error = "A Bulk group creation job is in progress, please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_create_groups", "Bulk creation of groups", k)
                success = "A Job has been submitted for bulk creation of groups, please check the " \
                          "Audit log for a completion message..."
                db.session.commit()
                flash(success)
    return render_template("/pages/create_grp.html", title=f"Create Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/bulk_create_groups")
def bulk_create_groups(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for uc in args[0]:
                payload = (
                    {
                        "name": uc

                    }
                )
                data = LOGIN.post(endpoint.jira_group(), payload=payload)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 201:
                    display_name = f"{user.username}".capitalize()
                    activity = "Failure in creating groups {} in bulk".format(uc)
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Bulk group creation successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user, {"success": "Successful", "job": "Bulk group creation"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in bulk group creation"})
        finally:
            set_job_progress(100)


@bulk.route("/delete_groups", methods=["GET", "POST"])
@login_required
@validate_account
def delete_groups():
    form = DeleteGroupForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        # an abritary expression to ensure our with statement works
        s_file = "sometext.txt"
        s_path = os.path.join(our_dir, s_file)
        sa_path = open(s_path, "w+")
        sa_path.close()
        k = form.delete_gp.data.split(",")
        p = len(k)
        if p == 1:
            data = LOGIN.delete(endpoint.jira_group(group_name="{}".format(form.delete_gp.data)))
            if data.status_code != 200:
                error = "Removing group \"{}\" failed, check the audit log for more detail".format(form.delete_gp.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Failure in deleting group"
                audit_log = "ERROR: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(error)
            else:
                success = "Group \"{}\" removed successfully".format(form.delete_gp.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Group deleted successfully"
                audit_log = "SUCCESS: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(success)
        elif 1 < p < 10:
            with open(s_path, "r") as _opr:
                for uc in k:
                    data = LOGIN.delete(endpoint.jira_group(group_name="{}".format(uc)))
                if data.status_code != 200:
                    error = "Removing multiple groups failed, please check the log to know why."
                    display_name = f"{current_user.username}".capitalize()
                    activity = "Failure in deleting multiple groups {}".format(uc)
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(error)
                else:
                    success = "Multiple group removal successful."
                    display_name = f"{current_user.username}".capitalize()
                    activity = "Multiple groups deletion successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(success)
        elif p > 10:
            if current_user.get_job_in_progress("bulk_delete_groups"):
                error = "A bulk group deletion job is in progress, please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_delete_groups", "Bulk deletion of groups", k)
                success = "A job has been submitted for bulk deletion of groups, please check the " \
                          "audit log for a completion message..."
                db.session.commit()
                flash(success)
    return render_template("/pages/delete_grp.html", title=f"Remove Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/bulk_delete_groups")
def bulk_delete_groups(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for uc in args[0]:
                data = LOGIN.delete(endpoint.jira_group(group_name="{}".format(uc)))
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 200:
                    display_name = f"{user.username}".capitalize()
                    activity = "Failure in deleting multiple groups {}".format(uc)
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Multiple groups deletion successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user, form={"success": "Successful", "job": "Bulk deletion of groups"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, form={"error": f"{e}", "job": "Failure in bulk deletion of groups"})
        finally:
            set_job_progress(100)


@bulk.route("/create_org", methods=["GET", "POST"])
@login_required
@validate_account
def create_org():
    form = OrgForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        # an abritary statement to ensure our with statement works
        s_file = "sometext.txt"
        s_path = os.path.join(our_dir, s_file)
        sa_path = open(s_path, "w+")
        sa_path.close()
        k = form.org_field.data.split(",")
        org = len(k)
        if org == 1:
            payload = {"name": form.org_field.data}
            data = LOGIN.post(endpoint.create_organization(), payload=payload)
            if data.status_code != 201:
                error = "Cannot create organization \"{}\", failure encountered".format(form.org_field.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Failure in creating organization"
                audit_log = "ERROR: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(error)
            else:
                success = "Organization \"{}\" created successfully.".format(form.org_field.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Successfully created user group"
                audit_log = "SUCCESS: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(success)
        elif 1 < org < 7:
            with open(s_path, "r") as _opr:
                for uc in k:
                    payload = {"name": uc}
                    data = LOGIN.post(endpoint.create_organization(), payload=payload)
                if data.status_code != 201:
                    error = "Cannot create multiple organizations, check the audit log for more detail."
                    display_name = f"{current_user.username}".capitalize()
                    activity = "Failure in creating organization {} in bulk".format(uc)
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(error)
                else:
                    success = "Multiple organization created successfully."
                    display_name = f"{current_user.username}".capitalize()
                    activity = "Bulk organization creation successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(success)
        elif org > 7:
            if current_user.get_job_in_progress("bulk_create_organizations"):
                error = "A Bulk organization creation job is in progress, please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_create_organizations", "Bulk creation of JSM organizations", k)
                success = "A Job has been submitted for bulk creation of organizations, please check the " \
                          "audit log for a completion message..."
                db.session.commit()
                flash(success)
    return render_template("/pages/jsm/create_org.html",
                           title=f"Create Organization :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/bulk_create_organizations")
def bulk_create_organizations(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for org in args[0]:
                payload = {"name": org}
                data = LOGIN.post(endpoint.create_organization(), payload=payload)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 201:
                    display_name = f"{user.username}".capitalize()
                    activity = "Failure in creating JSM organizations {} in bulk".format(org)
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Bulk JSM organization creation successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user, {"success": "Successful", "job": "Bulk JSM organization creation"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in bulk JSM organization creation"})
        finally:
            set_job_progress(100)


@bulk.route("/delete_org", methods=["GET", "POST"])
@login_required
@validate_account
def delete_org():
    form = OrgForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        k = form.org_field.data.split(",")
        org = len(k)
        if org > 0:
            if current_user.get_job_in_progress("bulk_delete_organizations"):
                error = "A Bulk JSM deletion of organizations job is in progress, please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_delete_organizations", "Bulk deletion of JSM organizations", k)
                success = "A Job has been submitted for bulk deletion of JSM organizations, please check the " \
                          "audit log for a completion message."
                db.session.commit()
                flash(success)
    return render_template("/pages/jsm/delete_org.html",
                           title=f"Delete Organization :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/bulk_delete_organizations")
def bulk_delete_organizations(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            set_job_progress(0)
            i = 0
            name_of_org = args[0]
            org_collection = deque()
            get_org = filter_jsm(LOGIN.get(endpoint.get_organizations(0, 100)).json(), org_collection)
            org_collection.clear()
            count = len(name_of_org)
            for names in name_of_org:
                for org_id in get_org:
                    if names == org_id.get("name"):
                        data = LOGIN.delete(endpoint.delete_organization(org_id.get('id')))
                        i += 1
                        set_job_progress(100 * i // count)
                        if data.status_code != 204:
                            display_name = f"{user.username}".capitalize()
                            activity = "Failure in deleting JSM organizations {} in bulk".format(org_id.get('name'))
                            audit_log = "ERROR: {}".format(data.status_code)
                            auto_commit_jobs(display_name, activity, audit_log, user)
                        else:
                            display_name = f"{user.username}".capitalize()
                            activity = "Bulk JSM deletion of organization successful"
                            audit_log = "SUCCESS: {}".format(data.status_code)
                            auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user, {"success": "Successful", "job": "Bulk JSM organization deletion"})
        except Exception as e:
            bulk.logger.error('Exception occurred', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in bulk JSM organization deletion"})
        finally:
            set_job_progress(100)


@bulk.route("/add_customer", methods=["GET", "POST"])
@login_required
@validate_account
def add_customer():
    form = UploadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    create_dir(our_dir, save_path)
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        form_selection = form.upload_opt.data
        if current_user.get_job_in_progress("bulk_add_customer"):
            error = "A bulk addition of customers job is in progress, please wait until it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |account_id | name_of_user|organization name|
                loop_count = [u for u in reader]
                another_read = deepcopy(loop_count)
                width = [len(k) for k in another_read if k]  # get the number of columns
                number_of_loops = len(loop_count)
                if width[0] > 3:
                    error = "Expecting a CSV file with max 3 columns not more."
                    flash(error)
                elif width[0] < 2:
                    error = "Invalid number of columns received, please click the \"Need help\" " \
                            "button to see the expected format."
                    flash(error)
                elif width[0] == 3:
                    # Format for single addition |account_id|name|org1|
                    # Format for addition to multiple orgs are |account_id|name|org1~>org2~>org3|
                    # Format for addition to multiple projects are |account_id |name |ABC~>ITSM~>SD|
                    if number_of_loops > 0:
                        current_user.launch_jobs("bulk_add_customer", "Bulk addition of customers", loop_count,
                                                 form_selection)
                        success = "A Job has been submitted for bulk addition of customers, " \
                                  "please check the audit log page for the updated result."
                        db.session.commit()
                        os.remove(o)
                        flash(success)
    return render_template("pages/jsm/add_customers.html",
                           title=f"Bulk addition of customer :: {bulk.config['APP_NAME_SINGLE']}", error=error,
                           success=success, form=form, Messages=Messages)


@bulk.route("/bulk_add_customer")
def bulk_add_customer(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        data_dog = namedtuple("data_dog", ["accountId", "name", "org_data"])
        try:
            set_job_progress(0)
            i = 0
            id_of_request = args[0]
            form_select = args[1]

            def process_bulk_customer() -> t.NoReturn:
                """Processes the context between adding customers to project or organizations."""
                nonlocal i
                attr = getattr(endpoint, "get_service_desks" if form_select == "JSM_PROJ" else "get_organizations")
                list_of_col = deque()
                get_org = filter_jsm(LOGIN.get(attr(0, 100)).json(), list_of_col,
                                     types=True if form_select == "JSM_ORG" else False)
                list_of_col.clear()
                count = len(id_of_request)
                name_list = {}
                for customer in id_of_request:
                    row_list = data_dog._make(customer)
                    column = row_list.org_data.split("~>")
                    for rows in column:
                        for ids in get_org:
                            if rows == ids.get("name" if form_select == "JSM_ORG" else "project_key"):
                                name_list.update({
                                    str(ids.get("id")): []
                                })

                for _customer in id_of_request:
                    _row_list = data_dog._make(_customer)
                    _column = _row_list.org_data.split("~>")
                    for rows in _column:
                        for _ids in get_org:
                            if rows == _ids.get("name" if form_select == "JSM_ORG" else "project_key"):
                                if _row_list.accountId not in name_list.get(str(_ids.get("id"))):
                                    name_list.get(str(_ids.get("id"))).append(_row_list.accountId)

                # At this point, account_id is suppose to be a list of users in the item.
                for attr_id, account_id in name_list.items():
                    payload = {"accountIds": account_id}
                    attr_post = getattr(endpoint, "add_customers" if form_select == "JSM_PROJ"
                    else "add_users_to_organization")
                    data = LOGIN.post(attr_post(attr_id), payload=payload)
                    i += 1
                    set_job_progress(100 * i // count)
                    if data.status_code < 300:
                        display_name = f"{user.username}".capitalize()
                        activity = "Success in adding customers to JSM project in bulk" if form_select == "JSM_PROJ" \
                            else "Success in adding customers to JSM organizations in bulk"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure in addition of customers to JSM project" if form_select == "JSM_PROJ" \
                            else "Failure in addition of customers to JSM organization"
                        audit_log = "ERROR: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                send_app_messages(admin, user, {"success": "Successful", "job": "Bulk addition of customers to "
                                                                                "JSM projects"
                if form_select == "JSM_PROJ" else "Bulk addition of customers to JSM organization"})

            if form_select == "JSM_PROJ":
                process_bulk_customer()

            elif form_select == "JSM_ORG":
                process_bulk_customer()
        except Exception as e:
            bulk.logger.error('Exception occurred', exc_info=sys.exc_info())
            send_error_messages(admin,
                                user,
                                {"error": f"{e}", "job": "Failure in bulk addition of customers to JSM organization."
                                if form_select == "JSM_ORG" else "Failure in bulk addition of customers to JSM project."
                                 })
        finally:
            set_job_progress(100)


@bulk.route("/remove_customer", methods=["GET", "POST"])
@login_required
@validate_account
def remove_customer():
    form = UploadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    create_dir(our_dir, save_path)
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        form_selection = form.upload_opt.data
        if current_user.get_job_in_progress("bulk_remove_customer"):
            error = "A bulk removal of customers job is in progress, please wait until it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |account_id | name_of_user|organization name|
                loop_count = [u for u in reader]
                another_read = deepcopy(loop_count)
                width = [len(k) for k in another_read if k]  # get the number of columns
                number_of_loops = len(loop_count)
                if width[0] > 3:
                    error = "Expecting a CSV file with max 3 columns not more."
                    flash(error)
                elif width[0] < 2:
                    error = "Invalid number of columns received, please click the \"Need help\" " \
                            "button to see the expected format."
                    flash(error)
                elif width[0] == 3:
                    # Format for single removal |account_id|name|org1|
                    # Format for removal of multiple orgs are |account_id|name|org1~>org2~>org3|
                    # Format for removal of multiple projects are |account_id |name |ABC~>ITSM~>SD|
                    if number_of_loops > 0:
                        current_user.launch_jobs("bulk_remove_customer", "Bulk removal of customers", loop_count,
                                                 form_selection)
                        success = "A Job has been submitted for bulk removal of JSM customers, " \
                                  "please check the audit log page for the updated result."
                        db.session.commit()
                        os.remove(o)
                        flash(success)
    return render_template("pages/jsm/remove_customers.html",
                           title=f"Bulk removal of customer :: {bulk.config['APP_NAME_SINGLE']}", error=error,
                           success=success, form=form, Messages=Messages)


@bulk.route("/bulk_remove_customer")
def bulk_remove_customer(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        data_dog = namedtuple("data_dog", ["accountId", "name", "org_data"])
        try:
            set_job_progress(0)
            i = 0
            request_id = args[0]
            select_form = args[1]

            def remove_bulk_customer() -> t.NoReturn:
                """This function processes the context of removing customers from project or organizations."""
                nonlocal i
                rem_attr = getattr(endpoint, "get_service_desks" if select_form == "JSM_PROJ" else "get_organizations")
                cols = deque()
                fetch_org = filter_jsm(LOGIN.get(rem_attr(0, 100)).json(), cols,
                                       types=True if select_form == "JSM_ORG" else False)
                cols.clear()
                count = len(request_id)
                data_list = {}
                for customer in request_id:
                    row_cell = data_dog._make(customer)
                    column_cell = row_cell.org_data.split("~>")
                    for rows in column_cell:
                        for ids in fetch_org:
                            if rows == ids.get("name" if select_form == "JSM_ORG" else "project_key"):
                                data_list.update({
                                    str(ids.get("id")): []
                                })

                for _customer in request_id:
                    _row_cell = data_dog._make(_customer)
                    _column_cell = _row_cell.org_data.split("~>")
                    for rows in _column_cell:
                        for _ids in fetch_org:
                            if rows == _ids.get("name" if select_form == "JSM_ORG" else "project_key"):
                                if _row_cell.accountId not in data_list.get(str(_ids.get("id"))):
                                    data_list.get(str(_ids.get("id"))).append(_row_cell.accountId)

                # At this point, account_id is suppose to be a list of users in the item.
                for attr_id, account_id in data_list.items():
                    payload = {"accountIds": account_id}
                    attr_delete = getattr(endpoint, "remove_customers" if select_form == "JSM_PROJ"
                    else "remove_users_from_organization")
                    data = LOGIN.delete(attr_delete(attr_id), json=payload)
                    i += 1
                    set_job_progress(100 * i // count)
                    if data.status_code < 300:
                        display_name = f"{user.username}".capitalize()
                        activity = "Success in removal of customers from JSM project in bulk" \
                            if select_form == "JSM_PROJ" else "Success in removal of customers from " \
                                                              "JSM organizations in bulk"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure in removal of customers from JSM project" if select_form == "JSM_PROJ" \
                            else "Failure in removal of customers from JSM organization"
                        audit_log = "ERROR: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                send_app_messages(admin, user, {"success": "Successful", "job": "Bulk removal of customers from "
                                                                                "JSM projects"
                if select_form == "JSM_PROJ" else "Bulk removal of customers from JSM organization"})

            if select_form == "JSM_PROJ":
                remove_bulk_customer()

            elif select_form == "JSM_ORG":
                remove_bulk_customer()
        except Exception as e:
            bulk.logger.error('Exception occurred', exc_info=sys.exc_info())
            send_error_messages(admin,
                                user,
                                {"error": f"{e}", "job": "Failure in bulk removal of customers from JSM organization."
                                if select_form == "JSM_ORG" else "Failure in bulk removal of customers from "
                                                                 "JSM project."})
        finally:
            set_job_progress(100)


@bulk.route("/add_org", methods=["GET", "POST"])
@login_required
@validate_account
def add_org():
    form = UploadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    create_dir(our_dir, save_path)
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_add_org"):
            error = "A bulk addition of organizations to a project job is in progress, please wait until it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |organization name| project key|
                loop_count = [u for u in reader]
                another_read = deepcopy(loop_count)
                width = [len(k) for k in another_read if k]  # get the number of columns
                number_of_loops = len(loop_count)
                if width[0] > 2:
                    error = "Expecting a CSV file with max 2 columns not more."
                    flash(error)
                elif width[0] < 2:
                    error = "Invalid number of columns received, please click the \"Need help\" " \
                            "button to see the expected format."
                    flash(error)
                elif width[0] == 2:
                    # Format for single addition |org name|ABC|
                    # Format for addition of multiple orgs are |org name|ABC~>ITSM~>SD|
                    if number_of_loops > 0:
                        current_user.launch_jobs("bulk_add_org", "Bulk addition of organization to projects",
                                                 loop_count)
                        success = "A Job has been submitted for bulk addition of organization to a project, " \
                                  "please check the audit log page for the updated result."
                        db.session.commit()
                        os.remove(o)
                        flash(success)
    return render_template("pages/jsm/add_org.html",
                           title=f"Bulk addition of organizations to projects :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


@bulk.route("/bulk_add_org")
def bulk_add_org(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        data_dog = namedtuple("data_dog", ["name", "project_data"])
        try:
            set_job_progress(0)
            i = 0
            add_org_project = args[0]
            list_of_col = deque()
            org_collection = deque()
            get_sd = filter_jsm(LOGIN.get(endpoint.get_service_desks(0, 100)).json(), list_of_col, types=False)
            get_orgs = filter_jsm(LOGIN.get(endpoint.get_organizations(0, 100)).json(), org_collection)
            count = len(add_org_project)
            list_of_col.clear()
            org_collection.clear()
            for orgs in add_org_project:
                row_data = data_dog._make(orgs)
                columns = row_data.project_data.split("~>")
                for rows in columns:
                    for ids in get_orgs:
                        for desk in get_sd:
                            if rows == desk.get("project_key") and row_data.name == ids.get("name"):
                                payload = {"organizationId": ids.get("id")}
                                data = LOGIN.post(endpoint.add_sd_organization(desk.get("id")), payload=payload)
                                i += 1
                                set_job_progress(100 * i // count)
                                if data.status_code < 300:
                                    display_name = f"{user.username}".capitalize()
                                    activity = "Success in adding organization to JSM project in bulk"
                                    audit_log = "SUCCESS: {}".format(data.status_code)
                                    auto_commit_jobs(display_name, activity, audit_log, user)
                                else:
                                    display_name = f"{user.username}".capitalize()
                                    activity = "Failure in adding organization to JSM project"
                                    audit_log = "ERROR: {}".format(data.status_code)
                                    auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user,
                              {"success": "Successful", "job": "Bulk addition of organization to JSM projects"})
        except Exception as e:
            bulk.logger.error('Exception occurred', exc_info=sys.exc_info())
            send_error_messages(admin,
                                user, {"error": f"{e}",
                                       "job": "Failure in bulk addition of organization to JSM projects."})
        finally:
            set_job_progress(100)


@bulk.route("/remove_org", methods=["GET", "POST"])
@login_required
@validate_account
def remove_org():
    form = UploadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    create_dir(our_dir, save_path)
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_remove_org"):
            error = "A bulk removal of organizations from a project job is in progress, " \
                    "please wait until it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |organization name| project key|
                loop_count = [u for u in reader]
                another_read = deepcopy(loop_count)
                width = [len(k) for k in another_read if k]  # get the number of columns
                number_of_loops = len(loop_count)
                if width[0] > 2:
                    error = "Expecting a CSV file with max 2 columns not more."
                    flash(error)
                elif width[0] < 2:
                    error = "Invalid number of columns received, please click the \"Need help\" " \
                            "button to see the expected format."
                    flash(error)
                elif width[0] == 2:
                    # Format for single removal |org name|ABC|
                    # Format for removal of multiple orgs are |org name|ABC~>ITSM~>SD|
                    if number_of_loops > 0:
                        current_user.launch_jobs("bulk_remove_org", "Bulk removal of organization from projects",
                                                 loop_count)
                        success = "A Job has been submitted for bulk removal of organization from a project, " \
                                  "please check the audit log page for the updated result."
                        db.session.commit()
                        os.remove(o)
                        flash(success)
    return render_template("pages/jsm/remove_org.html",
                           title=f"Bulk removal of organizations from projects :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


@bulk.route("/bulk_remove_org")
def bulk_remove_org(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        data_dog = namedtuple("data_dog", ["name", "project_data"])
        try:
            set_job_progress(0)
            i = 0
            add_org_project = args[0]
            list_of_col = deque()
            org_collection = deque()
            get_sd = filter_jsm(LOGIN.get(endpoint.get_service_desks(0, 100)).json(), list_of_col, types=False)
            get_orgs = filter_jsm(LOGIN.get(endpoint.get_organizations(0, 100)).json(), org_collection)
            count = len(add_org_project)
            list_of_col.clear()
            org_collection.clear()
            for orgs in add_org_project:
                row_data = data_dog._make(orgs)
                columns = row_data.project_data.split("~>")
                for rows in columns:
                    for ids in get_orgs:
                        for desk in get_sd:
                            if rows == desk.get("project_key") and row_data.name == ids.get("name"):
                                payload = {"organizationId": ids.get("id")}
                                data = LOGIN.delete(endpoint.add_sd_organization(desk.get("id")), json=payload)
                                i += 1
                                set_job_progress(100 * i // count)
                                if data.status_code < 300:
                                    display_name = f"{user.username}".capitalize()
                                    activity = "Success in removing organization from JSM project in bulk"
                                    audit_log = "SUCCESS: {}".format(data.status_code)
                                    auto_commit_jobs(display_name, activity, audit_log, user)
                                else:
                                    display_name = f"{user.username}".capitalize()
                                    activity = "Failure in removing organization from JSM project"
                                    audit_log = "ERROR: {}".format(data.status_code)
                                    auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user,
                              {"success": "Successful", "job": "Bulk removal of organization from JSM projects"})
        except Exception as e:
            bulk.logger.error('Exception occurred', exc_info=sys.exc_info())
            send_error_messages(admin,
                                user, {"error": f"{e}",
                                       "job": "Failure in bulk removal of organization from JSM projects."})
        finally:
            set_job_progress(100)


@bulk.route("/add_groups", methods=["GET", "POST"])
@login_required
@validate_account
def add_groups():
    form = AddUserGroupForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        payload = (
            {
                "accountId": form.aaid.data

            }
        )
        data = LOGIN.post(endpoint.group_jira_users(group_name="{}".format(form.group_name.data)), payload=payload)
        if data.status_code != 201:
            error = "Unable to add user, it seems there's a problem."
            display_name = f"{current_user.username}".capitalize()
            activity = "Failure in adding user to group"
            audit_log = "ERROR: {}".format(data.status_code)
            auto_commit(display_name, activity, audit_log)
            flash(error)
        else:
            success = "User added to group successfully."
            display_name = f"{current_user.username}".capitalize()
            activity = "Added user successfully to group"
            audit_log = "SUCCESS: {}".format(data.status_code)
            auto_commit(display_name, activity, audit_log)
            flash(success)
    return render_template("/pages/add_grp.html", title=f"Add User to Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/add_groups/bulk_add", methods=["GET", "POST"])
@login_required
@validate_account
def bulk_add():
    form = UploadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    create_dir(our_dir, save_path)
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        # saving the file literally to the path as it is named including <space> characters
        filename = secure_filename(str(f.filename))
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_add_users"):
            error = "A bulk addition of users to group job is in progress, please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |groupName |id | displayName |
                loop_count = [u for u in reader]
                another_read = deepcopy(loop_count)
                width = [len(k) for k in another_read if k]  # get the number of columns
                number_of_loop = len(loop_count)
                if width[0] > 3:
                    error = "Your column should not be greater than 3 max. Please recheck your file."
                    flash(error)
                elif width[0] < 3:
                    error = "Your column length is not expected. Did you check the required file format and how many" \
                            " columns are needed?"
                    flash(error)
                elif width[0] == 3:
                    if number_of_loop > 1:
                        current_user.launch_jobs("bulk_add_users", "Bulk add users to groups", loop_count)
                        success = "A Job has been submitted for bulk addition of users to groups, please check the " \
                                  "audit log for a completion message..."
                        db.session.commit()
                        os.remove(o)
                        flash(success)
                    else:
                        error = "Unable to run task, you must at least submit more than 1 entity of data."
                        flash(error)
                        os.remove(o)
    return render_template("pages/sub_pages/_add_group.html",
                           title=f"Bulk Add Users to Groups :: {bulk.config['APP_NAME_SINGLE']}", error=error,
                           success=success, form=form, Messages=Messages)


@bulk.route("/bulk_add_users")
def bulk_add_users(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for u in args[0]:
                group_names = u[0].split("~>")
                for name in group_names:
                    payload = (
                        {
                            "accountId": u[1]

                        }
                    )
                    data = LOGIN.post(endpoint.group_jira_users(group_name="{}".format(name)), payload=payload)
                    if data.status_code != 201:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure adding users {} to groups {} in bulk".format(u[2], name)
                        audit_log = "ERROR: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Bulk addition of users to groups successful"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                i += 1
                set_job_progress(100 * i // count)
            send_app_messages(admin, user, {"success": "Successful", "job": "Bulk addition of users to groups"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in bulk addition of users to groups"})
        finally:
            set_job_progress(100)


@bulk.route("/remove_groups", methods=["GET", "POST"])
@login_required
@validate_account
def remove_groups():
    form = RemoveUserGroupForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        data = LOGIN.delete(endpoint.group_jira_users(group_name=form.group_name.data, account_id=form.aaid.data))
        if data.status_code != 200:
            error = "Unable to remove user from group, please check the log."
            display_name = f"{current_user.username}".capitalize()
            activity = "Failure in removing user from group"
            audit_log = "ERROR: {}".format(data.status_code)
            auto_commit(display_name, activity, audit_log)
            flash(error)
        else:
            success = "User removed from group successfully."
            display_name = f"{current_user.username}".capitalize()
            activity = "Successfully removed user from group"
            audit_log = "SUCCESS: {}".format(data.status_code)
            auto_commit(display_name, activity, audit_log)
            flash(success)
    return render_template("/pages/remove_grp.html",
                           title=f"Remove User from Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/remove_groups/bulk_remove", methods=["GET", "POST"])
@login_required
@validate_account
def bulk_remove():
    form = UploadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    create_dir(our_dir, save_path)
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out"
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        # saving the file literally to the path as it is named including <space> characters
        filename = secure_filename(str(f.filename))
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_remove_users"):
            error = "A bulk removal of users from group job is in progress, please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                loop_count = [u for u in reader]
                # Format for CSV is |groupName |id | displayName |
                another_read = deepcopy(loop_count)
                width = [len(k) for k in another_read if k]  # get the number of columns
                number_of_loop = len(loop_count)
                if width[0] > 3:
                    error = "Unexpected number of columns received. A maximum of 3 columns are required."
                    flash(error)
                elif width[0] < 3:
                    error = "Unexpected number of columns received. A minimum of 3 columns are required." \
                            " Please click the \"Need help\" button to see the format."
                    flash(error)
                elif width[0] == 3:
                    if number_of_loop > 1:
                        current_user.launch_jobs("bulk_remove_users", "Bulk remove users from groups", loop_count)
                        success = "A Job has been submitted for bulk removal of users from groups, please check the " \
                                  "audit log for a completion message."
                        db.session.commit()
                        os.remove(o)
                        flash(success)
                    else:
                        error = "Unable to run task, you must at least submit more than 1 entity of data."
                        flash(error)
                        os.remove(o)
    return render_template("pages/sub_pages/_remove_group.html",
                           title=f"Bulk Add Users to Groups :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


@bulk.route("/bulk_remove_users")
def bulk_remove_users(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for u in args[0]:
                group_names = u[0].split("~>")
                for name in group_names:
                    data = LOGIN.delete(endpoint.group_jira_users(group_name=name, account_id=u[1]))
                    if data.status_code != 200:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure removing multiple users {} from group {}".format(u[2], name)
                        audit_log = "ERROR: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Successfully removed multiple users from group"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                i += 1
                set_job_progress(100 * i // count)
            send_app_messages(admin, user, {"success": "Successful", "job": "Bulk removal of users from group"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in removing multiple users from group"})
        finally:
            set_job_progress(100)


@bulk.route("/projects", methods=["GET", "POST"])
@login_required
@validate_account
def projects():
    form = DeleteProjectForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect. Please check it out."
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        # an abritary statement to ensure our with statement works
        s_file = "sometext.txt"
        s_path = os.path.join(our_dir, s_file)
        sa_path = open(s_path, "w+")
        sa_path.close()
        f = form.project.data.split(",")
        p = len(f)
        if p == 1:
            data = LOGIN.delete(endpoint.projects(id_or_key=form.project.data, enable_undo=form.undo.data))
            if data.status_code != 204:
                error = "Cannot delete project {} seems an error occurred.".format(form.project.data)
                display_name = f"{current_user.username}".capitalize()
                activity = f"Failure in deleting Project, {form.project.data}"
                audit_log = "ERROR: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(error)
            else:
                success = "Project {} deleted successfully,".format(form.project.data)
                display_name = f"{current_user.username}".capitalize()
                activity = f"Successfully deleted project, {form.project.data}"
                audit_log = "SUCCESS: {}".format(data.status_code)
                auto_commit(display_name, activity, audit_log)
                flash(success)
        elif 1 < p < 3:
            with open(s_path, "r") as _opr:
                for z in f:
                    data = LOGIN.delete(endpoint.projects(id_or_key=z, enable_undo=form.undo.data))
                if data.status_code != 204:
                    error = "Cannot delete multiple projects {} because an error occurred.".format(form.project.data)
                    display_name = f"{current_user.username}".capitalize()
                    activity = f"Failure deleting these projects {z}"
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(error)
                else:
                    success = "Projects {} deleted completely.".format(form.project.data)
                    display_name = f"{current_user.username}".capitalize()
                    activity = f"Success in deleting off these projects {z}"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(success)
        elif p > 3:
            if current_user.get_job_in_progress("bulk_projects"):
                error = "A bulk deletion of project job is in progress, please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_projects", "Bulk project deletion", f, form.undo.data)
                success = "A job has been submitted for bulk deletion of projects, please check the " \
                          "audit log for a completion message..."
                db.session.commit()
                flash(success)
    return render_template("/pages/projects.html", title=f"Delete Projects :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


@bulk.route("/bulk_projects")
def bulk_projects(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        undo = args[1]
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for z in args[0]:
                data = LOGIN.delete(endpoint.projects(z, enable_undo=undo))
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 204:
                    display_name = f"{user.username}".capitalize()
                    activity = f"Failure deleting these projects {z}"
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = f"Success in deleting off these projects {z}"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user, {"success": "Successful", "job": "Projects deleted"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in deleting projects"})
        finally:
            set_job_progress(100)


@bulk.route("/delete_issue", methods=["GET", "POST"])
@login_required
@validate_account
def delete_issue():
    form = DeleteIssuesForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out"
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        q = form.issues.data.split(",")
        k = form.issues.data
        m = re.search("JQL:", k)
        p = len(q)
        r = k.strip("JQL:")
        start_at = 0
        max_results = 50
        sub_task = form.sub_task.data
        if p == 1:
            if m is not None:
                data = LOGIN.get(endpoint.search_issues_jql(query="{}".format(r), start_at=start_at,
                                                            max_results=max_results))
                if data.status_code != 200:
                    error = "Unable to fetch JQL issues due to {}".format(data.reason)
                    flash(error)
                else:
                    jql_data = json.loads(data.content)
                    total = jql_data["total"]
                    full_number = int(total / 1)
                    if str(jql_data["issues"]) == "[]":
                        error = "JQL: {} issues returned, please use another query." \
                            .format(total)
                        flash(error)
                    else:
                        if current_user.get_job_in_progress("bulk_schedule_delete"):
                            error = "A bulk deletion using JQL job is in progress, please wait till it's finished."
                            flash(error)
                        else:
                            current_user.launch_jobs("bulk_schedule_delete", "Bulk deletion with JQL", total, r,
                                                     start_at, max_results, full_number, sub_task)
                            success = "A job has been submitted for bulk deletion of issues using JQL, " \
                                      "please check the audit log for a completion message..."
                            flash(success)
                            db.session.commit()
            else:
                data = LOGIN.delete(endpoint.issues(issue_key_or_id=form.issues.data,
                                                    query="deleteSubtasks={}".format(sub_task)))
                if data.status_code != 204:
                    error = "Cannot delete issue {} something went wrong!".format(form.issues.data)
                    display_name = f"{current_user.username}".capitalize()
                    activity = f"Failure deleting single issue {form.issues.data}"
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(error)
                else:
                    success = "Issue {} deleted with success".format(form.issues.data)
                    display_name = f"{current_user.username}".capitalize()
                    activity = f"Deleted off single issue {form.issues.data}"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit(display_name, activity, audit_log)
                    flash(success)
        elif p > 1:
            if current_user.get_job_in_progress("bulk_delete_issues"):
                error = "A bulk deletion of issues job is in progress, please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_delete_issues", "Bulk issue deletion", q, sub_task)
                success = "A job has been submitted for bulk deletion of issues, please check the " \
                          "audit log for a completion message..."
                flash(success)
                db.session.commit()
    return render_template("/pages/delete_issue.html", title=f"Delete Issues :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/bulk_delete_issues")
def bulk_delete_issues(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        q = args[0]
        sub_task = args[1]
        try:
            set_job_progress(0)
            i = 0
            count = len(q)
            for z in q:
                data = LOGIN.delete(endpoint.issues(issue_key_or_id=z, query="deleteSubtasks={}".format(sub_task)))
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 204:
                    display_name = f"{user.username}".capitalize()
                    activity = "Multiple issue deletion failed"
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Multiple issue deletion successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user, {"success": "Successful", "job": "Deletion of multiple issues"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in deleting multiple issues"})
        finally:
            set_job_progress(100)


@bulk.route("/bulk_schedule_delete")
def bulk_schedule_delete(user_id, *args):
    issue_list = deque()
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        total = args[0]
        r = args[1]
        start_at = args[2]
        max_results = args[3]
        full_number = args[4]
        sub_task = args[5]
        try:
            set_job_progress(0)
            i = 0

            def schedule_delete():
                nonlocal start_at, i
                while max_results < total or max_results > total:
                    if start_at < full_number:
                        info = LOGIN.get(endpoint.search_issues_jql(query="{}".format(r), start_at=start_at,
                                                                    max_results=max_results))
                        wjson = json.loads(info.content)

                        for w in list(wjson["issues"]):
                            issue_list.append([w["key"]])
                        start_at += 50
                    if start_at > (full_number - 1):
                        break

                count = len(issue_list)
                for key in issue_list:
                    data = LOGIN.delete(endpoint.issues(issue_key_or_id=key[0],
                                                        query="deleteSubtasks={}".format(sub_task)))
                    i += 1
                    set_job_progress(100 * i // count)
                    if data.status_code != 204:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure in JQL, issue deletion returned error"
                        audit_log = "ERROR: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Multiple issues were deleted"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        auto_commit_jobs(display_name, activity, audit_log, user)

            schedule_delete()
            send_app_messages(admin, user, {"success": "Successful", "job": "Multiple issues deleted"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in multiple issue deletion"})
        finally:
            set_job_progress(100)


@bulk.route("/project_lead", methods=["GET", "POST"])
@login_required
@validate_account
def project_lead():
    form = ChangeProjectLeadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        payload = (
            {
                "leadAccountId": form.aaid.data,
                "assigneeType": form.assignee.data,
                "key": form.project.data,

            }
        )
        data = LOGIN.put(endpoint.projects(form.project.data), payload=payload)
        if data.status_code != 200:
            error = "Cannot change project lead project {} due to an error.".format(form.project.data)
            display_name = f"{current_user.username}".capitalize()
            activity = "Failed updating project lead"
            audit_log = "ERROR: {}".format(data.status_code)
            auto_commit(display_name, activity, audit_log)
            flash(error)
        else:
            success = "Project lead changed for project {} is completed.".format(form.project.data)
            display_name = f"{current_user.username}".capitalize()
            activity = "Project lead updated successfully"
            audit_log = "SUCCESS: {}".format(data.status_code)
            auto_commit(display_name, activity, audit_log)
            flash(success)
    return render_template("/pages/project_lead.html",
                           title=f"Change Project Lead :: {bulk.config['APP_NAME_SINGLE']}", form=form,
                           error=error, success=success, Messages=Messages)


@bulk.route("/project_lead/bulk_lead", methods=["GET", "POST"])
@login_required
@validate_account
def bulk_lead():
    form = UploadForm()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    create_dir(our_dir, save_path)
    if request.method == "GET":
        if check_token_valid().status_code != 200:
            error = "Your token seems to be incorrect, please check it out"
            flash(error)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        # saving the file literally to the path as it is named including <space> characters
        filename = secure_filename(str(f.filename))
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_project_lead"):
            error = "A bulk change of project lead job is in progress, please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |id | key | assignee_type |
                loop_count = [u for u in reader]
                another_read = deepcopy(loop_count)
                width = [len(k) for k in another_read if k]  # get the number of columns
                number_of_loop = len(loop_count)
                if width[0] > 3:
                    error = "Please check the required columns expected for this operation by clicking " \
                            "the \"Need help\" button above."
                    flash(error)
                elif width[0] < 3:
                    error = "A minimum of 3 columns are required in your uploaded file, please check again."
                    flash(error)
                elif width[0] == 3:
                    if 1 < number_of_loop < 10:
                        for u in loop_count:
                            payload = (
                                {
                                    "leadAccountId": u[0],
                                    "assigneeType": u[2],
                                    "key": u[1],

                                }
                            )
                            data = LOGIN.put(endpoint.projects(u[1]), payload=payload)
                        if data.status_code != 200:
                            error = "Cannot change multiple project lead project due to an error!"
                            display_name = f"{current_user.username}".capitalize()
                            activity = "Error, bulk changing project lead"
                            audit_log = "ERROR: {}".format(data.status_code)
                            auto_commit(display_name, activity, audit_log)
                            os.remove(o)
                            flash(error)
                        else:
                            success = "Multiple project lead change completed."
                            display_name = f"{current_user.username}".capitalize()
                            activity = "Bulk project lead change successful"
                            audit_log = "SUCCESS: {}".format(data.status_code)
                            auto_commit(display_name, activity, audit_log)
                            os.remove(o)
                            flash(success)
                    elif number_of_loop > 10:
                        current_user.launch_jobs("bulk_project_lead", "Bulk change project lead", loop_count)
                        success = "A Job has been submitted for bulk change of project leads. Please check the " \
                                  "audit log for a completion message..."
                        db.session.commit()
                        flash(success)
                        os.remove(o)
    return render_template("pages/sub_pages/_change_lead.html",
                           title=f"Bulk Add Users to Groups :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


@bulk.route("/bulk_project_lead")
def bulk_project_lead(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
        LOGIN(user=user.email, password=user.token, url="https://{}".format(user.instances))
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for u in args[0]:
                payload = (
                    {
                        "leadAccountId": u[0],
                        "assigneeType": u[2],
                        "key": u[1],

                    }
                )
                data = LOGIN.put(endpoint.projects(u[1]), payload=payload)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 200:
                    display_name = f"{user.username}".capitalize()
                    activity = "Error, bulk changing project lead"
                    audit_log = "ERROR: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Bulk project lead change successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    auto_commit_jobs(display_name, activity, audit_log, user)
            send_app_messages(admin, user, {"success": "Successful", "job": "Bulk project leads changed"})
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
            send_error_messages(admin, user, {"error": f"{e}", "job": "Failure in changing project leads"})
        finally:
            set_job_progress(100)


@bulk.route("/audit", methods=["GET", "POST"])
@login_required
@validate_account
def audit():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    page = request.args.get("page", 1, type=int)
    tasks = {
        "task": current_user.jobs.filter_by(completion=False).all(),
        "task_count": current_user.jobs.filter_by(completion=False).count()
    }
    logs = user.audit.order_by(Audit.timestamp.desc()).paginate(page, current_app.config["AUDIT_PER_PAGE"], False)
    next_url = url_for("audit", page=logs.next_num) if logs.has_next else None
    prev_url = url_for("audit", page=logs.prev_num) if logs.has_prev else None
    return render_template("/config/audit.html", title=f"Audit Log :: {bulk.config['APP_NAME_SINGLE']}",
                           logs=logs.items, next_url=next_url, prev_url=prev_url, Messages=Messages, tasks=tasks)


@bulk.route("/messages/inbox", methods=["GET", "POST"])
@login_required
@validate_account
def messages():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    form = MessageForm()
    error = None
    success = None
    page = request.args.get("page", 1, type=int)
    msg = user.received_messages.order_by(Messages.timestamp.desc()) \
        .paginate(page, current_app.config["MESSAGES_PER_PAGE"], False)
    next_url = url_for("messages", page=msg.next_num) if msg.has_next else None
    prev_url = url_for("messages", page=msg.prev_num) if msg.has_prev else None
    current_user.last_read_message = datetime.utcnow()
    current_user.add_notification("unread_msg_count", 0)
    db.session.commit()
    if request.method == "POST" and form.validate_on_submit():
        send = Messages(subject=form.subject.data, body=form.messages.data,
                        receiver_id=receiver(recipient=form.receiver.data), sender_id=user.id)
        user.add_notification("unread_msg_count", user.new_messages())
        db.session.add(send)
        db.session.commit()
        if form.receiver.data == bulk.config["APP_ADMIN_USERNAME"]:
            send_admin_message(admin, user, form)
        success = f"Your message has been sent to the {bulk.config['APP_NAME_SINGLE']} team"
        flash(success)
    return render_template("/pages/messages.html",
                           title=f"Messages - Preview Messages::{bulk.config['APP_NAME_SINGLE']}",
                           msg=msg.items, next_url=next_url, prev_url=prev_url, error=error,
                           success=success, form=form, Messages=Messages, admin=admin)


def receiver(recipient):
    admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    receive = User.query.filter_by(username=recipient).first()
    if receive.id is not None:
        return receive.id
    else:
        return admin.id


# view inbox messages
@bulk.route("/messages/inbox/<int:id>/view", methods=["GET", "POST"])
@login_required
@validate_account
def i_messages(id):
    form = MessageForm()
    error = None
    url_path = True
    success = None
    user = User.query.filter_by(username=current_user.username).first_or_404()
    admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    if request.method == "POST" and form.validate_on_submit():
        send = Messages(subject=form.subject.data, body=form.messages.data,
                        receiver_id=receiver(recipient=form.receiver.data), sender_id=user.id)
        user.add_notification("unread_msg_count", user.new_messages())
        db.session.add(send)
        db.session.commit()
        if form.receiver.data == bulk.config["APP_ADMIN_USERNAME"]:
            send_admin_message(admin, user, form)
        success = "Your message has been sent successfully"
        flash(success)
    return render_template("/pages/view_message.html",
                           title=f"Messages - View Inbox Messages ::{bulk.config['APP_NAME_SINGLE']}",
                           Messages=Messages, view=trigger_msg(id), form=form, error=error, success=success,
                           admin=admin, url_path=url_path)


def trigger_msg(id):
    view = Messages.query.get(id)
    # find all the messages received by the user, if not don't show it
    user = User.query.filter_by(username=current_user.username).first_or_404()
    c = user.received_messages.order_by(Messages.receiver_id.desc()).all()
    if view.id not in (m.id for m in c):
        return None
    else:
        return view


@bulk.route("/messages/sent", methods=["GET", "POST"])
@login_required
@validate_account
def sent_messages():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    form = MessageForm()
    error = None
    success = None
    page = request.args.get("page", 1, type=int)
    msg = user.sent_messages.order_by(Messages.timestamp.desc()) \
        .paginate(page, current_app.config["MESSAGES_PER_PAGE"], False)
    next_url = url_for("sent_messages", page=msg.next_num) if msg.has_next else None
    prev_url = url_for("sent_messages", page=msg.prev_num) if msg.has_prev else None
    if request.method == "POST" and form.validate_on_submit():
        send = Messages(subject=form.subject.data, body=form.messages.data, receiver_id=admin.id, sender_id=user.id)
        user.add_notification("unread_msg_count", user.new_messages())
        db.session.add(send)
        db.session.commit()
        if form.receiver.data == bulk.config["APP_ADMIN_USERNAME"]:
            send_admin_message(admin, user, form)
        success = f"Your message has been sent to the {bulk.config['APP_NAME_SINGLE']} team"
        flash(success)
    return render_template("/pages/send_message.html",
                           title=f"Messages - Send Messages::{bulk.config['APP_NAME_SINGLE']}",
                           msg=msg.items, next_url=next_url, prev_url=prev_url, success=success, error=error,
                           form=form, Messages=Messages, admin=admin)


# delete sent messages
@bulk.route("/messages/sent/<int:id>/delete", methods=["GET", "POST"])
@login_required
@validate_account
def delete_messages(id):
    msg = Messages.query.get(id)
    db.session.delete(msg)
    db.session.commit()
    flash("Your message has been deleted...")
    return redirect(url_for("sent_messages"))


# view sent messages
@bulk.route("/messages/sent/<int:id>/view", methods=["GET", "POST"])
@login_required
@validate_account
def s_messages(id):
    user = User.query.filter_by(username=current_user.username).first_or_404()
    admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    user.last_read_message = datetime.utcnow()
    db.session.commit()
    form = MessageForm()
    error = None
    success = None
    if request.method == "POST" and form.validate_on_submit():
        send = Messages(subject=form.subject.data, body=form.messages.data,
                        receiver_id=receiver(recipient=form.receiver.data), sender_id=user.id)
        user.add_notification("unread_msg_count", user.new_messages())
        db.session.add(send)
        db.session.commit()
        if form.receiver.data == bulk.config["APP_ADMIN_USERNAME"]:
            send_admin_message(admin, user, form)
        success = f"Your message has been sent to the {bulk.config['APP_NAME_SINGLE']} team"
        flash(success)
    return render_template("/pages/view_message.html",
                           title=f"Messages - View Sent Messages ::{bulk.config['APP_NAME_SINGLE']}",
                           Messages=Messages, view=trigger_rmsg(id), form=form, error=error, success=success,
                           admin=admin)


def trigger_rmsg(id):
    view = Messages.query.get(id)
    # find all the messages sent by the user if not don't show it
    user = User.query.filter_by(username=current_user.username).first_or_404()
    d = user.sent_messages.order_by(Messages.sender_id.desc()).all()
    if view.id not in (m.id for m in d):
        return None
    else:
        return view


@bulk.route("/messages/stats", methods=["GET", "POST"])
@login_required
@validate_account
def stats():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    form = MessageForm()
    error = None
    success = None
    r_msg = user.received_messages.order_by(Messages.timestamp.desc()).count()
    s_msg = user.sent_messages.order_by(Messages.timestamp.desc()).count()
    t_msg = user.received_messages.order_by(Messages.timestamp.desc()).limit(1).all()
    if request.method == "POST" and form.validate_on_submit():
        send = Messages(subject=form.subject.data, body=form.messages.data, receiver_id=admin.id, sender_id=user.id)
        db.session.add(send)
        db.session.commit()
        if form.receiver.data == bulk.config["APP_ADMIN_USERNAME"]:
            send_admin_message(admin, user, form)
        success = f"Your message has been sent to the {bulk.config['APP_NAME_SINGLE']} team"
        flash(success)
    return render_template("/pages/stats.html",
                           title=f"Messages - Stats ::{bulk.config['APP_NAME_SINGLE']}", r_msg=r_msg,
                           s_msg=s_msg, t_msg=t_msg, Messages=Messages, form=form, error=error,
                           success=success, admin=admin)


@bulk.route("/system/notifications", methods=["GET", "POST"])
@login_required
def notifications():
    when = request.args.get("when", 0.0, type=float)
    notification = current_user.notifications.filter(Notification.timestamp > when) \
        .order_by(Notification.timestamp.asc())
    return jsonify([{
        "name": n.name,
        "data": n.run_data(),
        "timestamp": n.timestamp
    } for n in notification])


@bulk.route("/auto_logout", methods=["GET", "POST"])
@login_required
def auto_logout():
    flash("You have been logged out due to inactivity for 10 minutes.", "success")
    return redirect(url_for("logout"), code=302)


@bulk.route("/settings/config", methods=["GET", "POST"])
@login_required
@validate_account
def config():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    error = None
    success = None
    data = None
    load_data = None
    form = TokenForm()
    r_msg = user.received_messages.order_by(Messages.timestamp.desc()).count()
    LOGIN(user=current_user.email, password=current_user.token, url="https://{}".format(current_user.instances))
    if request.method == "GET":
        form.token.data = current_user.token
        form.notify_me.data = current_user.notify_me
        data = LOGIN.get(endpoint.myself())
        if data.status_code == 200:
            load_data = json.loads(data.content)
    return render_template("/config/config.html",
                           title=f"Configuration - Check Stats ::{bulk.config['APP_NAME_SINGLE']}", r_msg=r_msg,
                           Messages=Messages, user=user, form=form, error=error, success=success,
                           data=data, load_data=load_data)


@bulk.route("/settings/delete", methods=["GET", "POST"])
@login_required
@validate_account
def account_delete():
    success = None
    error = None
    import glob
    user = User.query.filter_by(username=current_user.username).first_or_404()
    admin = User.query.filter_by(username=bulk.config["APP_ADMIN_USERNAME"]).first()
    date = datetime.now().strftime("%a, %d %b %Y - %I:%M %p")
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    files = glob.glob(f"{save_path}/*")
    if request.method == "POST":
        if os.path.exists(save_path):
            for f in files:
                os.remove(f)
            os.rmdir(save_path)
        db.session.delete(user)
        send_goodbye_message(user)
        time.sleep(0.5)
        send_user_exit(user, admin, date)
        db.session.commit()
        flash("You have been signed out")
        return redirect(url_for("logout"))
    return render_template("/config/account.html",
                           title=f"Configuration - Delete Account ::{bulk.config['APP_NAME_SINGLE']}",
                           Messages=Messages, error=error, success=success)


@bulk.route("/token", methods=["GET", "POST"])
@login_required
def tokens():
    form = TokenForm()
    if form.validate_on_submit():
        current_user.token = form.token.data
        db.session.commit()
        flash("Your API token has been saved!")
        return redirect(url_for("config"))


@bulk.route("/notify_me", methods=["GET", "POST"])
@login_required
def notify_me():
    form = TokenForm()
    if request.method == "POST":
        current_user.notify_me = form.notify_me.data
        db.session.commit()
        flash("Notifications setting changed.")
        return redirect(url_for("config"))


@bulk.route("/progress", methods=["GET", "POST"])
@login_required
def progress():
    def load():
        x = 0

        while x <= 100:
            yield "data:" + str(x) + "\n\n"
            x += 4
            time.sleep(0.3)

    return Response(load(), mimetype="text/event-stream")


def auto_commit(display_name, activity, audit_log):
    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
    db.session.add(ad)
    db.session.commit()


def auto_commit_jobs(display_name, activity, audit_log, user):
    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=user.id)
    db.session.add(ad)
    db.session.commit()


def check_token_valid():
    data = LOGIN.get(endpoint.myself())
    return data


def create_dir(direct, path):
    if not os.path.exists(direct):
        os.mkdir(direct)
    if not os.path.exists(path):
        os.mkdir(path)


@bulk.route("/audit/task/<task_id>", methods=["GET", "POST"])
@login_required
def clear_task(task_id):
    task = Jobs.query.get(task_id)
    if request.method == "POST":
        task.completion = True
        db.session.commit()
        flash("Cleared pending task!", "alert-success")
        return redirect(url_for('audit'))


def filter_jsm(maps: t.Mapping, queue: t.Deque, types: bool = True) -> t.List:
    """Search through the list of organization or projects and return a dict of id and name
     or id, projectId, project name and project key if projects.

    :param maps: The payload to query

    :param queue: A storage list of data

    :param types: A bool condition of the field name, True for orgs, false for project.

    :returns: A List of all organization names or project entity values and ids within the instance.
    """

    while True:
        next_page = maps.get("next") if "next" in maps and maps.get("isLastPage") is False else []
        for filter_name in maps.get("values"):
            filter_data = {
                "id": filter_name['id'],
                "name": filter_name['name']
            } if types is True else {
                "id": filter_name['id'],
                "project_id": filter_name['projectId'],
                "project_key": filter_name['projectKey'],
                "project_name": filter_name['projectName']
            }
            queue.append(filter_data)
        if isinstance(next_page, list):
            break
        _maps = LOGIN.get(next_page)
        if _maps.status_code < 300:
            maps = _maps.json()
    return [s for s in queue]
