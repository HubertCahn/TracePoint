#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, jsonify, g, request
from celery import Celery
from task import send2FCM
import mydb
import math
import time
import sys  

reload(sys)  
sys.setdefaultencoding('utf8')

app = Flask(__name__)

@app.before_request
def before_request():
    g.mydb = mydb.MyDataBase()
    return

@app.route("/api/login", methods=['POST'])
def login():

    user_email = None
    user_pw = None
    user_token = None

    try:
        user_email = request.form["user_email"]
        user_pw = request.form["user_pw"]
        user_token = request.form["user_token"]
    finally:
        if user_email is None or user_pw is None or user_token is None:
            return jsonify(status="ERROR", message="missing parameters",code=500)

        login_query = "SELECT user_id, user_head FROM user_info WHERE user_email = \'%s\' and user_pw = \'%s\'" % (user_email, user_pw)
        g.mydb.cursor.execute(login_query)

        db_return = g.mydb.cursor.fetchone()
        if db_return is None:
            return jsonify(status="ERROR", message="user email or user password is incorrect",code=400)
        user_id = db_return['user_id']
        user_head = db_return['user_head']
        update_query = "UPDATE user_info SET user_token=\'%s\' WHERE user_id=%s" % (user_token, user_id)
        g.mydb.cursor.execute(update_query)
        g.mydb.db.commit()
        return jsonify(status="OK",message="login successfully",user_id=user_id,user_head=user_head,code=200)

@app.route("/api/logout", methods=['POST'])
def logout():
    user_id = None
    try:
        user_id = request.form["user_id"]
    finally:
        if user_id is None:
            return jsonify(status="ERROR", message="missing parameters",code=500)

        update_query = "UPDATE user_info SET user_token=NULL WHERE user_id=%s" % (user_id)
        g.mydb.cursor.execute(update_query)
        g.mydb.db.commit()
        return jsonify(status="OK",message="logout successfully",code=200)

@app.route("/api/register", methods=['POST'])
def register():

    user_email = None
    user_pw = None
    user_name = None

    try:
        user_email = request.form["user_email"]
        user_pw = request.form["user_pw"]
        user_name = request.form["user_name"]
    finally:
        if user_email is None or user_pw is None or user_name is None:
            return jsonify(status="ERROR", message="missing parameters",code=500)

        check_query = "SELECT user_email FROM user_info WHERE user_email = \'%s\'" % user_email
        g.mydb.cursor.execute(check_query)
        db_return = g.mydb.cursor.fetchone()
        if db_return is not None:
            return jsonify(status="ERROR", message="user email exist!",code=401)

        register_query = "INSERT INTO user_info VALUES (NULL,\'%s\', \'%s\', \'%s\', \'anonymousmask\', NULL)" % (user_email, user_pw, user_name)
        g.mydb.cursor.execute(register_query)
        g.mydb.db.commit()
        return jsonify(status="OK",message="register successfully",code=200)

@app.route("/api/publish_trace", methods=['POST'])
def publish_trace():
    user_id = None
    longitude = None
    latitude = None
    geohash = None
    text = None
    try:
        user_id = request.form["user_id"]
        longitude = request.form["longitude"]
        latitude = request.form["latitude"]
        geohash = request.form["geohash"]
        text = request.form["text"]
    finally:
        if user_id is None or longitude is None or latitude is None \
        or geohash is None or text is None:
            return jsonify(status="ERROR", message="missing parameters", code=500)
        else:
            date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()+8*3600))
            publish_query = "INSERT INTO trace_content VALUES (NULL,\'%s\', %s, %s, \'%s\', \'%s\')" \
            % (date, longitude, latitude, geohash, text)
            g.mydb.cursor.execute(publish_query)
            g.mydb.db.commit()
            updateid_query = "INSERT INTO user_trace SELECT NULL, LAST_INSERT_ID(), %s" % (user_id)
            g.mydb.cursor.execute(updateid_query)
            g.mydb.db.commit()
            return jsonify(status="OK",message="publish trace successfully",code=200)

@app.route("/api/publish_comment", methods=['POST'])
def publish_comment():
    user_id = None
    trace_id = None
    text = None
    try:
        user_id = request.form["user_id"]
        trace_id = request.form["trace_id"]
        text = request.form["text"]
    finally:
        if user_id is None or trace_id is None or text is None:
            return jsonify(status="ERROR", message="missing parameters", code=500)
        else:
            date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()+8*3600))
            publish_query = "INSERT INTO trace_comment VALUES (NULL, %s, %s, \'%s\', \'%s\')" \
            % (trace_id, user_id, text, date)
            g.mydb.cursor.execute(publish_query)
            g.mydb.db.commit()
            token_query = "SELECT user_token FROM user_info WHERE user_id = (SELECT user_id FROM user_trace WHERE trace_id=%s)" % (trace_id)
            g.mydb.cursor.execute(token_query)
            db_return = g.mydb.cursor.fetchone()
            if db_return is None:
                return jsonify(status="ERROR",message="cannot find token from datebase",code=400)
            user_token = db_return['user_token']
            info_query = "SELECT user_name,user_head FROM user_info WHERE user_id =%s" % (user_id)
            g.mydb.cursor.execute(info_query)
            db_return = g.mydb.cursor.fetchone()
            user_name = db_return['user_name']
            user_head = db_return['user_head']
            messagebody = "你的好友%s发表了评论:%s" % (user_name, text)
            send2FCM.delay(user_token, user_head, messagebody)
            return jsonify(status="OK",message="publish comment successfully",code=200)

@app.route("/api/publish_like", methods=['POST'])
def publish_like():
    user_id = None
    trace_id = None
    try:
        user_id = request.form["user_id"]
        trace_id = request.form["trace_id"]
    finally:
        if user_id is None or trace_id is None:
            return jsonify(status="ERROR", message="missing parameters", code=500)
        else:
            check_query = "SELECT id FROM trace_like WHERE trace_id=%s AND user_id=%s" % (trace_id, user_id)
            g.mydb.cursor.execute(check_query)
            db_return = g.mydb.cursor.fetchone()
            if db_return is None:
                date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()+8*3600))
                publish_query = "INSERT INTO trace_like VALUES (NULL, %s, %s, \'%s\')" \
                % (trace_id, user_id, date)
                g.mydb.cursor.execute(publish_query)
                g.mydb.db.commit()
                token_query = "SELECT user_token FROM user_info WHERE user_id = (SELECT user_id FROM user_trace WHERE trace_id=%s)" % (trace_id)
                g.mydb.cursor.execute(token_query)
                db_return = g.mydb.cursor.fetchone()
                if db_return is None:
                    return jsonify(status="ERROR",message="cannot find token from datebase",code=400)
                user_token = db_return['user_token']
                info_query = "SELECT user_name,user_head FROM user_info WHERE user_id =%s" % (user_id)
                g.mydb.cursor.execute(info_query)
                db_return = g.mydb.cursor.fetchone()
                user_name = db_return['user_name']
                user_head = db_return['user_head']
                messagebody = "你的好友%s给你点赞了" % (user_name)
                send2FCM.delay(user_token, user_head, messagebody)
                return jsonify(status="OK",message="publish like successfully",code=200)
            else:
                return jsonify(status="ERROR", message="you have liked this trace already",code=400)

@app.route("/api/get_traces", methods=['GET'])
def get_traces():
    geohash_1 = None;
    geohash_2 = None;
    geohash_3 = None;
    geohash_4 = None;
    geohash_5 = None;
    geohash_6 = None;
    geohash_7 = None;
    geohash_8 = None;
    geohash_9 = None;
    try:
        geohash_1 = request.args.get("geohash_1")
        geohash_2 = request.args.get("geohash_2")
        geohash_3 = request.args.get("geohash_3")
        geohash_4 = request.args.get("geohash_4")
        geohash_5 = request.args.get("geohash_5")
        geohash_6 = request.args.get("geohash_6")
        geohash_7 = request.args.get("geohash_7")
        geohash_8 = request.args.get("geohash_8")
        geohash_9 = request.args.get("geohash_9")
    finally:
        if geohash_1 is None or geohash_2 is None or geohash_3 is None or geohash_4 is None \
        or geohash_5 is None or geohash_6 is None or geohash_7 is None or geohash_8 is None \
        or geohash_9 is None :
            return jsonify(status="ERROR", message="missing parameters", code=500)
        else :          
            get_trace_query = "SELECT ui.user_name, ui.user_head, tc.date, tc.text ,tc.trace_id, tc.longitude, tc.latitude FROM user_trace AS ut INNER JOIN trace_content AS tc \
            ON ut.trace_id=tc.trace_id INNER JOIN user_info AS ui ON ui.user_id = ut.user_id \
            WHERE tc.geohash IN (\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\")" % \
            (geohash_1, geohash_2, geohash_3, geohash_4, geohash_5, geohash_6, geohash_7, geohash_8, geohash_9)
            g.mydb.cursor.execute(get_trace_query)
            traces_list = []
            while(1):
                trace = g.mydb.cursor.fetchone()
                if trace is None:
                    break
                else:
                    trace['longitude'] = str(trace['longitude'])
                    trace['latitude'] = str(trace['latitude'])
                    traces_list.append(trace)

            get_comment_query = "SELECT ui.user_name, tcom.text, tcom.trace_id FROM trace_comment AS tcom \
            INNER JOIN user_info AS ui ON tcom.user_id=ui.user_id WHERE tcom.trace_id IN (SELECT tc.trace_id FROM user_trace AS ut INNER JOIN trace_content AS tc \
            ON ut.trace_id=tc.trace_id INNER JOIN user_info AS ui ON ui.user_id = ut.user_id \
            WHERE tc.geohash IN (\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"))" % \
            (geohash_1, geohash_2, geohash_3, geohash_4, geohash_5, geohash_6, geohash_7, geohash_8, geohash_9)
            g.mydb.cursor.execute(get_comment_query)
            comments_list = []
            while(1):
                comment = g.mydb.cursor.fetchone()
                if comment is None:
                    break
                else:
                    comments_list.append(comment)

            get_like_query = "SELECT tl.user_id, tl.trace_id FROM trace_like AS tl \
            WHERE tl.trace_id IN (SELECT tc.trace_id FROM user_trace AS ut INNER JOIN trace_content AS tc \
            ON ut.trace_id=tc.trace_id INNER JOIN user_info AS ui ON ui.user_id = ut.user_id \
            WHERE tc.geohash IN (\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"))" % \
            (geohash_1, geohash_2, geohash_3, geohash_4, geohash_5, geohash_6, geohash_7, geohash_8, geohash_9)
            g.mydb.cursor.execute(get_like_query)
            likes_list = []
            while(1):
                like = g.mydb.cursor.fetchone()
                if like is None:
                    break
                else:
                    likes_list.append(like)

            return jsonify(status="OK", trace_data=traces_list, comment_data=comments_list, like_data=likes_list, code=200)

@app.route("/api/change_head", methods=['POST'])
def change_head():
    user_id = None
    user_head = None
    try:
        user_id = request.form["user_id"]
        user_head = request.form["user_head"]
    finally:
        if user_id is None or user_head is None:
            return jsonify(status="ERROR", message="missing parameters",code=500)

        update_query = "UPDATE user_info SET user_head=\'%s\' WHERE user_id=%s" % (user_head, user_id)
        g.mydb.cursor.execute(update_query)
        g.mydb.db.commit()
        return jsonify(status="OK",message="change head successfully",code=200)

@app.route("/api/change_name", methods=['POST'])
def change_name():
    user_id = None
    user_name = None
    try:
        user_id = request.form["user_id"]
        user_name = request.form["user_name"]
    finally:
        if user_id is None or user_name is None:
            return jsonify(status="ERROR", message="missing parameters",code=500)

        update_query = "UPDATE user_info SET user_name=\'%s\' WHERE user_id=%s" % (user_name, user_id)
        g.mydb.cursor.execute(update_query)
        g.mydb.db.commit()
        return jsonify(status="OK",message="change name successfully",code=200)

@app.route("/api/request_info", methods=['GET'])
def request_info():
    user_id = request.args.get("user_id") 

    if user_id is None :
        return jsonify(status="ERROR", message="missing parameters",code=500)

    get_query = "SELECT ui.user_name, ui.user_head, count(ut.trace_id) AS count_trace FROM user_trace AS ut \
    INNER JOIN user_info AS ui ON  ut.user_id=ui.user_id WHERE ut.user_id=%s" % (user_id)
    g.mydb.cursor.execute(get_query)
    info_data = g.mydb.cursor.fetchone()
    count_trace = info_data['count_trace']
    user_head = info_data['user_head']
    user_name = info_data['user_name']
    return jsonify(status="OK", count_trace=count_trace,user_head=user_head,user_name=user_name,code=200)

@app.route("/api/get_person_traces", methods=['GET'])
def get_person_traces():
    user_id = None
    try:
        user_id = request.args.get("user_id")
    finally:
        if user_id is None:
            return jsonify(status="ERROR", message="missing parameters", code=500)
        else :          
            get_trace_query = "SELECT ui.user_name, ui.user_head, tc.date, tc.text, tc.trace_id, tc.longitude, tc.latitude FROM user_trace AS ut INNER JOIN trace_content AS tc \
            ON ut.trace_id=tc.trace_id INNER JOIN user_info AS ui ON ui.user_id = ut.user_id WHERE ut.user_id=%s" % (user_id)
            g.mydb.cursor.execute(get_trace_query)
            traces_list = []
            while(1):
                trace = g.mydb.cursor.fetchone()
                if trace is None:
                    break
                else:
                    trace['longitude'] = str(trace['longitude'])
                    trace['latitude'] = str(trace['latitude'])
                    traces_list.append(trace)

            get_comment_query = "SELECT ui.user_name, tcom.text, tcom.trace_id FROM trace_comment AS tcom \
            INNER JOIN user_info AS ui ON tcom.user_id=ui.user_id WHERE tcom.trace_id IN (SELECT ut.trace_id FROM user_trace AS ut WHERE ut.user_id=%s)" % (user_id)
            g.mydb.cursor.execute(get_comment_query)
            comments_list = []
            while(1):
                comment = g.mydb.cursor.fetchone()
                if comment is None:
                    break
                else:
                    comments_list.append(comment)

            get_like_query = "SELECT tl.user_id, tl.trace_id FROM trace_like AS tl \
            WHERE tl.trace_id IN (SELECT ut.trace_id FROM user_trace AS ut WHERE ut.user_id=%s)" % (user_id)
            g.mydb.cursor.execute(get_like_query)
            likes_list = []
            while(1):
                like = g.mydb.cursor.fetchone()
                if like is None:
                    break
                else:
                    likes_list.append(like)

            return jsonify(status="OK", trace_data=traces_list, comment_data=comments_list, like_data=likes_list, code=200)

@app.teardown_request
def teardown_request(exception): 
    mydb = getattr(g, 'mydb', None) 
    if mydb is not None:
        mydb.db.close()
    return
    
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')


