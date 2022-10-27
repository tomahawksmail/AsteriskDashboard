from flask import Flask, render_template, request, make_response, session, redirect, flash, escape
from settings import host, user, password, db, version, host2, user2, password2, db2
import datetime
import pymysql
import io
import csv

app = Flask(__name__)
app.secret_key = 'admin'

@app.route("/base", methods=['POST', 'GET'])
def base():
    return render_template('base.html', version=version)

@app.route("/", methods=['POST', 'GET'])
def start():
    return redirect("/login")

@app.route("/logout", methods=['POST', 'GET'])
def logout():
    session.pop('user', None)
    flash('Вы вышли из системы')
    return redirect("/login")




# @app.route("/login", methods=['POST', 'GET'])
# def login():
#     if request.method == 'POST':
#         if request.form["user"] != 'admin' or request.form["password"] != app.secret_key:
#             flash("Не верный логин или пароль")
#             return redirect("/login")
#         elif request.form["user"] == 'admin' and request.form["password"] == app.secret_key:
#             session['user'] = request.form['user']
#             return redirect("/index")
#     else:
#         pass
#     return render_template('login.html', version=version)

@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form["user"]
        password = request.form["password"]
        param = (username, password)
        con = pymysql.connect(host=host2, user=user2, password=password2, db=db2, use_unicode=True, charset='utf8')
        loginrequest = con.cursor()
        loginrequest.execute("""SELECT * FROM users where (username = %s and password= %s)""", param)
        resault = loginrequest.fetchone()

        if resault == None:
            flash("Не верный логин или пароль")
            return redirect("/login")
        else:
            session['user'] = request.form['user']
            return redirect("/index")

    return render_template('login.html', version=version)




@app.route("/index", methods=['POST', 'GET'])
def index():
    if 'user' in session:
        con = pymysql.connect(host=host, user=user, password=password, db=db, use_unicode=True, charset='utf8')
        # Запрос Время  по часам
        cur_time_hour = con.cursor()
        cur_time_hour.execute("""SELECT * FROM DashboardInOutHourCurrentDate""")
        data_time_hour = cur_time_hour.fetchall()

        # Запрос Время по операторам
        cur_total_time_oper = con.cursor()
        cur_total_time_oper.execute("""SELECT  tDate, ext, t_in, t_out
                                        FROM DashboardInOutHourCurrentDayPerExtention
                                        """)
        data_total_time_oper = cur_total_time_oper.fetchall()

        # Запрос Общее время разговора за сегодня
        cur_total_time = con.cursor()
        cur_total_time.execute(""" 
                                    SELECT   SUM(t_in), SUM(t_out)
                                    FROM DashboardInOutHourCurrentDayPerExtention
                                    """)
        data_total_time = cur_total_time.fetchone()
        cur_missingcalls = con.cursor()
        cur_missingcalls.execute("""SELECT COUNT(t1) FROM DashboardMissedCallsToday""")

        miss = cur_missingcalls.fetchone()[0]

        # Запрос maxoper

        maxoper = con.cursor()
        maxoper.execute("""SELECT ext  FROM DashboardInOutHourCurrentDayPerExtention
                    WHERE (t_in + t_out) = (SELECT MAX(t_in + t_out) FROM DashboardInOutHourCurrentDayPerExtention)""")

        maxoper = maxoper.fetchone()[0]



        # Запрос minoper
        minoper = con.cursor()
        minoper.execute("""SELECT ext, (t_in + t_out)
                            FROM DashboardInOutHourCurrentDayPerExtention  
                            WHERE (
                            (t_in + t_out) = (SELECT MIN(t_in + t_out) FROM DashboardInOutHourCurrentDayPerExtention 
                            WHERE (t_in + t_out) > 0 AND ext <> '6000')  AND ext <> '6000') 
                                               """)
        minoper = minoper.fetchone()[0]

        # Запрос для графика
        cur_miss = con.cursor()
        cur_miss.execute("""SELECT HOUR(ttime), COUNT(t1) FROM DashboardMissedCallsToday GROUP BY t1""")
        missgraph = cur_miss.fetchall()

        con.close()
        return render_template('index.html', version=version, data_time_hour=data_time_hour,
                               data_total_time_oper=data_total_time_oper, data_total_time=data_total_time, miss=miss,
                               maxoper=maxoper, minoper=minoper, missgraph=missgraph)
    else:
        flash("You are not logged in")
        return redirect("/login")

@app.route("/viborka", methods=['POST', 'GET'])
def viborka():
    if 'user' in session:
        message = ''
        try:
            con = pymysql.connect(host=host, user=user, password=password, db=db, use_unicode=True, charset='utf8')

        except Exception:
            print(Exception)
        else:
            if request.method == 'GET':
                data = ''
                message1 = ''
                message2 = ''

            if request.method == 'POST':

                # запрос к данным формы
                calldate = request.form.get('calldate')  # запрос к данным формы
                timefrom = request.form.get('timefrom')
                timeto = request.form.get('timeto')
                tSource = request.form.get('tSource')
                tDistenation = request.form.get('tDistenation')
                type_ = request.form.get('type_')
                direction = request.form.get('direction')

                if calldate == '':
                    calldate = str(datetime.date.today())
                if timefrom == '':
                    timefrom = '00:00'
                if timeto == '':
                    timeto = '23:59'

                resultdatetimefrom = calldate + ' ' + timefrom
                resultdatetimeto = calldate + ' ' + timeto
                resultdatetimefrom = str(datetime.datetime.strptime(resultdatetimefrom, '%Y-%m-%d %H:%M'))
                resultdatetimeto = str(datetime.datetime.strptime(resultdatetimeto, '%Y-%m-%d %H:%M'))

                cur_Calls = con.cursor()

                if type_ == 'Входящие':
                    type = 'in'
                    param = (
                        resultdatetimefrom, resultdatetimeto, '%' + str(tSource) + '%', '%' + str(tDistenation) + '%', type)
                    cur_Calls.execute("""SELECT time(calldate),
                                                        SUBSTRING_INDEX(SUBSTRING_INDEX(recordingfile, '-', 3), '-', -1) AS tSource,
                                                        SUBSTRING_INDEX(SUBSTRING_INDEX(recordingfile, '-', 2), '-', -1) AS tDistenation,
                                                        dst,
                                                        SUBSTRING_INDEX(recordingfile, '-', 1) AS type_,
                                                        SEC_TO_TIME(duration),
                                                        SEC_TO_TIME(billsec),
                                                        SEC_TO_TIME(duration - billsec) AS waittime,
                                                        recordingfile
    
                                                        from cdr
                                                        WHERE (calldate BETWEEN %s AND %s)
                                                        AND 
                                                        (SUBSTRING_INDEX(SUBSTRING_INDEX(recordingfile, '-', 3), '-', -1) LIKE %s) 
                                                        AND
                                                        (SUBSTRING_INDEX(SUBSTRING_INDEX(recordingfile, '-', 2), '-', -1) LIKE %s)
                                                        AND
                                                        (SUBSTRING_INDEX(recordingfile, '-', 1) LIKE %s) 
                                                        AND
                                                        (billsec > 1) 
                                                        AND 
                                                        (recordingfile != '')
                                                        
                                                        ORDER BY calldate""", param)
                    data = cur_Calls.fetchall()
                    # AND dst LIKE '6___'
                    message1 = 'Вы выбрали звонки на дату ' + str(calldate) + ' между ' + str(timefrom) + ' и ' + str(
                        timeto)

                    message2 = 'Фильтр: вызывающий =' + str(tSource) + ' ,вызываемый =' + str(
                        tDistenation) + ', направление =' + str(direction) + ' и тип =' + str(type_)

                if type_ == 'Исходящие':
                    param = (
                        resultdatetimefrom, resultdatetimeto, '%' + str(tSource) + '%', '%' + str(tDistenation) + '%')
                    cur_Calls.execute("""SELECT time(calldate),
                                                    SUBSTRING_INDEX(SUBSTRING_INDEX(recordingfile, '-', 3), '-', -1) AS tSource,
                                                    SUBSTRING_INDEX(SUBSTRING_INDEX(recordingfile, '-', 2), '-', -1) AS tDistenation,
                                                    '' as temp,
                                                    SUBSTRING_INDEX(recordingfile, '-', 1) AS type_,
                                                    SEC_TO_TIME(duration),
                                                    SEC_TO_TIME(billsec),
                                                    SEC_TO_TIME(duration - billsec) AS waittime,
                                                    recordingfile
                                                    
                                                    from cdr
                                                    WHERE (calldate BETWEEN %s AND %s)
                                                    AND 
                                                    (SUBSTRING_INDEX(SUBSTRING_INDEX(recordingfile, '-', 3), '-', -1) LIKE %s) 
                                                    AND
                                                    (SUBSTRING_INDEX(SUBSTRING_INDEX(recordingfile, '-', 2), '-', -1) LIKE %s)
                                                     
                                                    AND
                                                    (billsec > 1) 
                                                    AND 
                                                    (recordingfile != '')
                                                    AND SUBSTRING_INDEX(SUBSTRING_INDEX(recordingfile, '-', 3), '-', -1) LIKE '6___'
                                                    ORDER BY calldate""", param)
                    data = cur_Calls.fetchall()

                    message1 = 'Вы выбрали звонки на дату ' + str(calldate) + ' между ' + str(timefrom) + ' и ' + str(
                        timeto)

                    message2 = 'Фильтр: вызывающий =' + str(tSource) + ' ,вызываемый =' + str(
                        tDistenation) + ', направление =' + str(direction) + ' и тип =' + str(type_)

            return render_template('viborka.html',
                                   data=data, message1=message1, message2=message2, version=version)
        finally:
            con.close()
    else:
        flash("You are not logged in")
        return redirect("/login")


@app.route("/missedcallstoday", methods=['POST', 'GET'])
def missedcallstoday():
    con = pymysql.connect(host=host, user=user, password=password, db=db, use_unicode=True, charset='utf8')

    # Запрос на пропущенные
    cur_missingcalls = con.cursor()
    sql = """SELECT  tDATE, tTIME, callid, duration, n1, n2 FROM DashboardMissedCallsToday"""
    cur_missingcalls.execute(sql)
    data_cur_missingcalls = cur_missingcalls.fetchall()

    # Запрос для графика
    cur_miss = con.cursor()
    cur_miss.execute("""SELECT HOUR(ttime), COUNT(t1) FROM DashboardMissedCallsToday GROUP BY t1""")
    miss = cur_miss.fetchall()
    con.close()
    return render_template('missedcallstoday.html',
                           data_cur_missingcalls=data_cur_missingcalls,
                           version=version, miss=miss)


@app.route("/masterreport", methods=['POST', 'GET'])
def masterreport():
    global a, b
    try:
        con = pymysql.connect(host=host, user=user, password=password, db=db, use_unicode=True, charset='utf8')

    except Exception:
        print(Exception)
    else:

        if request.method == 'GET':
            data_in = ''
            data_out = ''

        if request.method == 'POST':
            data_in = ''
            data_out = ''

            calldate_from = request.form.get('calldate_from')  # запрос к данным формы
            calldate_to = request.form.get('calldate_to')  # запрос к данным формы

            if calldate_from == '':
                calldate_from = datetime.date.today()

            else:
                calldate_from = request.form.get('calldate_from')

            if calldate_to == '':
                calldate_to = datetime.date.today()
            else:
                calldate_to = request.form.get('calldate_to')

            cur_Calls = con.cursor()


            if "submit_btn_in" in request.form:
                par = (
                    calldate_from,
                    calldate_to,
                    'in%'
                )

                cur_Calls.execute("""SELECT calldate, src, dst, SEC_TO_TIME(duration), SEC_TO_TIME(billsec), TIME((duration - billsec)),
                                        SUBSTRING_INDEX(SUBSTRING(recordingfile, LOCATE('-', recordingfile)+1), '-', 1) AS 'Направление'
                                        from cdr
                                        WHERE (DATE(calldate)  BETWEEN  %s AND  %s) AND
                                        (LENGTH(src) > 4) AND (LENGTH(dst) > 2)
                                        AND (recordingfile LIKE %s)
                                        GROUP BY recordingfile
                                        ORDER BY calldate""", par)

                data_in = cur_Calls.fetchall()
                a = data_in
            if "submit_btn_out" in request.form:
                par = (
                    calldate_from,
                    calldate_to,
                    'out%')

                cur_Calls.execute("""SELECT calldate, cnum, src, dst, if(SEC_TO_TIME(billsec)>2, SEC_TO_TIME(billsec), "-----") AS billtime
                                            from cdr
                                            WHERE ((DATE(calldate) BETWEEN  %s AND  %s))
                                            AND
                                            (LENGTH(src) > 4) AND (LENGTH(dst) > 2) AND (duration > 1)
                                            AND (recordingfile LIKE %s)
                                            GROUP BY recordingfile
                                            ORDER BY calldate""", par)

                data_out = cur_Calls.fetchall()
                b = data_out
            if "export_to_csv_in" in request.form:

                output = io.StringIO()
                writer = csv.writer(output, dialect='excel-tab', delimiter=";")
                line = ['Date', 'ABONENT', 'OPERATOR', 'FULL duration',
                        'speaking duration', 'wait time', 'external number']
                writer.writerow(line)

                for row in a:
                    dataline = [str(row[0]), row[1], row[2], str(row[3]), str(
                        row[4]), str(row[5]), row[6]]
                    writer.writerow(dataline)
                file = make_response(output.getvalue())
                file.headers["Content-Disposition"] = "attachment; filename=export_in.csv"
                file.headers["Content-type"] = "text/csv; charset=utf-8"

                return file
            if "export_to_csv_out" in request.form:

                output = io.StringIO()
                writer = csv.writer(output, dialect='excel-tab', delimiter=";")
                line = ['Date', 'ABONENT', 'OPERATOR', 'FULL duration',
                        'speaking duration', 'wait time', 'external number']
                writer.writerow(line)

                for row in b:
                    dataline = [str(row[0]), row[3], row[1], '-----', str(row[4]), '-----', row[2]]
                    writer.writerow(dataline)
                file = make_response(output.getvalue())
                file.headers["Content-Disposition"] = "attachment; filename=export_out.csv"
                file.headers["Content-type"] = "text/csv; charset=utf-8"

                return file


        return render_template('masterreport.html', data_in=data_in, data_out=data_out, version=version)

    finally:
        con.close()


@app.route("/missedstatistic", methods=['POST', 'GET'])
def missedstatistic():
    con = pymysql.connect(host=host, user=user, password=password, db=db, use_unicode=True, charset='utf8')

    # Запрос на пропущенные
    cur_missingcallsall = con.cursor()
    sql = """SELECT * FROM DashboardMissedCallsAll ORDER BY DT DESC LIMIT 30"""
    cur_missingcallsall.execute(sql)
    data_cur_missingcallsall = cur_missingcallsall.fetchall()

    cur_missingcallsallgraph = con.cursor()
    sql = """SELECT * FROM DashboardMissedCallsAll ORDER BY DT DESC LIMIT 30"""
    cur_missingcallsallgraph.execute(sql)
    missedgraph = cur_missingcallsallgraph.fetchall()

    con.close()
    return render_template('missedstatistic.html',
                           data_cur_missingcallsall=data_cur_missingcallsall,
                           version=version, missedgraph=missedgraph)


@app.route("/avgtime", methods=['POST', 'GET'])
def avgtime():
    con = pymysql.connect(host=host, user=user, password=password, db=db, use_unicode=True, charset='utf8')

    # Запрос
    cur_avgtime = con.cursor()
    sql = """SELECT hour(calldate) AS h, round(avg(hanguptime-starttime), 0) AS 'Ожидание', round(avg(endtime-starttime), 0) AS 'Полное время' from
                (
                SELECT cdr.calldate, cdr.src, cdr.dst, cdr.duration, cdr.billsec, cdr.uniqueid, 
                sum(case when cel.eventtype = 'CHAN_START'   then  TIME_TO_SEC(time(cel.eventtime))  ELSE 0 END) AS starttime,
                sum(case when cel.eventtype = 'BRIDGE_ENTER' then  TIME_TO_SEC(time(cel.eventtime))  ELSE 0 END) AS hanguptime,
                sum(case when cel.eventtype = 'CHAN_END'     then  TIME_TO_SEC(time(cel.eventtime))  ELSE 0 END) AS endtime
                FROM cdr
                JOIN cel ON cdr.uniqueid = cel.uniqueid
                WHERE 
                (DATE(cdr.calldate) = DATE(CURDATE())) AND 
                (cel.eventtype = 'CHAN_START' OR cel.eventtype = 'BRIDGE_ENTER' OR cel.eventtype = 'CHAN_END') AND 
                dst = '1' AND cdr.disposition = 'ANSWERED' AND cdr.billsec > 0 
                GROUP BY uniqueid) AS temp WHERE hanguptime-starttime > 0
                GROUP BY h"""
    cur_avgtime.execute(sql)
    data_avgtime = cur_avgtime.fetchall()
    con.close()
    return render_template('avgtime.html',
                           data_avgtime=data_avgtime,
                           version=version)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
