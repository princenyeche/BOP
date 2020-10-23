import requests
import json
import os
import re
import csv
import sys
import time
from flask import render_template, flash, redirect, url_for, current_app
from bulkops.database import User, Audit, Messages, Notification
from flask_login import current_user
from flask import request, jsonify, Response
from flask_login import login_required
from bulkops import db
from bulkops.main.forms import SettingsForm, TokenForm, CreateGroupForm, \
    DeleteUserForm, CreateUsersForm, AddUserGroupForm, RemoveUserGroupForm, DeleteGroupForm, \
    ChangeProjectLeadForm, DeleteProjectForm, DeleteIssuesForm, UploadForm, MessageForm
from datetime import datetime
from requests.auth import HTTPBasicAuth
from werkzeug.utils import secure_filename
from bulkops import bulk
from bulkops.tasks.jobs import set_job_progress

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = "Files"
our_dir = os.path.join(basedir, UPLOAD_FOLDER)
file_limit = bulk.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

if not os.path.exists(our_dir):
    os.mkdir(our_dir)

auth_request = None
headers = None


class JiraUsers:

    @staticmethod
    def make_session(email=None, token=None):
        global auth_request
        global headers
        auth_request = HTTPBasicAuth(email, token)
        headers = {"Content-Type": "application/json"}

    @staticmethod
    def post(url, payload=None, *args):
        res = requests.post(url, json=payload, auth=auth_request, headers=headers)
        return res

    @staticmethod
    def get(url, *args):
        res = requests.get(url, auth=auth_request, headers=headers)
        return res

    @staticmethod
    def put(url, payload=None, *args):
        res = requests.put(url, json=payload, auth=auth_request, headers=headers)
        return res

    @staticmethod
    def delete(url, payload=None, *args):
        res = requests.delete(url, json=payload, auth=auth_request, headers=headers)
        return res


j = JiraUsers()


@bulk.route("/", methods=["GET", "POST"])
@bulk.route("/index", methods=["GET", "POST"])
@login_required
def index():
    data = None
    j.make_session(email=current_user.email, token=current_user.token)
    if request.method == "GET":
        web_url = ("https://{}/rest/api/3/myself".format(current_user.instances))
        data = j.get(web_url)
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
@login_required
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
        if y.startswith("http") or y.startswith("www"):
            error = "Please remove the \"http://\" or \"https://\" or \"www\" from the URL"
            flash(error)
        elif i < 8:
            error = "Your Password must be equal or greater than 8 Characters in length"
            flash(error)
        elif i > 64:
            error = "Your Password is too long, it must be within 64 Characters in length"
            flash(error)
        elif a is None:
            error = "You must use at least one of this Special Characters (!, @, #, $, %, &, or *) in your Password!"
            flash(error)
        elif y.endswith("atlassian.net") or y.endswith("jira-dev.com") \
                or y.endswith("jira.com"):
            user = User.query.filter_by(username=current_user.username).first()
            current_user.instances = form.instances.data
            user.set_password(form.password.data)
            display_name = f"{current_user.username}".capitalize()
            activity = f"Changes made to Settings From:{v}  To:{current_user.instances}"
            audit_log = f"CHANGES: Configuration"
            ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
            db.session.add(ad)
            db.session.add(user)
            db.session.commit()
            success = "Your changes have been saved."
            flash(success)
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
def users():
    form = CreateUsersForm()
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        if form.users_opt.data == "JIRA":
            web_url = ("https://{}/rest/api/3/user".format(current_user.instances))
            payload = (
                {
                    "emailAddress": form.users_email.data,
                    "displayName": form.users_name.data

                }
            )
            data = j.post(web_url, payload=payload)
            if data.status_code != 201:
                error = "Unable to Create user, probably due to an error"
                display_name = f"{current_user.username}".capitalize()
                activity = "Failure creating JIRA User"
                audit_log = "ERROR: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "User Created Successfully, Please check your Admin hub to confirm."
                display_name = f"{current_user.username}".capitalize()
                activity = "Created JIRA User successfully"
                audit_log = "SUCCESS: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(success)
        elif form.users_opt.data == "JSD":
            web_url = ("https://{}/rest/servicedeskapi/customer".format(current_user.instances))
            payload = (
                {
                    "email": form.users_email.data,
                    "displayName": form.users_name.data

                }
            )
            data = j.post(web_url, payload=payload)
            if data.status_code != 201:
                error = "Unable to Create Customer, check the audit log."
                display_name = f"{current_user.username}".capitalize()
                activity = "Failure creating JSD User"
                audit_log = "ERROR: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Customer user created Successfully."
                display_name = f"{current_user.username}".capitalize()
                activity = "JSD User created"
                audit_log = "SUCCESS: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(success)

    return render_template("pages/users.html", title=f"User Creation :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/users/bulk_users", methods=["GET", "POST"])
@login_required
def bulk_users():
    form = UploadForm()
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    if not os.path.exists(our_dir):
        os.mkdir(our_dir)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        form_selection = form.upload_opt.data
        if current_user.get_job_in_progress("bulk_users_creation"):
            error = "A Bulk User Job is in Progress, Please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |displayName | email|
                loop_count = [u for u in reader]
                current_user.launch_jobs("bulk_users_creation", "Bulk Creation of Users", loop_count, form_selection)
                success = "A Job has been submitted for Bulk User Creation, please check the Audit log page for the " \
                          "updated result..."
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
        j.make_session(email=user.email, token=user.token)
        try:
            i = 0
            set_job_progress(0)
            if args[1] == "JSD":
                count = len(args[0])
                for u in args[0]:
                    web_url = ("https://{}/rest/servicedeskapi/customer".format(user.instances))
                    payload = (
                        {
                            "email": u[1],
                            "displayName": u[0]

                        }
                    )
                    data = j.post(web_url, payload=payload)
                    i += 1
                    set_job_progress(100 * i // count)
                    if data.status_code != 201:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure creating Bulk JSD Users {}".format(u[0])
                        audit_log = "ERROR: {}".format(data.status_code)
                        ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                        db.session.add(ad)
                        db.session.commit()
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Success in creating Bulk JSD Users"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                        db.session.add(ad)
                        db.session.commit()
            elif args[1] == "JIRA":
                count = len(args[0])
                for u in args[0]:
                    web_url = ("https://{}/rest/api/3/user".format(user.instances))
                    payload = (
                        {
                            "emailAddress": u[1],
                            "displayName": u[0]

                        }
                    )
                    data = j.post(web_url, payload=payload)
                    i += 1
                    set_job_progress(100 * i // count)
                    if data.status_code != 201:
                        display_name = f"{user.username}".capitalize()
                        activity = "Failure in creating Bulk JIRA Users {}".format(u[0])
                        audit_log = "ERROR: {}".format(data.status_code)
                        ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                                   user_id=user.id)
                        db.session.add(ad)
                        db.session.commit()
                    else:
                        display_name = f"{user.username}".capitalize()
                        activity = "Success in creating Bulk JIRA Users"
                        audit_log = "SUCCESS: {}".format(data.status_code)
                        ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                                   user_id=user.id)
                        db.session.add(ad)
                        db.session.commit()
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/delete_users", methods=["GET", "POST"])
@login_required
def delete_users():
    form = DeleteUserForm()
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        web_url = ("https://{}/rest/api/3/user?accountId={}".format(current_user.instances, form.aaid.data))
        data = j.delete(web_url)
        if data.status_code != 204:
            error = "Unable to delete user as we encountered a blocker."
            display_name = f"{current_user.username}".capitalize()
            activity = "Failure in deleting user"
            audit_log = "ERROR: {}".format(data.status_code)
            ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
            db.session.add(ad)
            db.session.commit()
            flash(error)
        else:
            success = "User Deletion has been completed."
            display_name = f"{current_user.username}".capitalize()
            activity = "Successfully deleted user"
            audit_log = "SUCCESS: {}".format(data.status_code)
            ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
            db.session.add(ad)
            db.session.commit()
            flash(success)
    return render_template("pages/delete.html", title=f"Delete User :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/delete_users/bulk_delete", methods=["GET", "POST"])
@login_required
def bulk_delete():
    form = UploadForm()
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    if not os.path.exists(our_dir):
        os.mkdir(our_dir)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_users_deletion"):
            error = "A Bulk User Deletion Job is in Progress, Please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |id | displayName |
                loop_count = [u for u in reader]
                current_user.launch_jobs("bulk_users_deletion", "Bulk Deletion of Users", loop_count)
                success = "A Job has been submitted for Bulk User Deletion"
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
        j.make_session(email=user.email, token=user.token)
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for u in args[0]:
                web_url = ("https://{}/rest/api/3/user?accountId={}".format(user.instances, u[0]))
                data = j.delete(web_url)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 204:
                    display_name = f"{user.username}".capitalize()
                    activity = "Failure in Bulk user deletion of {}".format(u[1])
                    audit_log = "ERROR: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Executed successfully, Bulk User Deletion"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/create_groups", methods=["GET", "POST"])
@login_required
def create_groups():
    form = CreateGroupForm()
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        k = form.group.data.split(",")
        p = len(k)
        if p == 1:
            web_url = ("https://{}/rest/api/3/group".format(current_user.instances))
            payload = (
                {
                    "name": form.group.data

                }
            )
            data = j.post(web_url, payload=payload)
            if data.status_code != 201:
                error = "Cannot Create Group \"{}\", failure encountered".format(form.group.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Failure in creating user Group"
                audit_log = "ERROR: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Group \"{}\" Created Successfully.".format(form.group.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Successfully Created user Group"
                audit_log = "SUCCESS: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(success)
        elif p > 1:
            if current_user.get_job_in_progress("bulk_create_groups"):
                error = "A Bulk Group Creation Job is in Progress, Please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_create_groups", "Bulk Creation of Groups", k)
                success = "A Job has been submitted for Bulk Creation of Groups, Please check the " \
                          "Audit log for a completion message..."
                db.session.commit()
                flash(success)
    return render_template("/pages/create_grp.html", title=f"Create Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/bulk_create_groups")
def bulk_create_groups(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        j.make_session(email=user.email, token=user.token)
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for uc in args[0]:
                web_url = ("https://{}/rest/api/3/group".format(user.instances))
                payload = (
                    {
                        "name": uc

                    }
                )
                data = j.post(web_url, payload=payload)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 201:
                    display_name = f"{user.username}".capitalize()
                    activity = "Failure in creating Groups {} in Bulk".format(uc)
                    audit_log = "ERROR: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Bulk Group creation successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/delete_groups", methods=["GET", "POST"])
@login_required
def delete_groups():
    form = DeleteGroupForm()
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        k = form.delete_gp.data.split(",")
        p = len(k)
        if p == 1:
            web_url = ("https://{}/rest/api/3/group?groupname={}".format(current_user.instances, form.delete_gp.data))
            data = j.delete(web_url)
            if data.status_code != 200:
                error = "Removing Group \"{}\" failed, check the Audit log for more detail".format(form.delete_gp.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Failure in deleting group"
                audit_log = "ERROR: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Group \"{}\" Removed Successfully".format(form.delete_gp.data)
                display_name = f"{current_user.username}".capitalize()
                activity = "Group deleted successfully"
                audit_log = "SUCCESS: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(success)
        elif p > 1:
            if current_user.get_job_in_progress("bulk_delete_groups"):
                error = "A Bulk Group Deletion Job is in Progress, Please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_delete_groups", "Bulk Deletion of Groups", k)
                success = "A Job has been submitted for Bulk Deletion of Groups, Please check the " \
                          "Audit log for a completion message..."
                db.session.commit()
                flash(success)
    return render_template("/pages/delete_grp.html", title=f"Remove Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/bulk_delete_groups")
def bulk_delete_groups(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        j.make_session(email=user.email, token=user.token)
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for uc in args[0]:
                web_url = ("https://{}/rest/api/3/group?groupname={}".format(user.instances, uc))
                data = j.delete(web_url)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 200:
                    display_name = f"{user.username}".capitalize()
                    activity = "Failure in deleting Multiple groups {}".format(uc)
                    audit_log = "ERROR: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Multiple groups deletion successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/add_groups", methods=["GET", "POST"])
@login_required
def add_groups():
    form = AddUserGroupForm()
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        web_url = ("https://{}/rest/api/3/group/user?groupname={}".format(current_user.instances, form.group_name.data))
        payload = (
            {
                "accountId": form.aaid.data

            }
        )
        data = j.post(web_url, payload=payload)
        if data.status_code != 201:
            error = "Unable to Add user, it seems there's a problem."
            display_name = f"{current_user.username}".capitalize()
            activity = "Failure in adding user to Group"
            audit_log = "ERROR: {}".format(data.status_code)
            ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
            db.session.add(ad)
            db.session.commit()
            flash(error)
        else:
            success = "User Added to Group Successfully."
            display_name = f"{current_user.username}".capitalize()
            activity = "Added user successfully to Group"
            audit_log = "SUCCESS: {}".format(data.status_code)
            ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
            db.session.add(ad)
            db.session.commit()
            flash(success)
    return render_template("/pages/add_grp.html", title=f"Add User to Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/add_groups/bulk_add", methods=["GET", "POST"])
@login_required
def bulk_add():
    form = UploadForm()
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    if not os.path.exists(our_dir):
        os.mkdir(our_dir)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        # saving the file literally to the path as it is named including <space> characters
        filename = secure_filename(str(f.filename))
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_add_users"):
            error = "A Bulk Addition of Users to Group Job is in Progress, Please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |groupName |id | displayName |
                loop_count = [u for u in reader]
                current_user.launch_jobs("bulk_add_users", "Bulk Add users to Groups", loop_count)
                success = "A Job has been submitted for Bulk addition of users to Groups, Please check the " \
                          "Audit log for a completion message..."
                db.session.commit()
                os.remove(o)
                flash(success)
    return render_template("pages/sub_pages/_add_group.html",
                           title=f"Bulk Add Users to Groups :: {bulk.config['APP_NAME_SINGLE']}", error=error,
                           success=success, form=form, Messages=Messages)


@bulk.route("/bulk_add_users")
def bulk_add_users(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        j.make_session(email=user.email, token=user.token)
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for u in args[0]:
                web_url = ("https://{}/rest/api/3/group/user?groupname={}".format(user.instances,
                                                                                  u[0]))
                payload = (
                    {
                        "accountId": u[1]

                    }
                )
                data = j.post(web_url, payload=payload)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 201:
                    display_name = f"{user.username}".capitalize()
                    activity = "Failure adding users {} to Groups {} in Bulk".format(u[2], u[0])
                    audit_log = "ERROR: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Bulk addition of users to Groups successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/remove_groups", methods=["GET", "POST"])
@login_required
def remove_groups():
    form = RemoveUserGroupForm()
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        web_url = ("https://{}/rest/api/3/group/user?groupname={}&accountId={}"
                   .format(current_user.instances, form.group_name.data, form.aaid.data))
        data = j.delete(web_url)
        if data.status_code != 200:
            error = "Unable to Remove user from Group, please check the log."
            display_name = f"{current_user.username}".capitalize()
            activity = "Failure in removing user from Group"
            audit_log = "ERROR: {}".format(data.status_code)
            ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
            db.session.add(ad)
            db.session.commit()
            flash(error)
        else:
            success = "User removed from Group successfully."
            display_name = f"{current_user.username}".capitalize()
            activity = "Successfully removed user from Group"
            audit_log = "SUCCESS: {}".format(data.status_code)
            ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
            db.session.add(ad)
            db.session.commit()
            flash(success)
    return render_template("/pages/remove_grp.html",
                           title=f"Remove User from Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/remove_groups/bulk_remove", methods=["GET", "POST"])
@login_required
def bulk_remove():
    form = UploadForm()
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    if not os.path.exists(our_dir):
        os.mkdir(our_dir)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        # saving the file literally to the path as it is named including <space> characters
        filename = secure_filename(str(f.filename))
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_remove_users"):
            error = "A Bulk Removal of Users from Group Job is in Progress, Please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                loop_count = [u for u in reader]
                # Format for CSV is |groupName |id | displayName |
                current_user.launch_jobs("bulk_remove_users", "Bulk Remove users from Groups", loop_count)
                success = "A Job has been submitted for Bulk removal of users from Groups, Please check the " \
                          "Audit log for a completion message..."
                db.session.commit()
                os.remove(o)
                flash(success)
    return render_template("pages/sub_pages/_remove_group.html",
                           title=f"Bulk Add Users to Groups :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


@bulk.route("/bulk_remove_users")
def bulk_remove_users(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        j.make_session(email=user.email, token=user.token)
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for u in args[0]:
                web_url = ("https://{}/rest/api/3/group/user?groupname={}&accountId={}"
                           .format(user.instances, u[0], u[1]))
                data = j.delete(web_url)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 200:
                    display_name = f"{user.username}".capitalize()
                    activity = "Failure removing multiple users {} from Group {}".format(u[2], u[0])
                    audit_log = "ERROR: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Successfully removed Multiple users from Group"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/projects", methods=["GET", "POST"])
@login_required
def projects():
    form = DeleteProjectForm()
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        f = form.project.data.split(",")
        p = len(f)
        if p == 1:
            web_url = ("https://{}/rest/api/3/project/{}"
                       .format(current_user.instances, form.project.data))
            data = j.delete(web_url)
            if data.status_code != 204:
                error = "Cannot delete Project {} seems an error occurred.".format(form.project.data)
                display_name = f"{current_user.username}".capitalize()
                activity = f"Failure in deleting Project, {form.project.data}"
                audit_log = "ERROR: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Project {} Deleted successfully,".format(form.project.data)
                display_name = f"{current_user.username}".capitalize()
                activity = f"Successfully deleted Project, {form.project.data}"
                audit_log = "SUCCESS: {}".format(data.status_code)
                ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
                db.session.add(ad)
                db.session.commit()
                flash(success)
        elif p > 1:
            if current_user.get_job_in_progress("bulk_projects"):
                error = "A Bulk deletion of Project Job is in Progress, Please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_projects", "Bulk Project deletion", f)
                success = "A Job has been submitted for Bulk deletion of Projects, Please check the " \
                          "Audit log for a completion message..."
                db.session.commit()
                flash(success)
    return render_template("/pages/projects.html", title=f"Delete Projects :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


@bulk.route("/bulk_projects")
def bulk_projects(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        j.make_session(email=user.email, token=user.token)
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for z in args[0]:
                web_url = ("https://{}/rest/api/3/project/{}"
                           .format(current_user.instances, z))
                data = j.delete(web_url)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 204:
                    display_name = f"{user.username}".capitalize()
                    activity = f"Failure deleting these Projects {z}"
                    audit_log = "ERROR: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = f"Success in deleting off these Projects {z}"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/delete_issue", methods=["GET", "POST"])
@login_required
def delete_issue():
    form = DeleteIssuesForm()
    success = None
    error = None
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
            # TODO: this doesn't work well, it can delete up to a particular number then leave the
            #  remaining. need to understand why it behaves that way.
            if m is not None:
                web_url = ("https://{}/rest/api/3/search?jql={}&startAt={}&maxResults={}"
                           .format(current_user.instances, r, start_at, max_results))
                data = j.get(web_url)
                if data.status_code != 200:
                    error = "Unable to fetch JQL Issues due to {}".format(data.reason)
                    flash(error)
                else:
                    jql_data = json.loads(data.content)
                    total = jql_data["total"]
                    full_number = int(total / 1)
                    if str(jql_data["issues"]) == "[]":
                        error = "JQL: {} Issues returned, Please use another Query" \
                            .format(total)
                        flash(error)
                    else:
                        if current_user.get_job_in_progress("bulk_schedule_delete"):
                            error = "A Bulk deletion using JQL Job is in Progress, Please wait till it's finished."
                            flash(error)
                        else:
                            current_user.launch_jobs("bulk_schedule_delete", "Bulk deletion with JQL", total, r,
                                                     start_at, max_results, full_number, sub_task)
                            success = "A Job has been submitted for Bulk deletion of Issues using JQL, " \
                                      "Please check the Audit log for a completion message..."
                            flash(success)
                            db.session.commit()
            else:
                web_url = ("https://{}/rest/api/3/issue/{}?deleteSubtasks={}"
                           .format(current_user.instances, form.issues.data, form.sub_task.data))
                data = j.delete(web_url)
                if data.status_code != 204:
                    error = "Cannot delete Issue {} something went wrong!".format(form.issues.data)
                    display_name = f"{current_user.username}".capitalize()
                    activity = f"Failure deleting single issue {form.issues.data}"
                    audit_log = "ERROR: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=current_user.id)
                    db.session.add(ad)
                    db.session.commit()
                    flash(error)
                else:
                    success = "Issue {} Deleted with success".format(form.issues.data)
                    display_name = f"{current_user.username}".capitalize()
                    activity = f"Deleted off single issue {form.issues.data}"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=current_user.id)
                    db.session.add(ad)
                    db.session.commit()
                    flash(success)
        elif p > 1:
            if current_user.get_job_in_progress("bulk_delete_issues"):
                error = "A Bulk deletion of issues Job is in Progress, Please wait till it's finished."
                flash(error)
            else:
                current_user.launch_jobs("bulk_delete_issues", "Bulk Issue deletion", q, sub_task)
                success = "A Job has been submitted for Bulk deletion of Issues, Please check the " \
                          "Audit log for a completion message..."
                db.session.commit()
                flash(success)
    return render_template("/pages/delete_issue.html", title=f"Delete Issues :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/bulk_delete_issues")
def bulk_delete_issues(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        j.make_session(email=user.email, token=user.token)
        q = args[0]
        sub_task = args[1]
        try:
            set_job_progress(0)
            i = 0
            count = len(q)
            for z in q:
                web_url = ("https://{}/rest/api/3/issue/{}?deleteSubtasks={}"
                           .format(user.instances, z, sub_task))
                data = j.delete(web_url)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 204:
                    display_name = f"{user.username}".capitalize()
                    activity = "Multiple issue deletion failed"
                    audit_log = "ERROR: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Multiple issue deletion successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()

        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/bulk_schedule_delete")
def bulk_schedule_delete(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        j.make_session(email=user.email, token=user.token)
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
                        web_ex = ("https://{}/rest/api/3/search?jql={}&startAt={}&maxResults={}"
                                  .format(user.instances, r, start_at, max_results))
                        info = j.get(web_ex)
                        wjson = json.loads(info.content)
                        count = len(list(wjson["issues"]))
                        for w in list(wjson["issues"]):
                            web_url = ("https://{}/rest/api/3/issue/{}?deleteSubtasks={}"
                                       .format(user.instances, w["key"], sub_task))
                            data = j.delete(web_url)
                            i += 1
                            set_job_progress(100 * i // count)
                            if data.status_code != 204:
                                display_name = f"{user.username}".capitalize()
                                activity = "Failure in JQL, Issue deletion returned error"
                                audit_log = "ERROR: {}".format(data.status_code)
                                ad = Audit(display_name=display_name, activity=activity,
                                           audit_log=audit_log,
                                           user_id=user.id)
                                db.session.add(ad)
                                db.session.commit()
                            else:
                                display_name = f"{user.username}".capitalize()
                                activity = "Multiple Issues were deleted"
                                audit_log = "SUCCESS: {}".format(data.status_code)
                                ad = Audit(display_name=display_name, activity=activity,
                                           audit_log=audit_log,
                                           user_id=user.id)
                                db.session.add(ad)
                                db.session.commit()

                    start_at += 50
                    if start_at > (full_number - 1):
                        break

            schedule_delete()
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/project_lead", methods=["GET", "POST"])
@login_required
def project_lead():
    form = ChangeProjectLeadForm()
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        web_url = ("https://{}/rest/api/3/project/{}"
                   .format(current_user.instances, form.project.data))
        payload = (
            {
                "leadAccountId": form.aaid.data,
                "assigneeType": form.assignee.data,
                "key": form.project.data,

            }
        )
        data = j.put(web_url, payload=payload)
        if data.status_code != 200:
            error = "Cannot change Project Lead Project {} due to an error.".format(form.project.data)
            display_name = f"{current_user.username}".capitalize()
            activity = "Failed updating Project Lead"
            audit_log = "ERROR: {}".format(data.status_code)
            ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
            db.session.add(ad)
            db.session.commit()
            flash(error)
        else:
            success = "Project Lead changed for Project {} is completed.".format(form.project.data)
            display_name = f"{current_user.username}".capitalize()
            activity = "Project Lead updated successfully"
            audit_log = "SUCCESS: {}".format(data.status_code)
            ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log, user_id=current_user.id)
            db.session.add(ad)
            db.session.commit()
            flash(success)
    return render_template("/pages/project_lead.html",
                           title=f"Change Project Lead :: {bulk.config['APP_NAME_SINGLE']}", form=form,
                           error=error, success=success, Messages=Messages)


@bulk.route("/project_lead/bulk_lead", methods=["GET", "POST"])
@login_required
def bulk_lead():
    form = UploadForm()
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    if not os.path.exists(our_dir):
        os.mkdir(our_dir)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        # saving the file literally to the path as it is named including <space> characters
        filename = secure_filename(str(f.filename))
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        delimiter = form.delimiter.data
        if current_user.get_job_in_progress("bulk_project_lead"):
            error = "A Bulk Change of Project Lead Job is in Progress, Please wait till it's finished."
            flash(error)
        else:
            with open(o, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                next(reader, None)
                # Format for CSV is |id | key | assignee_type |
                loop_count = [u for u in reader]
                current_user.launch_jobs("bulk_project_lead", "Bulk Change Project lead", loop_count)
                success = "A Job has been submitted for Bulk Change of Project Leads, Please check the " \
                          "Audit log for a completion message..."
                db.session.commit()
                os.remove(o)
                flash(success)
    return render_template("pages/sub_pages/_change_lead.html",
                           title=f"Bulk Add Users to Groups :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


@bulk.route("/bulk_project_lead")
def bulk_project_lead(user_id, *args):
    with bulk.app_context():
        user = User.query.get(user_id)
        j.make_session(email=user.email, token=user.token)
        try:
            set_job_progress(0)
            i = 0
            count = len(args[0])
            for u in args[0]:
                web_url = ("https://{}/rest/api/3/project/{}"
                           .format(user.instances, u[1]))
                payload = (
                    {
                        "leadAccountId": u[0],
                        "assigneeType": u[2],
                        "key": u[1],

                    }
                )
                data = j.put(web_url, payload=payload)
                i += 1
                set_job_progress(100 * i // count)
                if data.status_code != 200:
                    display_name = f"{user.username}".capitalize()
                    activity = "Error, Bulk changing Project Lead"
                    audit_log = "ERROR: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
                else:
                    display_name = f"{user.username}".capitalize()
                    activity = "Bulk Project Lead Change successful"
                    audit_log = "SUCCESS: {}".format(data.status_code)
                    ad = Audit(display_name=display_name, activity=activity, audit_log=audit_log,
                               user_id=user.id)
                    db.session.add(ad)
                    db.session.commit()
        except Exception as e:
            bulk.logger.error('Unhandled exception', exc_info=sys.exc_info())
        finally:
            set_job_progress(100)


@bulk.route("/audit", methods=["GET", "POST"])
@login_required
def audit():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    page = request.args.get("page", 1, type=int)
    logs = user.audit.order_by(Audit.timestamp.desc()).paginate(page, current_app.config["AUDIT_PER_PAGE"], False)
    next_url = url_for("audit", page=logs.next_num) if logs.has_next else None
    prev_url = url_for("audit", page=logs.prev_num) if logs.has_prev else None
    return render_template("/config/audit.html", title=f"Audit Log :: {bulk.config['APP_NAME_SINGLE']}",
                           logs=logs.items, next_url=next_url, prev_url=prev_url, Messages=Messages)


@bulk.route("/messages/inbox", methods=["GET", "POST"])
@login_required
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
        success = f"Your Message has been sent to the {bulk.config['APP_NAME_SINGLE']} Team"
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
        success = "Your Message has been sent Successfully"
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
        success = f"Your Message has been sent to the {bulk.config['APP_NAME_SINGLE']} Team"
        flash(success)
    return render_template("/pages/send_message.html",
                           title=f"Messages - Send Messages::{bulk.config['APP_NAME_SINGLE']}",
                           msg=msg.items, next_url=next_url, prev_url=prev_url, success=success, error=error,
                           form=form, Messages=Messages, admin=admin)


# delete sent messages
@bulk.route("/messages/sent/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete_messages(id):
    msg = Messages.query.get(id)
    db.session.delete(msg)
    db.session.commit()
    flash("Your message has been deleted...")
    return redirect(url_for("sent_messages"))


# view sent messages
@bulk.route("/messages/sent/<int:id>/view", methods=["GET", "POST"])
@login_required
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
        success = f"Your Message has been sent to the {bulk.config['APP_NAME_SINGLE']} Team"
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
        success = f"Your Message has been sent to the {bulk.config['APP_NAME_SINGLE']} Team"
        flash(success)
    return render_template("/pages/stats.html",
                           title=f"Messages - Stats ::{bulk.config['APP_NAME_SINGLE']}", r_msg=r_msg,
                           s_msg=s_msg, t_msg=t_msg, Messages=Messages, form=form, error=error,
                           success=success, admin=admin)


@bulk.route("/messages/notifications", methods=["GET", "POST"])
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


@bulk.route("/settings/config", methods=["GET", "POST"])
@login_required
def config():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    error = None
    success = None
    data = None
    load_data = None
    form = TokenForm()
    r_msg = user.received_messages.order_by(Messages.timestamp.desc()).count()
    j.make_session(email=current_user.email, token=current_user.token)
    if request.method == "GET":
        form.token.data = current_user.token
        form.notify_me.data = current_user.notify_me
        web_url = ("https://{}/rest/api/3/myself".format(current_user.instances))
        data = j.get(web_url)
        if data.status_code == 200:
            load_data = json.loads(data.content)
    return render_template("/config/config.html",
                           title=f"Configuration - Check Stats ::{bulk.config['APP_NAME_SINGLE']}", r_msg=r_msg,
                           Messages=Messages, user=user, form=form, error=error, success=success,
                           data=data, load_data=load_data)


@bulk.route("/settings/delete", methods=["GET", "POST"])
@login_required
def account_delete():
    success = None
    error = None
    import glob
    user = User.query.filter_by(username=current_user.username).first_or_404()
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    files = glob.glob(f"{save_path}/*")
    if request.method == "POST":
        if os.path.exists(save_path):
            for f in files:
                os.remove(f)
            os.rmdir(save_path)
        db.session.delete(user)
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
        flash("Your API token has been Saved!")
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
