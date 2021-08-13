from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired

allowed_files = ["csv", "xlsx", "xls"]
error_message = "File format is not Accepted, only \"CSV\", \"XLSX\" or \"XLS\" files allowed!"


class SettingsForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    instances = StringField("Instances", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")])


class TokenForm(FlaskForm):
    token = StringField("Token", validators=[DataRequired()])
    notify_me = StringField("Check")


class DeleteUserForm(FlaskForm):
    aaid = StringField("AccountId", validators=[DataRequired()])
    users_opt = StringField("Select Option")


class CreateGroupForm(FlaskForm):
    group = StringField("Group", validators=[DataRequired()])


class DeleteGroupForm(FlaskForm):
    delete_gp = StringField("Delete Group", validators=[DataRequired()])


class AddUserGroupForm(FlaskForm):
    group_name = StringField("Group Name", validators=[DataRequired()])
    aaid = StringField("AccountId", validators=[DataRequired()])


class RemoveUserGroupForm(FlaskForm):
    group_name = StringField("Group Name", validators=[DataRequired()])
    aaid = StringField("AccountId", validators=[DataRequired()])


class CreateUsersForm(FlaskForm):
    users_name = StringField("Users", validators=[DataRequired()])
    users_email = StringField("User Email", validators=[DataRequired()])
    users_opt = StringField("User Option", validators=[DataRequired()])


class UploadForm(FlaskForm):
    docs = FileField("Upload File", validators=[FileRequired(), FileAllowed(allowed_files, error_message)])
    upload_opt = StringField("User Option")
    delimiter = StringField("Delimiter")


class ChangeProjectLeadForm(FlaskForm):
    project = StringField("Project Key", validators=[DataRequired()])
    aaid = StringField("AccountId", validators=[DataRequired()])
    assignee = StringField("Assignee Type", validators=[DataRequired()])


class DeleteProjectForm(FlaskForm):
    project = StringField("Project Key", validators=[DataRequired()])
    undo = StringField("Enable undo", validators=[DataRequired()])


class DeleteIssuesForm(FlaskForm):
    issues = StringField("Issue Key", validators=[DataRequired()])
    sub_task = StringField("Sub_task")


class DeleteSearchForm(FlaskForm):
    jql_search = StringField("Issue Key", validators=[DataRequired()])


class MessageForm(FlaskForm):
    messages = TextAreaField("Messages", validators=[DataRequired(), Length(min=0, max=980)])
    subject = StringField("Subject", validators=[DataRequired()])
    receiver = StringField("Receiver")
