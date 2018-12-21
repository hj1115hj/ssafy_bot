# -*- coding: utf-8 -*-
import json
import os
import re
import urllib.request
from selenium import webdriver
import time
import re

import multiprocessing as mp
from threading import Thread

from bs4 import BeautifulSoup
from slackclient import SlackClient
from flask import Flask, request, make_response, render_template

app = Flask(__name__)

slack_token = "xoxb-507428687235-508484995299-rjpy6Qf6dB6xXcuwvQmKmswa"  # 자신의 토큰 값을 입력해줍니다.
slack_client_id = "507428687235.509990628982"  # client_id 값을 입력합니다
slack_client_secret = "507428687235.509990628982"  # client_secret 값을 입력합니다
slack_verification = "y0uuyFCYToJRvjbfqLnpzdC9"  # verification 값을 입력합니다.
sc = SlackClient(slack_token)

# 크롤링 함수 구현하기

url = ""
step = 1
item = ""


def _11(search_url, item_name, sort):
    # 여기에 함수를 구현해봅시다.
    chrome_path = 'C:\\Users\\student\\Downloads\\chromedriver_win32\\chromedriver.exe'
    driver = webdriver.Chrome(chrome_path)
    driver.implicitly_wait(2)
    ## url에 접근한다.
    driver.get(search_url)
    ## 아이디/비밀번호를 입력해준다.

    print(item_name)

    driver.find_element_by_name('kwd').send_keys(item_name)
    driver.find_element_by_xpath('//*[@id="gnbTxtAd"]').click()
    time.sleep(2)  # 5초 대기
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    item_list = soup.find_all("div", class_="total_listitem")

    items_list = []
    sort_list = []
    for item in item_list:
        item_dict = {}
        title = item.find("p", class_="info_tit").get_text().strip()

        price = item.find("strong", class_="sale_price").get_text().strip().replace(",", "")
        price = int(re.findall('\d+', price)[0])
        # selr_star selr_star90

        try:
            review = item.find("a", class_="review").get_text().strip().replace(",", "")
            review = int(re.findall('\d+', review)[0])
        except:
            rev = 0

        try:
            score = item.find_all('span', {'class': re.compile(r'selr_star.*')})[0].get_text().strip()
            score = float(re.findall('\d.\d', score)[0])
        except:
            score = 0

        item_dict['title'] = str(title)
        item_dict['price'] = price
        item_dict['review'] = int(review)
        item_dict['score'] = score
        sort_list.append(item_dict)
    # 리뷰
    if sort == "리뷰":
        sort_list.sort(key=lambda x: (x['review']), reverse=True)
    # 가격
    elif sort == "가격":
        sort_list.sort(key=lambda x: (x['price']))
    # 평점
    elif sort == "평점":
        sort_list.sort(key=lambda x: (x['score']), reverse=True)

    items_list = sort_list[:10]
    # for i in range(0, 10):
    #     items_list[i] = str(items_list[i]).replace("title", str(i + 1))
    # items_list = str(items_list).replace('["{', "").replace('}"]', "").replace('}", "{', "\n").replace("'", "")

    result_list = []
    for idx, val in enumerate(items_list):
        result = str(idx + 1) + "위," + " 이름:" + str(val['title']) + " 가격:" + str(val['price']) + "원" + " 리뷰:" + str(
            val['review']) + " 평점:" + str(val['score'])
        result_list.append(result)

    # 한글 지원을 위해 앞에 unicode u를 붙혀준다.
    print(result_list)
    return result_list


def _crawl_naver_keywords(text):
    # 여기에 함수를 구현해봅시다.

    text = text.split()[1]

    global url
    global step
    global item
    print(text)
    if text == '11번가' and step == 1:
        print(step)
        url = "http://www.11st.co.kr"
        keywords = ["11번가에 접속하였습니다. 검색할 상품을 입력해주세요"]
        step = step + 1
    elif step == 2:
        print(step)
        item = text
        keywords = ['리뷰,평점,가격 중 어느 기준으로 정렬하시겠습니까?']
        step = step +1
    elif step == 3:
        sort = text
        search_url = url
        keywords = _11(search_url, item, sort)
        step=1

    # 한글 지원을 위해 앞에 unicode u를 붙힙니다.

    return u'\n'.join(keywords)


# threading function
def processing_event(queue):
    while True:
        if not queue.empty():
            slack_event = queue.get()

            channel = slack_event["event"]["channel"]
            text = slack_event["event"]["text"]

            keywords = _crawl_naver_keywords(text)

            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text=keywords
            )


# 이벤트 핸들하는 함수
def _event_handler(event_type, slack_event):
    if event_type == "app_mention":
        event_queue.put(slack_event)
        return make_response("App mention message has been sent", 200, )

    # ============= Event Type Not Found! ============= #
    # If the event_type does not have a handler
    message = "You have not added an event handler for the %s" % event_type
    # Return a helpful error message
    return make_response(message, 200, {"X-Slack-No-Retry": 1})


@app.route("/listening", methods=["GET", "POST"])
def hears():
    slack_event = json.loads(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                                 "application/json"
                                                             })

    if slack_verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s" % (slack_event["token"])
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return _event_handler(event_type, slack_event)

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})


@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"


if __name__ == '__main__':
    event_queue = mp.Queue()

    p = Thread(target=processing_event, args=(event_queue,))
    p.start()

    app.run('0.0.0.0', port=8080)
    p.join()