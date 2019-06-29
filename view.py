#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import datetime
import os
import logging

__author__ = 'L'
__version__ = "1.0"


def show_help():
    """
    显示帮助信息。
    :return:
    """
    print("View version v%s" % __version__)
    print("Usage: python view.py --host=test1 --date=20170512 --start_time=00:00:01 --end_time=01:00:00")


def view_log(host, date, start_time, end_time):
    start_flag = False
    end_flag = False
    start = datetime.datetime.strptime(start_time, "%X")
    end = datetime.datetime.strptime(end_time, "%X")

    host_dir = LOGS_PATH + os.sep + host
    if os.path.exists(host_dir):
        log_file = host_dir + os.sep + host + "_" + date + ".log"
        if os.path.exists(log_file):
            if end > start:
                with open(log_file, "r") as log_f:
                    for num, line in enumerate(log_f):
                        line_list = line.split()
                        if len(line_list) == 4:
                            try:
                                time_temp = datetime.datetime.strptime(line_list[1], "%X")
                            except ValueError:
                                logging.error("line:%d, Can not change time '%s' form string to datetime." % (num, line_list[1]))
                            if time_temp == start:
                                start_flag = True
                            if time_temp >= end:
                                end_flag = True
                            if start_flag:
                                print(line.rstrip())
                                if end_flag:
                                    break
                if not start_flag:
                    logging.error("Can not found 'start_time'.")
            else:
                logging.error("'start_time' bigger than 'end_time'.")
        else:
            logging.error("Can not found file '%s'." % log_file)
    else:
        logging.error("Can not found the host '%s'" % host)


def main():
    global LOGS_PATH
    global CONFIG_PATH
    LOGS_PATH = sys.path[0] + os.sep + "logs"
    CONFIG_PATH = sys.path[0] + os.sep + "pings.conf"

    argv_host = ""
    argv_date = ""
    argv_start_time = ""
    argv_end_time = ""

    log_format = "[%(asctime)s] [line:%(lineno)-3d] [%(levelname)-8s] %(message)s"
    logging.basicConfig(level=logging.WARNING, format=log_format, datefmt="%Y-%m-%d %H:%M:%S")
    logging.info("Start main()")

    argument_len = len(sys.argv)
    if argument_len == 5:
        for i in range(1, argument_len):
            str1 = (sys.argv[i]).split("=")[0]
            str2 = (sys.argv[i]).split("=")[1]
            if str1 == "--host":
                argv_host = str2
            if str1 == "--date":
                argv_date = str2
            if str1 == "--start_time":
                argv_start_time = str2
            if str1 == "--end_time":
                argv_end_time = str2
        if argv_host != "" and argv_date != "" and argv_start_time != "" and argv_end_time != "":
            try:
                datetime.datetime.strptime(argv_date, "%Y%m%d").date()
            except ValueError:
                logging.error("Argument 'date' value error.")
                sys.exit(1)
            try:
                datetime.datetime.strptime(argv_start_time, "%X").time()
            except ValueError:
                logging.error("Argument 'start_time' value error.")
                sys.exit(1)
            try:
                datetime.datetime.strptime(argv_end_time, "%X").time()
            except ValueError:
                logging.error("Argument 'end_time' value error.")
                sys.exit(1)
            # argv_host = "test1"
            # argv_date = "20170511"
            # argv_start_time = "18:30:00"
            # argv_end_time = "18:30:15"
            view_log(argv_host, argv_date, argv_start_time, argv_end_time)
    elif argument_len == 2:
        if sys.argv[1] == "--help":
            show_help()
        else:
            logging.error("Need 4 arguments.")
            show_help()
    else:
        logging.error("Need 4 arguments.")
        show_help()


if __name__ == "__main__":
    main()
