#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division
import os
import sys
import datetime
import ConfigParser
import logging

sys.path.append(sys.path[0] + os.sep + "lib")
from prettytable import PrettyTable

__author__ = 'L'
__version__ = "2.9"


def count(date, start_time, end_time):
    """
    统计ping信息并生成表格。
    :param date: 字符串，需要统计的日期，格式：--date=20160816。
    :param start_time: 字符串，统计开始的时间点，格式：--start_time=01:00:00。
    :param end_time:字符串，统计结束的时间点，格式：--end_time=09:00:00。
    :return:
    """
    logging.info("turn to read_config()")
    tag, name_list, ip_list, remark_list = read_config()
    table = PrettyTable(["Ping(%s)" % tag, "Total time(ms)", "Avg time(ms)", "Total icmp", "Loss icmp", "Loss percent(%)"])
    table.padding_width = 1

    for (i, n) in enumerate(name_list):
        total_time = 0.0
        total_count = 0
        loss_count = 0
        start_time_exist = False
        end_time_exist = False
        file_path = LOGS_PATH + os.sep + n + os.sep + n + "_" + date + ".log"
        if os.path.exists(file_path):
            logging.info("open file '%s', start count." % file_path)
            with open(file_path, "r") as log_file:
                for num, line in enumerate(log_file):
                    line_list = line.split(" ")
                    if len(line_list) == 4:
                        if line_list[1] == start_time:
                            start_time_exist = True
                        if line_list[1] == end_time:
                            end_time_exist = True
                        if start_time_exist:
                            total_count += 1
                            delay = line_list[3].rstrip()
                            if delay == "timeout":
                                loss_count += 1
                            else:
                                try:
                                    total_time += float(delay)
                                except ValueError:
                                    logging.error("File:'%s' line:%d Can not change 'delay' value(%s) from str to float." % (file_path, num, delay))
                                    sys.exit(3)
                        if end_time_exist:
                            break
                    else:
                        logging.error("File:'%s' line:%d data incomplete." % (file_path, num))
                        sys.exit(4)
                if start_time_exist and end_time_exist:
                    name = ip_list[i] + "(" + remark_list[i] + ")"
                    avg_time = total_time / total_count
                    loss_percent = loss_count / total_count * 100
                    table.add_row([name, format(total_time, ".1f"), format(avg_time, ".2f"), total_count, loss_count, format(loss_percent, ".2f")])
                elif not start_time_exist:
                    logging.error("HOST:'%s' IP:'%s' REMARK:'%s', start_time:'%s' not found." % (name_list[i], ip_list[i], remark_list[i], start_time))
                else:
                    logging.error("HOST:'%s' IP:'%s' REMARK:'%s', end_time:'%s' not found." % (name_list[i], ip_list[i], remark_list[i], end_time))
        else:
            logging.warning("File '%s' not found." % file_path)
    print(table)


def read_config():
    """
    读取配置文件，获取name_list、ip_list、remark_list。
    :return tag: 字符串类型，配置文件里主机标识信息。
    :return name_list: 字符串列表，配置文件里IP地址列表的名称。
    :return ip_list: 字符串列表，配置文件里IP地址列表。
    :return remark_list: 字符串列表，配置文件里remark列表。
    """
    tag = ""
    name_list = []
    ip_list = []
    remark_list = []
    config = ConfigParser.ConfigParser()

    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
        if len(config.sections()) > 0:
            for section in config.sections():
                if section == "Host_tag":
                    tag = config.get(section, "tag")
                elif section != "Logs":
                    name_list.append(section)
                    ip_list.append(config.get(section, "ip"))
                    remark_list.append(config.get(section, "remark"))
            return [tag, name_list, ip_list, remark_list]
    else:
        logging.error("Can not find the configuration file '%s'." % CONFIG_PATH)
        sys.exit(2)


def show_help():
    """
    显示帮助信息。
    :return:
    """
    print("Contrast version：v%s" % __version__)
    print("Usage: python contrast.py --date=20170511 --start_time=00:00:01 --end_time=09:00:00")


def main():
    """
    主程序入口，检查参数，启动统计函数。
    :return:
    """
    # 定义log级别CRITICAL,ERROR,WARNING,INFO,DEBUG，默认设置为WARNING
    log_format = "[%(asctime)s] [line:%(lineno)-3d] [%(levelname)-8s] %(message)s"
    logging.basicConfig(level=logging.WARNING, format=log_format, datefmt="%Y-%m-%d %H:%M:%S")
    logging.info("Start main()")

    global LOGS_PATH
    global CONFIG_PATH
    argv_date = ""
    argv_start_time = ""
    argv_end_time = ""
    root_path = sys.path[0]
    LOGS_PATH = root_path + os.sep + "logs"
    CONFIG_PATH = root_path + os.sep + "pings.conf"

    logging.info("judge arguments.")
    argument_len = len(sys.argv)
    if argument_len == 4:
        for i in range(1, argument_len):
            str1 = (sys.argv[i]).split("=")[0]
            str2 = (sys.argv[i]).split("=")[1]
            if str1 == "--date":
                argv_date = str2
            if str1 == "--start_time":
                argv_start_time = str2
            if str1 == "--end_time":
                argv_end_time = str2
        if argv_date != "" and argv_start_time != "" and argv_end_time != "":
            try:
                start = datetime.datetime.strptime(argv_start_time, "%X").time()
            except ValueError:
                logging.error("Argument 'start_time' value error.")
                sys.exit(1)
            try:
                end = datetime.datetime.strptime(argv_end_time, "%X").time()
            except ValueError:
                logging.error("Argument 'end_time' value error.")
                sys.exit(1)
            start_seconds = start.hour * 3600 + start.minute * 60 + start.second
            end_seconds = end.hour * 3600 + end.minute * 60 + end.second
            if end_seconds - start_seconds > 0:
                logging.info("Turn to count()")
                count(argv_date, argv_start_time, argv_end_time)
            else:
                logging.error("'start_time' bigger than 'end_time'.")
        else:
            logging.error("'date' or 'start_time' or 'end_time' can not be empty.")
            show_help()
    elif argument_len == 2:
        if sys.argv[1] == "--help":
            show_help()
    elif argument_len == 1:
        show_help()
    else:
        logging.error("Need 3 arguments.")
        show_help()


if __name__ == "__main__":
    main()
