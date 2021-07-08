from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bulkops import db
from flask_login import UserMixin
from bulkops import login
from hashlib import sha256
from time import time
from flask import current_app
from itsdangerous import URLSafeTimedSerializer
import jwt
import json
from bulkops import bulk
import redis
import rq


# initialize the SQLAlchemy class Model with db variable
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    instances = db.Column(db.String(140), index=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    register_date = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    confirm_user = db.Column(db.Boolean, nullable=False, default=False)
    confirm_period = db.Column(db.DateTime, nullable=True)
    token = db.Column(db.String(64), index=True)
    notify_me = db.Column(db.String(5), index=True)
    audit = db.relationship("Audit", backref="audits", lazy="dynamic", cascade="all,delete")

    sent_messages = db.relationship("Messages", foreign_keys="Messages.sender_id",
                                    backref="sender", lazy="dynamic", cascade="all,delete")
    received_messages = db.relationship("Messages", foreign_keys="Messages.receiver_id",
                                        backref="receiver", lazy="dynamic", cascade="all,delete")
    last_read_message = db.Column(db.DateTime)

    notifications = db.relationship("Notification", backref="user", lazy="dynamic", cascade="all,delete")
    
    jobs = db.relationship("Jobs", backref="user", lazy="dynamic", cascade="all,delete")

    def __repr__(self):
        return "<User {}>".format(self.username)

    def new_messages(self):
        last_time_read = self.last_read_message or datetime(1900, 1, 1)
        return Messages.query.filter_by(receiver=self).filter(
            Messages.timestamp > last_time_read).count()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = sha256(self.email.lower().encode("utf-8")).hexdigest()
        return "https://www.gravatar.com/avatar/{}?d=identicon&s={}".format(
            digest, size)

    def get_reset_password_token(self, expires=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time() + expires},
            bulk.config["SECRET_KEY"], algorithm="HS256").decode("utf-8")

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, bulk.config["SECRET_KEY"], algorithms="HS256")["reset_password"]
        except:
            return
        return User.query.get(id)
    
    @staticmethod
    def create_user_confirmation(email):
        parsers = URLSafeTimedSerializer(bulk.config['SECRET_KEY'])
        return parsers.dumps(email, salt=bulk.config['SECURITY_SALT'])

    @staticmethod
    def getuser_confirmation_token(token, expiration=3600):
        parsers = URLSafeTimedSerializer(bulk.config['SECRET_KEY'])
        try:
            email = parsers.loads(
                token,
                salt=bulk.config['SECURITY_SALT'],
                max_age=expiration)
        except:
            return False
        return email
    
    def launch_jobs(self, name, description, *args, **kwargs):
        req_job = current_app.job_queue.enqueue("bulkops.main.views." + name, self.id, *args, job_timeout=bulk.config['QUEUE_TIMEOUT'], 
                                                **kwargs)
        jobs = Jobs(id=req_job.get_id(), name=name, description=description, user=self)
        db.session.add(jobs)
        return jobs

    def get_job_in_progress(self, name):
        return Jobs.query.filter_by(name=name, user=self, completion=False).first()

    def get_jobs_in_progress(self):
        return Jobs.query.filter_by(user=self, completion=False).all()


class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    audit_log = db.Column(db.String(140), index=True)
    display_name = db.Column(db.String(64), index=True)
    activity = db.Column(db.String(220), index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __repr__(self):
        return "<Audit {}>".format(self.audit_log)


class Messages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    subject = db.Column(db.String(120), index=True)
    body = db.Column(db.String(1000), index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return "<Messages {}>".format(self.body)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload = db.Column(db.Text)

    def run_data(self):
        return json.loads(str(self.payload))
    

class Jobs(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(225), index=True)
    description = db.Column(db.String(225), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    completion = db.Column(db.Boolean, default=False)

    def get_job(self):
        try:
            req_job = rq.job.Job.fetch(self.id, connection=bulk.redis)
        except (redis.exceptions.RedisError, rq.queue.NoSuchJobError):
            return None
        return req_job

    def get_progress(self):
        job = self.get_job()
        return job.meta.get("progress", 0) if job is not None else 100


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
