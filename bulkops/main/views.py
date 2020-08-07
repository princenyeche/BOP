import requests
import json
import os
import re
import csv
from flask import render_template, flash, redirect, url_for, current_app
from bulkops.database import User, Audit, Messages, Notification
from flask_login import current_user
from flask import request, jsonify
from flask_login import login_required
from bulkops import db
from bulkops.main.forms import SettingsForm, TokenForm, CreateGroupForm, \
    DeleteUserForm, CreateUsersForm, AddUserGroupForm, RemoveUserGroupForm, DeleteGroupForm, \
    ChangeProjectLeadForm, DeleteProjectForm, DeleteIssuesForm, UploadForm, MessageForm
from datetime import datetime
from requests.auth import HTTPBasicAuth
from werkzeug.utils import secure_filename
from bulkops import bulk
from threading import Thread

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = "Files"
bulk.config["UPLOAD_FOLDER"] = os.path.join(basedir, UPLOAD_FOLDER)
our_dir = os.path.join(bulk.config["UPLOAD_FOLDER"])
file_limit = bulk.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
if os.path.exists(our_dir):
    pass
else:
    os.mkdir(our_dir)

auth_request = None
headers = None


class JiraUsers:
    def __init__(self):
        pass

    @staticmethod
    def make_session(email=None, token=None):
        global auth_request
        global headers
        auth_request = HTTPBasicAuth(email, token)
        headers = {"Content-Type": "application/json"}


j = JiraUsers()


@bulk.route("/", methods=["GET", "POST"])
@bulk.route("/index", methods=["GET", "POST"])
@login_required
def index():
    data = None
    j.make_session(email=current_user.email, token=current_user.token)
    if request.method == "GET":
        webURL = ("https://{}/rest/api/3/myself".format(current_user.instances))
        data = requests.get(webURL, auth=auth_request, headers=headers)
        if data.status_code != 200:
            flash("Your API Token is invalid, please go to the Settings > Configuration page to have it sorted")
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
    ad = Audit(audits=current_user)
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
        elif i < 6:
            error = "Your Password must be equal or greater than 6 Characters in length"
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
            ad.display_name = f"{current_user.username}".capitalize()
            ad.activity = f"Changes made to Settings From:{v}  To:{current_user.instances}"
            ad.audit_log = f"CHANGES: Configuration"
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
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        if form.users_opt.data == "JIRA":
            webURL = ("https://{}/rest/api/3/user".format(current_user.instances))
            payload = (
                {
                    "emailAddress": form.users_email.data,
                    "displayName": form.users_name.data

                }
            )
            data = requests.post(webURL, auth=auth_request, json=payload, headers=headers)
            if data.status_code != 201:
                error = "Unable to Create user, probably due to an error"
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Failure creating JIRA User"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "User Created Successfully, Please check your Admin hub to confirm."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Created JIRA User successfully"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(success)
        elif form.users_opt.data == "JSD":
            webURL = ("https://{}/rest/servicedeskapi/customer".format(current_user.instances))
            payload = (
                {
                    "email": form.users_email.data,
                    "displayName": form.users_name.data

                }
            )
            data = requests.post(webURL, auth=auth_request, json=payload, headers=headers)
            if data.status_code != 201:
                error = "Unable to Create Customer, check the audit log."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Failure creating JSD User"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Customer user created Successfully."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "JSD User created"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(success)

    return render_template("pages/users.html", title=f"User Creation :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/users/bulk_users", methods=["GET", "POST"])
@login_required
def bulk_users():
    form = UploadForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        if form.upload_opt.data == "JSD":
            with open(o, "r") as csvFile:
                reader = csv.reader(csvFile, delimiter=form.delimiter.data)
                next(reader, None)
                # Format for CSV is |displayName | email|
                for u in reader:
                    webURL = ("https://{}/rest/servicedeskapi/customer".format(current_user.instances))
                    payload = (
                        {
                            "email": u[1],
                            "displayName": u[0]

                        }
                    )
                    data = requests.post(webURL, auth=auth_request, json=payload, headers=headers)
                if data.status_code != 201:
                    error = "Unable to Create Multiple Customer, an error occurred."
                    ad.display_name = f"{current_user.username}".capitalize()
                    ad.activity = "Failure creating Bulk JSD Users"
                    ad.audit_log = "ERROR: {}".format(data.status_code)
                    db.session.add(ad)
                    db.session.commit()
                    flash(error)
                else:
                    success = "Multiple Customer users created Successfully."
                    ad.display_name = f"{current_user.username}".capitalize()
                    ad.activity = "Success in creating Bulk JSD Users"
                    ad.audit_log = "SUCCESS: {}".format(data.status_code)
                    db.session.add(ad)
                    db.session.commit()
                    flash(success)
        elif form.upload_opt.data == "JIRA":
            with open(o, "r") as csvFile:
                reader = csv.reader(csvFile, delimiter=",")
                next(reader, None)
                for u in reader:
                    webURL = ("https://{}/rest/api/3/user".format(current_user.instances))
                    payload = (
                        {
                            "email": u[1],
                            "displayName": u[0]

                        }
                    )
                    data = requests.post(webURL, auth=auth_request, json=payload, headers=headers)
                if data.status_code != 201:
                    error = "Unable to Create Multiple Jira users, something went wrong."
                    ad.display_name = f"{current_user.username}".capitalize()
                    ad.activity = "Failure in creating Bulk JIRA Users"
                    ad.audit_log = "ERROR: {}".format(data.status_code)
                    db.session.add(ad)
                    db.session.commit()
                    os.remove(o)
                    flash(error)
                else:
                    success = "Multiple Jira users created Successfully."
                    ad.display_name = f"{current_user.username}".capitalize()
                    ad.activity = "Success in creating Bulk JIRA Users"
                    ad.audit_log = "SUCCESS: {}".format(data.status_code)
                    db.session.add(ad)
                    db.session.commit()
                    os.remove(o)
                    flash(success)
    return render_template("users/sub_pages/_create_jira_user.html",
                           title=f"Bulk User Creation :: {bulk.config['APP_NAME_SINGLE']}", error=error,
                           success=success, form=form, Messages=Messages)


@bulk.route("/delete_users", methods=["GET", "POST"])
@login_required
def delete_users():
    form = DeleteUserForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        webURL = ("https://{}/rest/api/3/user?accountId={}".format(current_user.instances, form.aaid.data))
        data = requests.delete(webURL, auth=auth_request, headers=headers)
        if data.status_code != 204:
            error = "Unable to delete user as we encountered a blocker."
            ad.display_name = f"{current_user.username}".capitalize()
            ad.activity = "Failure in deleting user"
            ad.audit_log = "ERROR: {}".format(data.status_code)
            db.session.add(ad)
            db.session.commit()
            flash(error)
        else:
            success = "User Deletion has been completed."
            ad.display_name = f"{current_user.username}".capitalize()
            ad.activity = "Successfully deleted user"
            ad.audit_log = "SUCCESS: {}".format(data.status_code)
            db.session.add(ad)
            db.session.commit()
            flash(success)
    return render_template("pages/delete.html", title=f"Delete User :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/delete_users/bulk_delete", methods=["GET", "POST"])
@login_required
def bulk_delete():
    form = UploadForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        with open(o, "r") as csvFile:
            reader = csv.reader(csvFile, delimiter=form.delimiter.data)
            next(reader, None)
            # Format for CSV is |id | displayName |
            for u in reader:
                webURL = ("https://{}/rest/api/3/user?accountId={}".format(current_user.instances, u[0]))
                data = requests.delete(webURL, auth=auth_request, headers=headers)
            if data.status_code != 204:
                error = "Unable to  delete Multiple users, check the audit log for the cause."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Failure in Bulk user deletion"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                os.remove(o)
                flash(error)
            else:
                success = "Multiple User deletion completed."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Executed successfully, Bulk User Deletion"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                os.remove(o)
                flash(success)
    return render_template("users/sub_pages/_delete_user.html",
                           title=f"Bulk User Deletion :: {bulk.config['APP_NAME_SINGLE']}", error=error,
                           success=success, form=form, Messages=Messages)


@bulk.route("/create_groups", methods=["GET", "POST"])
@login_required
def create_groups():
    form = CreateGroupForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    data = None
    if request.method == "POST" and form.validate_on_submit():
        K = form.group.data.split(",")
        p = len(K)
        if p == 1:
            webURL = ("https://{}/rest/api/3/group".format(current_user.instances))
            payload = (
                {
                    "name": form.group.data

                }
            )
            data = requests.post(webURL, auth=auth_request, json=payload, headers=headers)
            if data.status_code != 201:
                error = "Cannot Create Group \"{}\", failure encountered".format(form.group.data)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Failure in creating user Group"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Group \"{}\" Created Successfully.".format(form.group.data)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Successfully Created user Group"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(success)
        elif p > 1:
            for uc in K:
                webURL = ("https://{}/rest/api/3/group".format(current_user.instances))
                payload = (
                    {
                        "name": uc

                    }
                )
                data = requests.post(webURL, auth=auth_request, json=payload, headers=headers)
            if data.status_code != 201:
                error = "Cannot Create Multiple Groups, check the Audit log for more detail."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Failure in creating Groups in Bulk"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Multiple Groups Created Successfully."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Bulk Group creation successful"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(success)
    return render_template("/pages/create_grp.html", title=f"Create Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, error=error, success=success, Messages=Messages)


@bulk.route("/delete_groups", methods=["GET", "POST"])
@login_required
def delete_groups():
    form = DeleteGroupForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    data = None
    if request.method == "POST" and form.validate_on_submit():
        K = form.delete_gp.data.split(",")
        p = len(K)
        if p == 1:
            webURL = ("https://{}/rest/api/3/group?groupname={}".format(current_user.instances, form.delete_gp.data))
            data = requests.delete(webURL, auth=auth_request, headers=headers)
            if data.status_code != 200:
                error = "Removing Group \"{}\" failed, check the Audit log for more detail".format(form.delete_gp.data)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Failure in deleting group"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Group \"{}\" Removed Successfully".format(form.delete_gp.data)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Group deleted successfully"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(success)
        elif p > 1:
            for uc in K:
                webURL = ("https://{}/rest/api/3/group?groupname={}".format(current_user.instances, uc))
                data = requests.delete(webURL, auth=auth_request, headers=headers)
            if data.status_code != 200:
                error = "Removing multiple Groups failed, please check the log to know why."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Failure in deleting Multiple groups"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Multiple Group Removal Successful."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Multiple groups deletion successful"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(success)
    return render_template("/pages/delete_grp.html", title=f"Remove Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/add_groups", methods=["GET", "POST"])
@login_required
def add_groups():
    form = AddUserGroupForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        webURL = ("https://{}/rest/api/3/group/user?groupname={}".format(current_user.instances, form.group_name.data))
        payload = (
            {
                "accountId": form.aaid.data

            }
        )
        data = requests.post(webURL, auth=auth_request, json=payload, headers=headers)
        if data.status_code != 201:
            error = "Unable to Add user, it seems there's a problem."
            ad.display_name = f"{current_user.username}".capitalize()
            ad.activity = "Failure in adding user to Group"
            ad.audit_log = "ERROR: {}".format(data.status_code)
            db.session.add(ad)
            db.session.commit()
            flash(error)
        else:
            success = "User Added to Group Successfully."
            ad.display_name = f"{current_user.username}".capitalize()
            ad.activity = "Added user successfully to Group"
            ad.audit_log = "SUCCESS: {}".format(data.status_code)
            db.session.add(ad)
            db.session.commit()
            flash(success)
    return render_template("/pages/add_grp.html", title=f"Add User to Group :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/add_groups/bulk_add", methods=["GET", "POST"])
@login_required
def bulk_add():
    form = UploadForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        # saving the file literally to the path as it is named including <space> characters
        filename = secure_filename(str(f.filename))
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        with open(o, "r") as csvFile:
            reader = csv.reader(csvFile, delimiter=form.delimiter.data)
            next(reader, None)
            # Format for CSV is |groupName |id | displayName |
            for u in reader:
                webURL = ("https://{}/rest/api/3/group/user?groupname={}".format(current_user.instances,
                                                                                 u[0]))
                payload = (
                    {
                        "accountId": u[1]

                    }
                )
                data = requests.post(webURL, auth=auth_request, json=payload, headers=headers)
            if data.status_code != 201:
                error = "Unable to Add Multiple Users to group because an error occurred."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Failure adding users to Groups in Bulk"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                os.remove(o)
                flash(error)
            else:
                success = "Multiple users has been added to your group, Yay!"
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Bulk addition of users to Groups successful"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                os.remove(o)
                flash(success)
    return render_template("pages/sub_pages/_add_group.html",
                           title=f"Bulk Add Users to Groups :: {bulk.config['APP_NAME_SINGLE']}", error=error,
                           success=success, form=form, Messages=Messages)


@bulk.route("/remove_groups", methods=["GET", "POST"])
@login_required
def remove_groups():
    form = RemoveUserGroupForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        webURL = ("https://{}/rest/api/3/group/user?groupname={}&accountId={}"
                  .format(current_user.instances, form.group_name.data, form.aaid.data))
        data = requests.delete(webURL, auth=auth_request, headers=headers)
        if data.status_code != 200:
            error = "Unable to Remove user from Group, please check the log."
            ad.display_name = f"{current_user.username}".capitalize()
            ad.activity = "Failure in removing user from Group"
            ad.audit_log = "ERROR: {}".format(data.status_code)
            db.session.add(ad)
            db.session.commit()
            flash(error)
        else:
            success = "User removed from Group successfully."
            ad.display_name = f"{current_user.username}".capitalize()
            ad.activity = "Successfully removed user from Group"
            ad.audit_log = "SUCCESS: {}".format(data.status_code)
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
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    progress = 0
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        # saving the file literally to the path as it is named including <space> characters
        filename = secure_filename(str(f.filename))
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        with open(o, "r") as csvFile:
            reader = csv.reader(csvFile, delimiter=form.delimiter.data)
            next(reader, None)
            # Format for CSV is |groupName |id | displayName |
            for u in reader:
                webURL = ("https://{}/rest/api/3/group/user?groupname={}&accountId={}"
                          .format(current_user.instances, u[0], u[1]))
                data = requests.delete(webURL, auth=auth_request, headers=headers)
            if data.status_code != 200:
                error = "Unable to Remove Multiple Users {} from group {}. Something went wrong!".format(u[2], u[0])
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Failure removing multiple users from Group"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                os.remove(o)
                flash(error)
            else:
                success = "Multiple Users removed from group successfully."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Successfully removed Multiple users from Group"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                os.remove(o)
                flash(success)
    return render_template("pages/sub_pages/_remove_group.html",
                           title=f"Bulk Add Users to Groups :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, progress=progress, Messages=Messages)


@bulk.route("/projects", methods=["GET", "POST"])
@login_required
def projects():
    form = DeleteProjectForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    data = None
    if request.method == "POST" and form.validate_on_submit():
        F = form.project.data.split(",")
        p = len(F)
        if p == 1:
            webURL = ("https://{}/rest/api/3/project/{}"
                      .format(current_user.instances, form.project.data))
            data = requests.delete(webURL, auth=auth_request, headers=headers)
            if data.status_code != 204:
                error = "Cannot delete Project {} seems an error occurred.".format(form.project.data)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = f"Failure in deleting Project, {form.project.data}"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Project {} Deleted successfully,".format(form.project.data)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = f"Successfully deleted Project, {form.project.data}"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(success)
        elif p > 1:
            for z in F:
                webURL = ("https://{}/rest/api/3/project/{}"
                          .format(current_user.instances, z))
                data = requests.delete(webURL, auth=auth_request, headers=headers)
            if data.status_code != 204:
                error = "Cannot Delete Multiple Projects {} because an error occurred.".format(form.project.data)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = f"Failure deleting these Projects {form.project.data}"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Projects {} Deleted completely.".format(form.project.data)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = f"Success in deleting off these Projects {form.project.data}"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(success)
    return render_template("/pages/projects.html", title=f"Delete Projects :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


@bulk.route("/delete_issue", methods=["GET", "POST"])
@login_required
def delete_issue():
    form = DeleteIssuesForm()
    ad = Audit(audits=current_user)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        G = form.issues.data.split(",")
        K = form.issues.data
        m = re.search("JQL:", K)
        p = len(G)
        r = K.strip("JQL:")
        startAt = 0
        maxResults = 50
        if p == 1:
            # TODO: this doesn't work well, it can delete up to a particular number then leave the
            #  remaining. need to understand why it behaves that way.
            if m is not None:
                webURL = ("https://{}/rest/api/3/search?jql={}&startAt={}&maxResults={}"
                          .format(current_user.instances, r, startAt, maxResults))
                data = requests.get(webURL, auth=auth_request, headers=headers)
                if data.status_code != 200:
                    error = "Unable to fetch JQL Issues due to {}".format(data.reason)
                    flash(error)
                else:
                    jql_data = json.loads(data.content)
                    total = jql_data["total"]
                    fullNumber = int(total / 1)
                    if str(jql_data["issues"]) == "[]":
                        error = "JQL: {} Issues returned, Please use another Query" \
                            .format(total)
                        flash(error)

                    def schedule_delete():
                        nonlocal startAt, success, error, data
                        while maxResults < total or maxResults > total:
                            if startAt < fullNumber:
                                webEx = ("https://{}/rest/api/3/search?jql={}&startAt={}&maxResults={}"
                                         .format(current_user.instances, r, startAt, maxResults))
                                info = requests.get(webEx, auth=auth_request, headers=headers)
                                wjson = json.loads(info.content)
                                for w in list(wjson["issues"]):
                                    webURL = ("https://{}/rest/api/3/issue/{}?deleteSubtasks={}"
                                              .format(current_user.instances, w["key"], form.sub_task.data))
                                    data = requests.delete(webURL, auth=auth_request, headers=headers)
                                if data.status_code != 204:
                                    error = "JQL: Cannot Delete Multiple Issues because something went wrong!"
                                    ad.display_name = f"{current_user.username}".capitalize()
                                    ad.activity = "Failure in JQL, Issue deletion returned error"
                                    ad.audit_log = "ERROR: {}".format(data.status_code)
                                    db.session.add(ad)
                                    db.session.commit()
                                    flash(error)
                                else:
                                    success = "JQL: {} Issues Deleted successfully.".format(total)
                                    ad.display_name = f"{current_user.username}".capitalize()
                                    ad.activity = "Multiple Issues were deleted"
                                    ad.audit_log = "SUCCESS: {}".format(data.status_code)
                                    db.session.add(ad)
                                    db.session.commit()
                                    flash(success)
                            startAt += 50
                            if startAt > (fullNumber - 1):
                                break

                    Thread(target=schedule_delete()).start()
            else:
                webURL = ("https://{}/rest/api/3/issue/{}?deleteSubtasks={}"
                          .format(current_user.instances, form.issues.data, form.sub_task.data))
                data = requests.delete(webURL, auth=auth_request, headers=headers)
                if data.status_code != 204:
                    error = "Cannot delete Issue {} something went wrong!".format(form.issues.data)
                    ad.display_name = f"{current_user.username}".capitalize()
                    ad.activity = f"Failure deleting single issue {form.issues.data}"
                    ad.audit_log = "ERROR: {}".format(data.status_code)
                    db.session.add(ad)
                    db.session.commit()
                    flash(error)
                else:
                    success = "Issue {} Deleted with success".format(form.issues.data)
                    ad.display_name = f"{current_user.username}".capitalize()
                    ad.activity = f"Deleted off single issue {form.issues.data}"
                    ad.audit_log = "SUCCESS: {}".format(data.status_code)
                    db.session.add(ad)
                    db.session.commit()
                    flash(success)
        elif p > 1:
            data = None
            z = None
            for z in G:
                webURL = ("https://{}/rest/api/3/issue/{}?deleteSubtasks={}"
                          .format(current_user.instances, z, form.sub_task.data))
                data = requests.delete(webURL, auth=auth_request, headers=headers)
            if data.status_code != 204:
                error = "Cannot Delete Multiple Issues {} because an error occurred.".format(z)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Multiple issue deletion failed"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(error)
            else:
                success = "Issues {} Deleted completely.".format(z)
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Multiple issue deletion successful"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                flash(success)
    return render_template("/pages/delete_issue.html", title=f"Delete Issues :: {bulk.config['APP_NAME_SINGLE']}",
                           form=form, success=success, error=error, Messages=Messages)


@bulk.route("/project_lead", methods=["GET", "POST"])
@login_required
def project_lead():
    form = ChangeProjectLeadForm()
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    if request.method == "POST" and form.validate_on_submit():
        webURL = ("https://{}/rest/api/3/project/{}"
                  .format(current_user.instances, form.project.data))
        payload = (
            {
                "leadAccountId": form.aaid.data,
                "assigneeType": form.assignee.data,
                "key": form.project.data,

            }
        )
        data = requests.put(webURL, auth=auth_request, json=payload, headers=headers)
        if data.status_code != 200:
            error = "Cannot change Project Lead Project {} due to an error.".format(form.project.data)
            ad.display_name = f"{current_user.username}".capitalize()
            ad.activity = "Failed updating Project Lead"
            ad.audit_log = "ERROR: {}".format(data.status_code)
            db.session.add(ad)
            db.session.commit()
            flash(error)
        else:
            success = "Project Lead changed for Project {} is completed.".format(form.project.data)
            ad.display_name = f"{current_user.username}".capitalize()
            ad.activity = "Project Lead updated successfully"
            ad.audit_log = "SUCCESS: {}".format(data.status_code)
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
    ad = Audit(audits=current_user)
    j.make_session(email=current_user.email, token=current_user.token)
    success = None
    error = None
    user_dir = current_user.username
    save_path = os.path.join(our_dir, user_dir)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if request.method == "POST" and form.validate_on_submit():
        f = form.docs.data
        # saving the file literally to the path as it is named including <space> characters
        filename = secure_filename(str(f.filename))
        f.save(os.path.join(save_path, filename))
        o = os.path.join(save_path, filename)
        with open(o, "r") as csvFile:
            reader = csv.reader(csvFile, delimiter=form.delimiter.data)
            next(reader, None)
            # Format for CSV is |id | key | assignee_type |
            for u in reader:
                webURL = ("https://{}/rest/api/3/project/{}"
                          .format(current_user.instances, u[1]))
                payload = (
                    {
                        "leadAccountId": u[0],
                        "assigneeType": u[2],
                        "key": u[1],

                    }
                )
                data = requests.put(webURL, auth=auth_request, json=payload, headers=headers)
            if data.status_code != 200:
                error = "Cannot change Multiple Project Lead Project due to an error!"
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Error, Bulk changing Project Lead"
                ad.audit_log = "ERROR: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                os.remove(o)
                flash(error)
            else:
                success = "Multiple Project Lead change completed."
                ad.display_name = f"{current_user.username}".capitalize()
                ad.activity = "Bulk Project Lead Change successful"
                ad.audit_log = "SUCCESS: {}".format(data.status_code)
                db.session.add(ad)
                db.session.commit()
                os.remove(o)
                flash(success)
    return render_template("pages/sub_pages/_change_lead.html",
                           title=f"Bulk Add Users to Groups :: {bulk.config['APP_NAME_SINGLE']}",
                           error=error, success=success, form=form, Messages=Messages)


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
        webURL = ("https://{}/rest/api/3/myself".format(current_user.instances))
        data = requests.get(webURL, auth=auth_request, headers=headers)
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
            os.removedirs(save_path)
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
