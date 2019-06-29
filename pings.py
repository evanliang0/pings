#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import os
import ConfigParser
import datetime
import multiprocessing
import sys
import platform
import logging

sys.path.append(sys.path[0] + os.sep + "lib")
import ping
import prctl

__author__ = "L"
__version__ = "2.10"


def global_init():
    """
    定义主进程全局常量和logging配置。
    :return:
    """
    global ROOT_PATH
    global LOGS_PATH
    global CONFIG_PATH
    global MAIN_LOG_PATH
    global PID_PATH
    ROOT_PATH = sys.path[0]
    LOGS_PATH = ROOT_PATH + os.sep + "logs"
    CONFIG_PATH = ROOT_PATH + os.sep + "pings.conf"
    MAIN_LOG_PATH = ROOT_PATH + os.sep + "pings.log"
    PID_PATH = ROOT_PATH + os.sep + "pings.pid"

    log_format = "[%(asctime)s] [line:%(lineno)-3d] [%(levelname)-8s] %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt="%Y-%m-%d %H:%M:%S", filename=MAIN_LOG_PATH)


def read_config():
    """
    读取配置文件信息，判断配置是否合法，并返回配置信息。
    :return flag：布尔型，True表示配置文件合法，False表示配置文件不合法。
    :return cycle：整形，logs目录里面各个子目录下的*.log文件保存的周期。
    :return name_list：字符串列表，表示配置文件里面所有IP地址列表的名称。
    :return ip_list: 字符串列表，配置文件里名称对应的IP列表。
    :return remark_list: 字符串列表，配置文件里名称对应的remark列表。
    """
    flag = False
    cycle = 7
    name_list = []
    ip_list = []
    remark_list = []

    config = ConfigParser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
        if len(config.sections()) > 0:
            for section in config.sections():
                if section != "Host_tag":
                    option_count = len(config.options(section))
                    if section == "Logs" and option_count == 1:
                        cycle = config.get("Logs", "clean_cycle")
                    elif section != "Logs" and option_count == 2:
                        name_list.append(section)
                        ip_list.append(config.get(section, "ip"))
                        remark_list.append(config.get(section, "remark"))
            if len(name_list) == 0 or ip_list == 0 or remark_list == 0:
                return [flag, cycle, name_list, ip_list, remark_list]
            else:
                flag = True
                return [flag, cycle, name_list, ip_list, remark_list]
        else:
            return [flag, cycle, name_list, ip_list, remark_list]
    else:
        return [flag, cycle, name_list, ip_list, remark_list]


def check_logs_path(name_list):
    """
    判断logs文件夹是否存在。
    :param name_list：字符串列表，表示配置文件里面所有IP地址列表的名称。
    :return :flag：布尔型，True表示成功创建logs目录和对应的子目录，False表示失败。
    """
    if os.path.exists(LOGS_PATH):
        for name in name_list:
            logs_name_path = LOGS_PATH + os.sep + name
            if not os.path.exists(logs_name_path):
                os.mkdir(logs_name_path)
        flag = True
    else:
        os.mkdir(LOGS_PATH)
        for name in name_list:
            logs_name_path = LOGS_PATH + os.sep + name
            os.mkdir(logs_name_path)
        flag = True
    return flag


def ping_write_log(name, dst_ip, ppid):
    """
    子进程函数，ping目标IP，并写入log文件，log文件为  名称_日期.log，例如：test1_20160815.log。
    :param name：字符串，配置文件里IP地址列表的名称。
    :param dst_ip：字符串，需要ping的目标IP地址。
    :param ppid: 字符串，父进程的PID。
    :return:
    """
    first_day = datetime.datetime.now().date()
    prctl.set_proctitle("ping " + name)
    while True:
        if check_pid(ppid):
            day_temp = datetime.datetime.now().date()
            log_path = LOGS_PATH + os.sep + name + os.sep + name + "_" + datetime.datetime.now().strftime("%Y%m%d") + ".log"
            with open(log_path, mode="a") as log_file:
                before = datetime.datetime.now()
                while first_day == day_temp:
                    if check_pid(ppid):
                        after = datetime.datetime.now()
                        if (after.hour * 3600 + after.minute * 60 + after.second) > (before.hour * 3600 + before.minute * 60 + before.second):
                            time_str = after.strftime("%Y-%m-%d %X")
                            delay = ping.do_one(dst_ip, timeout=0.7, psize=64)
                            if delay is None or delay > 4.0:
                                if os.path.exists(log_path):
                                    log_file.write(time_str + " " + dst_ip + " timeout\n")
                                    log_file.flush()
                                else:
                                    break
                            else:
                                delay_ms = delay * 1000
                                if os.path.exists(log_path):
                                    log_file.write(time_str + " " + dst_ip + " " + str(format(delay_ms, ".1f")) + "\n")
                                    log_file.flush()
                                else:
                                    break
                            before = datetime.datetime.now()
                        else:
                            before = datetime.datetime.now()
                            time.sleep(0.1)
                        day_temp = datetime.datetime.now().date()
                    else:
                        logging.info("Main process exit.")
                        logging.info("Subprocess exit. PPID:%s, PID:%s, HOST:%s, IP:%s" % (ppid, os.getpid(), name, dst_ip))
                        return
            if day_temp >= first_day:
                first_day = day_temp
            else:
                logging.error("Wrong date. Subprocess exit. PPID:%s, PID:%s, HOST:%s, IP:%s" % (ppid, os.getpid(), name, dst_ip))
                return
        else:
            logging.info("Main process exit.")
            logging.info("Subprocess exit. PPID:%s, PID:%s, HOST:%s, IP:%s" % (ppid, os.getpid(), name, dst_ip))
            return


def create_pid_file(name_list, ppid, process_list):
    """
    生成pings.pid文件，pid文件里面第一行是主进程的PID，后面是子进程对应的PID，匹配配置文件里的IP名称列表。
    :param name_list: 字符串列表，主机名列表。
    :param ppid: 字符串列表，主进程的PID。
    :param process_list: 字符串列表，启动的子进程对象。
    :return:
    """
    logging.info("Write pid file.")
    with open(PID_PATH, mode="w") as pid_file:
        pid_file.write(ppid + " PPID" + "\n")
        for i in range(0, len(process_list)):
            pid_str = str(process_list[i].pid) + " " + name_list[i] + "\n"
            pid_file.write(pid_str)


def clean_log(cycle, name_list):
    """
    定期清除log文件
    :param cycle: 整型，保存多少天的log。
    :param name_list: 字符串列表，主机名称列表。
    :return:
    """
    date_file = ""
    clean_cycle = datetime.timedelta(days=int(cycle))
    date_now = datetime.datetime.now().date()
    for n in name_list:
        log = LOGS_PATH + os.sep + n
        for f in os.listdir(log):
            if f[-3:] == "log":
                log_date = f[-12:-4]
                try:
                    date_file = datetime.datetime.strptime(log_date, "%Y%m%d").date()
                except ValueError:
                    logging.warning("Can not change the logs file name('%s') form str to datetime." % f)
                if date_now - date_file >= clean_cycle:
                    os.remove(log + os.sep + f)


def background():
    """
    后台启动主进程函数。
    :return:
    """
    logging.debug("Turn to check_process().")
    if not check_process():
        logging.info("Main process start.")
        logging.debug("Turn to read_config().")
        config_flag, cycle, name_list, ip_list, remark_list = read_config()
        logging.info("Check config.")
        if config_flag:
            print("[INFO] Program start.")
            logging.info("Check config OK.")
            logging.debug("Turn to daemonize().")
            # daemonize('/dev/null', '/tmp/daemon_stdout.log', '/tmp/daemon_error.log')
            daemonize()
            logging.debug("Turn to start_process().")
            start_process(cycle, name_list, ip_list)
        else:
            logging.error("Config file '%s' read error. Main process stop." % CONFIG_PATH)
            print("[ERROR] Config file '%s' read error. Program exit." % CONFIG_PATH)
    else:
        print("[ERROR] Program is running. Please do not run the program repeatedly.")


def start_process(cycle, name_list, ip_list):
    """
    启动子进程，执行主进程循环，清理过期日志文件。
    :param cycle: 整型，保存多少天的log。
    :param name_list: 字符串列表，主机名称列表。
    :param ip_list: 字符串列表，IP地址列表。
    :return:
    """
    process_list = []

    logging.info("Check logs directory structure.")
    logging.debug("Turn to check_logs_path().")
    if check_logs_path(name_list):
        logging.info("Check logs directory structure OK.")
        logging.info("Begin to start subprocess.")
        ppid = str(os.getpid())
        for (i, n) in enumerate(name_list):
            process = multiprocessing.Process(name=n, target=ping_write_log, args=(n, ip_list[i], ppid))
            process.daemon = True
            process.start()
            logging.info("Start subprocess, PPID:%s, PID:%s, HOST:%s, IP:%s." % (ppid, str(process.pid), n, ip_list[i]))
            process_list.append(process)

        logging.debug("Turn to create_pid_file().")
        create_pid_file(name_list, ppid, process_list)

        first_day = datetime.datetime.now().date()
        prctl.set_proctitle(prctl.get_name() + " " + sys.argv[0] + " -d")
        logging.info("Main process run loop task.")
        while True:
            day_temp = datetime.datetime.now().date()
            if day_temp > first_day:
                first_day = day_temp
                logging.info("Clean expired logs.")
                clean_log(cycle, name_list)
                logging.info("Clean expired logs OK.")
            else:
                time.sleep(3600)
    else:
        logging.error("Check logs directory structure error. Program exit.")


def stop_process():
    """
    停止主进程。
    :return:
    """
    logging.info("Stopping main process.")
    logging.info("Check PID file.")
    if os.path.exists(PID_PATH):
        with open(PID_PATH, mode="r") as pid_file:
            line = pid_file.readline()
            l = line[:-1].split(" ")
            logging.debug("Turn to check_pid().")
            if check_pid(l[0]):
                print("[INFO] Program stop.")
                os.kill(int(l[0]), 15)
                logging.info("Main process stopped.")
            else:
                logging.info("Main process not found. Program exit.")
    else:
        logging.info("Pid file 'pings.pid' not found. Program exit.")


def check_pid(pid):
    """
    检查进程PID，判断进程是否存在。
    :param pid: 字符串，进程的PID。
    :return: 布尔值，True为进程存在，False为进程不存在。
    """
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    else:
        return True


def check_process():
    """
    检查主进程是否存在。
    :return: 布尔值
    """
    logging.info("Check main process.")
    if os.path.exists(PID_PATH):
        with open(PID_PATH, mode="r") as pid_file:
            line = pid_file.readline()
            l = line[:-1].split(" ")
            return check_pid(l[0])
    else:
        return False


def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    """
    守护进程函数。
    :param stdin: 字符串，重定向标准文件描述符。
    :param stdout: 字符串，重定向标准文件描述符。
    :param stderr: 字符串，重定向标准文件描述符。
    :return:
    """
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.exit(1)

    os.chdir("/")
    os.umask(022)
    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.exit(1)

    for f in sys.stdout, sys.stderr:
        f.flush()
    si = open(stdin, 'r')
    so = open(stdout, 'a+')
    se = open(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


def usage():
    """
    打印使用方法。
    :return:
    """
    print("Pings version：v%s" % __version__)
    print("Usage: python pings.py [-d|-s|-r]")
    print("Options:")
    print("     -d: run in daemon mode.")
    print("     -s: stop the program.")
    print("     -r: restart the program.")


def main():
    """
    程序入口。
    :return:
    """
    global_init()

    if platform.system() == "Linux":
        if len(sys.argv) == 1:
            usage()
        elif len(sys.argv) == 2:
            if sys.argv[1] == "-s":
                logging.debug("Turn to stop_process().")
                stop_process()
            elif sys.argv[1] == "-r":
                logging.debug("Turn to stop_process().")
                stop_process()
                time.sleep(1)
                logging.debug("Turn to background().")
                background()
            elif sys.argv[1] == "-d":
                logging.debug("Turn to background().")
                background()
            elif sys.argv[1] == "--help":
                usage()
            else:
                print("[ERROR] Wrong argument.")
                usage()
        else:
            print("[ERROR] Wrong argument.")
            usage()
    else:
        print("[ERROR] This program only for linux.")

if __name__ == "__main__":
    main()
