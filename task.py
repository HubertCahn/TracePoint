from celery import Celery
from flask import Flask
import requests

def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='amqp://guest@0.0.0.0'
)
celery = make_celery(app)


@celery.task()
def send2FCM(device_token, user_head, messagebody):

    api_key = 'AAAAe3Aeku4:APA91bFH-TvdAu4IEGDe4c5ELhI1hlbstOqTugND6euVWVYHHEarcaMrYlpXdBv5f9lttbQnJAcmDWUK4UmBIi6QDOkVGb-8vKR_w1-KGVcPAmJA96ewxBFRYm0I8ICNR9sAqRdYUMhB'
    url = 'https://fcm.googleapis.com/fcm/send'

    headers = {
        'Authorization':'key='+api_key,
        'Content-Type':'application/json'
    }

    payload = {
        'to':device_token,
        'notification':{
            'tag':user_head,
            'body':messagebody
        }
    }

    r = requests.post(url, headers=headers, json=payload)

    if r.status_code == 200:
        print "Request sent to FCM server successfully!"

if __name__ == '__main__':
    app.run(host='0.0.0.0')