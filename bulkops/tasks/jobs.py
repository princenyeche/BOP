from bulkops.database import Jobs
from rq import get_current_job
from bulkops import db


def set_job_progress(progress):
    job = get_current_job()
    if job:
        job.meta["progress"] = progress
        job.save_meta()
        task = Jobs.query.get(job.get_id())
        task.user.add_notification("task_progress", {"task_id": job.get_id(),
                                                     "progress": progress})
        if progress >= 100:
            task.completion = True
        db.session.commit()
