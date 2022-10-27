from datetime import datetime
import asyncio
from panoramisk import Manager
from settings import host, username, passw, host2, user2, password2, db2
import pymysql
from time import sleep
LOG_FILE = 'logfile.log'
manager = Manager(loop=asyncio.get_event_loop(),
                  host=host,
                  username=username,
                  secret=passw)


@manager.register_event('Newstate')
def callback(event, manager):
    if "FullyBooted" not in manager.event:
        info = dict(manager)
        if (info.get('ChannelStateDesc') == 'Up') and (info.get('Context') == 'from-queue'):
            DATE = datetime.now()
            OperNum = str(info.get('Channel')).partition('/')[2][0:4]

            if len(info.get('ConnectedLineNum')) == 10:
                PhoneNum = '38' + info.get('ConnectedLineNum')
            elif len(info.get('ConnectedLineNum')) == 9:
                PhoneNum = '380' + info.get('ConnectedLineNum')
            else:
                PhoneNum = info.get('ConnectedLineNum')


            if len(info.get('CallerIDNum')) == 10:
                ExternalPhone = '38' + info.get('CallerIDNum')
            elif len(info.get('CallerIDNum')) == 9:
                ExternalPhone = '380' + info.get('CallerIDNum')
            elif info.get('CallerIDNum') == '7051033':
                ExternalPhone = '380487051033'
            elif info.get('CallerIDNum') == '7053333':
                ExternalPhone = '380487053333'
            else:
                ExternalPhone = info.get('CallerIDNum')



            param = (DATE, OperNum, PhoneNum, ExternalPhone, 'N')

            try:
                con = pymysql.connect(host=host2, user=user2, password=password2, db=db2, use_unicode=True,
                                      charset='utf8')
                cur = con.cursor()
                cur.execute("""INSERT  AMI_log (CALLDATE,  OperNum, PhoneNum, ExternalPhone, chek) VALUES (%s, %s, %s, %s, %s)""", param)
                con.commit()
            except Exception as E:
                f = open(LOG_FILE, 'a')
                f.write(str(datetime.now()) + ' === ' + "Couldn't connect" + ' === ' + str(E) + '\n')
                sleep(.1)
                f.close()
            finally:
                con.close()





def main():
    manager.connect()
    try:
        manager.loop.run_forever()
    except KeyboardInterrupt:
        manager.loop.close()


if __name__ == '__main__':
    main()