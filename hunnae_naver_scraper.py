from bs4 import BeautifulSoup
import pickle
from datetime import date, datetime, timedelta
import sys, os, glob
import requests, urllib.request, urllib.parse
import csv, re, time, math
import numpy as np, pandas as pd
import json
from itertools import chain
from tqdm import tqdm

def textfile_reader(x, encodingtype='utf-8') :
    with open(x, 'r', encoding=encodingtype) as f:
        lines = f.readlines()
        output = [line for line in lines]
    return output  

def textfile_writer(objecttosave, filename, encodingtype='utf-8') :
    with open(filename, 'w', encoding) as f:
        for each_sentence in objecttosave:
            f.write(f'{each_sentence}\n')     

def pickle_reader(filename) :
    with open(filename, 'rb') as f :
        output_df = pickle.load(f)
    return output_df

def pickle_writer(objecttosave, filename) :
    with open(filename, 'wb') as f :
        pickle.dump(objecttosave, f, protocol=4)

basic_header = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5)\AppleWebKit 537.36 (KHTML, like Gecko) Chrome',
                'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'}

client_id = 'RCDsq39IfMLOReExsL9E'
client_secret = 'bmQ34fmVmz'

naverapi_header = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36',
                   'X-Naver-Client-Id':client_id,
                   'X-Naver-Client-Secret':client_secret}

def basic_naverjson_cleaner(input_soup_text) :
    input_soup_text = input_soup_text.replace('_callback', '')
    input_soup_text = input_soup_text.replace('\\(', '')
    input_soup_text = input_soup_text.replace('\\)', '')
    input_soup_text = input_soup_text.replace(';', '')
    input_soup_text = input_soup_text.replace('\n', '')
    input_soup_text = input_soup_text.replace('\'','')
    input_soup_text = input_soup_text.replace('\\"', '')
    input_soup_text = input_soup_text.replace('\\,"', '\",\"')
    input_soup_text = input_soup_text.replace('\\','')
    input_soup_text = input_soup_text[1:-1]
    return input_soup_text

def dirty_naverjson_cleaner(input_text, starting_str, closing_str) :
    output_list = []
    for index, each_quotechunk in enumerate(input_text.split(starting_str)) :
        catchunk = each_quotechunk.split(closing_str)
        if index==0 or '"' not in catchunk[0] :
            output_list.append(each_quotechunk)
        else :
            output_list.append(closing_str.join([catchunk[0].replace('"',''), catchunk[1]]))
    final_output = starting_str.join(output_list)
    return final_output

def json_web_cleaner(input_req_or_soup) :
    input_text = input_req_or_soup.text
    input_text = basic_naverjson_cleaner(input_text)
    try :
        output_comment_json = json.loads(input_text)
    except :
        input_text = dirty_naverjson_cleaner(input_text,
                                             'objectSource\":\"',
                                             '\",\"objectCat')
        input_text = dirty_naverjson_cleaner(input_text,
                                             'source\":\"',
                                             '\",\"url')
        input_text = dirty_naverjson_cleaner(input_text,
                                             'contents\":\"',
                                             '\",\"userIdNo')
        output_comment_json = json.loads(input_text)
    return output_comment_json

def naver_entertainnews_scraper(url) :
    session = requests.Session()
    req = session.get(url, headers=basic_header)
    soup = BeautifulSoup(req.text, 'lxml')
   
    oid = re.findall(r'\d+', url.split('oid')[1])[0]
    aid = re.findall(r'\d+', url.split('aid')[1])[0]
    
    category = '연예'
    press = soup.find('div', attrs={'class':'press_logo'}).a.img['alt']

    predate = soup.find('span', attrs={'class':'author'}).em.text.split()
    if predate[1]=='오전' or int(predate[2].split(':')[0])==12 :
        time = predate[2] 
    else :
        time = str(int(predate[2].split(':')[0])+12) + ':' + predate[2].split(':')[1]
    date = pd.to_datetime(''.join(predate[0].split('.')) + ' ' + time)

    title = ' '.join(soup.find('h2', attrs={'class':'end_tit'}).text.split())
    img_list = list(map(lambda x : x['src'], soup.find('div', attrs={'class':'article_body'}).find_all('img')))

    prebody = soup.find('div', attrs={'class':'end_body_wrp'})
    try :
        for each_imgdesc in prebody.find_all('em', attrs={'class':'img_desc'}) :
            each_imgdesc.decompose()
        for each_endnote in prebody.find_all('a', attrs={'target':'_blank'}) :
            each_endnote.decompose()
    except :
        pass
    try :
        summary = prebody.find('strong', attrs={'class':'media_end_summary'}).get_text(separator=' ')
    except :
        summary = None
    
    try :
        prebody.find('script', attrs={'type':'text/javascript'}).decompose()
    except :
        pass
    
    try :
        for each_strong in prebody.find_all('strong', attrs={'class':'media_end_summary'}) :
            each_strong.decompose()
    except :
        pass
    try :
        for each_a in prebody.find_all('a') :
            each_a.decompose()
    except :
        pass
    
    body = ' '.join(prebody.text.split())
    numcomment = None
    
    return dict(zip(['oid', 'aid', 'title', 'date', 'summary', 'body', 'category', 'press', 'numcomment'], 
                    [oid, aid, title, date, summary, body, category, press, numcomment]))

def naver_sportsnews_scraper(url) :
    session = requests.Session()
    req = session.get(url, headers=basic_header)
    soup = BeautifulSoup(req.text, 'lxml')
    
    oid = re.findall(r'\d+', url.split('oid')[1])[0]
    aid = re.findall(r'\d+', url.split('aid')[1])[0]
    
    category = '스포츠'
    press = ' '.join(soup.find('span', attrs={'class':'logo'}).a.img['alt'].split())

    predate = soup.find('div', attrs={'class':'info'}).text.split()
    if predate[2]=='오전' or int(predate[3].split(':')[0])==12 :
        time = predate[3] 
    else :
        time = str(int(predate[3].split(':')[0])+12) + ':' + predate[3].split(':')[1]
    date = pd.to_datetime(''.join(predate[1].split('.')) + ' ' + time)

    title = soup.find('h4', attrs={'class':'title'}).text
    pre_img_list = soup.find_all('span', attrs={'class':'end_photo_org'})
    img_list = [each_img.img['src'] for each_img in pre_img_list]

    prebody = soup.find('div', attrs={'class':'news_end'})
    try :
        for each_imgdesc in prebody.find_all('em', attrs={'class':'img_desc'}) :
            each_imgdesc.decompose()
        for each_endnote in prebody.find_all('a', attrs={'target':'_blank'}) :
            each_endnote.decompose()
    except :
        pass
    try :
        summary = prebody.find('strong', attrs={'class':'media_end_summary'}).get_text(separator=' ')
    except :
        summary = None
    
    try :
        prebody.find('script', attrs={'type':'text/javascript'}).decompose()
    except :
        pass
    try :
        for each_strong in prebody.find_all('strong', attrs={'class':'media_end_summary'}) :
            each_strong.decompose()
    except :
        pass
    try :
        for each_a in prebody.find_all('a') :
            each_a.decompose()
    except :
        pass
    

    body = ' '.join(prebody.text.split())
    
    comment_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json?ticket=sports&templateId=view&pool=cbox2&lang=ko&country=KR&objectId=news{oid}%2C{aid}&pageSize=20&indexSize=10&groupId=&listType=OBJECT&pageType=more&page=1&refresh=true&sort=old'
    basic_header.update({'Referer':url})

    comment_req = session.get(comment_url, headers=basic_header)
    comment_soup = BeautifulSoup(comment_req.text, 'lxml')
    comment_json = json_web_cleaner(comment_soup)
    numcomment = comment_json['result']['pageModel']['totalRows']

    return dict(zip(['oid', 'aid', 'title', 'date', 'summary', 'body', 'category', 'press', 'numcomment'], 
                    [oid, aid, title, date, summary, body, category, press, numcomment]))

def naver_news_scraper(url) :
    session = requests.Session()
    req = session.get(url, headers=basic_header)
    soup = BeautifulSoup(req.text, 'lxml')
    
    oid = re.findall(r'\d+', url.split('oid')[1])[0]
    aid = re.findall(r'\d+', url.split('aid')[1])[0]
    
    try :
        category = soup.find('em', attrs={'class':'guide_categorization_item'}).text
    except :
        category = soup.find('li', attrs={'class':'on'}).text.split()[0]
    press = soup.find('div', attrs={'class':'press_logo'}).a.img['alt']

    predate = soup.find('span', attrs={'class':'t11'}).text.split()
    if predate[1]=='오전' or int(predate[2].split(':')[0])==12 :
        time = predate[2] 
    else :
        time = str(int(predate[2].split(':')[0])+12) + ':' + predate[2].split(':')[1]

    date = pd.to_datetime(''.join(predate[0].split('.')) + ' ' + time)

    title = soup.find('h3', attrs={'id':'articleTitle'}).text
    img_list = list(map(lambda x : x['src'], soup.find('div', attrs={'class':'article_body'}).find_all('img')))

    prebody = soup.find('div', attrs={'id':'articleBodyContents'})
    try :
        summary = prebody.find('strong', attrs={'class':'media_end_summary'}).get_text(separator=' ')
    except :
        summary = None

    prebody.find('script', attrs={'type':'text/javascript'}).decompose()
    try :
        for each_strong in prebody.find_all('strong', attrs={'class':'media_end_summary'}) :
            each_strong.decompose()
    except :
        pass
    try :
        for each_a in prebody.find_all('a') :
            each_a.decompose()
    except :
        pass

    body = ' '.join(prebody.get_text(separator= ' ').split())
    
    comment_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json?ticket=news&templateid=default_politics&pool=cbox5&lang=ko&country=KR&objectId=news{oid}%2C{aid}&pageSize=100&indexSize=10&groupId=&page=1&initialize=true&useAltSort=true&replyPageSize=30&moveTo=&sort=old'
    basic_header.update({'Referer':url})

    comment_req = session.get(comment_url, headers=basic_header)
    comment_soup = BeautifulSoup(comment_req.text, 'lxml')
    comment_json = json_web_cleaner(comment_soup)
    numcomment = comment_json['result']['pageModel']['totalRows']

    return dict(zip(['oid', 'aid', 'title', 'date', 'summary', 'body', 'category', 'press', 'numcomment'], 
                    [oid, aid, title, date, summary, body, category, press, numcomment]))

def naver_commentlist_scraper(url) :
    session = requests.Session()
    req = session.get(url, headers=basic_header)
    soup = BeautifulSoup(req.text, 'lxml')

    oid = re.findall(r'\d+', url.split('oid')[1])[0]
    aid = re.findall(r'\d+', url.split('aid')[1])[0]

    page = 1
    comment_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json?ticket=news&templateid=default_politics&pool=cbox5&lang=ko&country=KR&objectId=news{oid}%2C{aid}&pageSize=100&indexSize=10&groupId=&page=1&initialize=true&useAltSort=true&replyPageSize=30&moveTo=&sort=old'
    basic_header.update({'Referer':url})

    comment_req = session.get(comment_url, headers=basic_header)
    comment_soup = BeautifulSoup(comment_req.text, 'lxml')
    comment_json = json_web_cleaner(comment_soup)
    numCommentPage = math.ceil(comment_json['result']['pageModel']['totalRows']/100)

    basicinfo = comment_json['result']['count']
    try :
        demographicinfo = comment_json['result']['graph']
    except :
        demographicinfo = None

    if numCommentPage==1 :
        list_comment_json = comment_json['result']['commentList']
    else :
        list_comment_json = []
        for page in range(1, numCommentPage+1) :
            comment_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json?ticket=news&templateid=default_politics&pool=cbox5&lang=ko&country=KR&objectId=news{oid}%2C{aid}&pageSize=100&indexSize=10&groupId=&page={page}&initialize=true&useAltSort=true&replyPageSize=30&moveTo=&sort=old'
            comment_req = session.get(comment_url, headers=basic_header)
            comment_json = json_web_cleaner(comment_req)
            list_comment_json.extend(comment_json['result']['commentList'])

    return list_comment_json

def naver_childcommentlist_scraper(url, list_comment_json) :
    session = requests.Session()
    req = session.get(url, headers=basic_header)
    soup = BeautifulSoup(req.text, 'lxml')

    oid = re.findall(r'\d+', url.split('oid')[1])[0]
    aid = re.findall(r'\d+', url.split('aid')[1])[0]
    
    list_parentCommentNo_with_childComment = []
    for each_comment in list_comment_json : 
        if each_comment['replyCount']>0 :
            parentCommentNo = each_comment['parentCommentNo']
            list_parentCommentNo_with_childComment.append(parentCommentNo)

    list_childcomment_json = []
    for parentCommentNo in list_parentCommentNo_with_childComment :
        page = 1
        childcomment_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json?ticket=news&templateid=default_politics&pool=cbox5&lang=ko&country=KR&objectId=news{oid}%2C{aid}&pageSize=100&indexSize=10&groupId=&page={page}&parentCommentNo={parentCommentNo}&initialize=true&useAltSort=true&replyPageSize=30&moveTo=&sort=old'
        childcomment_req = session.get(childcomment_url, headers=basic_header)
        childcomment_json = json_web_cleaner(childcomment_req)
        numChildCommentPage = math.ceil(childcomment_json['result']['pageModel']['totalRows']/100)

        if numChildCommentPage==1 :
            prelist_childcomment_json = childcomment_json['result']['commentList']
        else :
            prelist_childcomment_json = []
            for page in range(1, numChildCommentPage+1) :
                childcomment_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json?ticket=news&templateid=default_politics&pool=cbox5&lang=ko&country=KR&objectId=news{oid}%2C{aid}&pageSize=100&indexSize=10&groupId=&page={page}&initialize=true&useAltSort=true&replyPageSize=30&moveTo=&sort=old'
                childcomment_req = session.get(childcomment_url, headers=basic_header)
                childcomment_soup = BeautifulSoup(childcomment_req.text, 'lxml')
                childcomment_json = json_web_cleaner(childcomment_soup)
                prelist_childcomment_json.extend(comment_json['result']['commentList'])
        list_childcomment_json.extend(prelist_childcomment_json)
        
    return list_childcomment_json

def naver_idhistory_scraper(news_url, commentNo) :
    oid = re.findall(r'\d+', news_url.split('oid')[1])[0]
    aid = re.findall(r'\d+', news_url.split('aid')[1])[0]
    
    page = 1
    idhistory_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_per_user_jsonp.json?ticket=news&templateId=default_world&pool=cbox5&lang=ko&country=KR&objectId=news{oid}%2C{aid}&categoryId=&pageSize=100&indexSize=10&groupId=&listType=user&pageType=more&page={page}&sort=old&commentNo={commentNo}'
    basic_header.update({'Referer':news_url})

    session = requests.Session()
    idhistory_req = session.get(idhistory_url, headers=basic_header)
    idhistory_json = json_web_cleaner(idhistory_req)

    numHistoryPage = math.ceil(idhistory_json['result']['pageModel']['totalRows']/100)
    if numHistoryPage==1 :
        list_history_json = idhistory_json['result']['commentList']
    else :
        list_history_json = []
        for page in range(1, numHistoryPage+1) :
            idhistory_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_per_user_jsonp.json?ticket=news&templateId=default_world&pool=cbox5&lang=ko&country=KR&objectId=news{oid}%2C{aid}&categoryId=&pageSize=100&indexSize=10&groupId=&listType=user&pageType=more&page={page}&sort=old&commentNo={commentNo}'
            idhistory_req = session.get(idhistory_url, headers=basic_header)
            idhistory_json = json_web_cleaner(idhistory_req)
            list_history_json.extend(idhistory_json['result']['commentList'])
    return list_history_json

def old_naver_idhistory_scraper(comment_url, commentNo) :
    oid, aid = re.findall(r'objectId=news(.*?)&pageSize=', comment_url)[0].split('%2C')
    page = 1
    idhistory_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_per_user_jsonp.json?ticket=news&templateId=default_world&pool=cbox5&lang=ko&country=KR&objectId=news{oid}%2C{aid}&categoryId=&pageSize=100&indexSize=10&groupId=&listType=user&pageType=more&page={page}&sort=old&commentNo={commentNo}'
    basic_header.update({'Referer':comment_url})

    session = requests.Session()
    idhistory_req = session.get(idhistory_url, headers=basic_header)
    idhistory_json = json_web_cleaner(idhistory_req)

    numHistoryPage = math.ceil(idhistory_json['result']['pageModel']['totalRows']/100)
    if numHistoryPage==1 :
        list_history_json = idhistory_json['result']['commentList']
    else :
        list_history_json = []
        for page in range(1, numHistoryPage+1) :
            idhistory_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_per_user_jsonp.json?ticket=news&templateId=default_world&pool=cbox5&lang=ko&country=KR&objectId=news{oid}%2C{aid}&categoryId=&pageSize=100&indexSize=10&groupId=&listType=user&pageType=more&page={page}&sort=old&commentNo={commentNo}'
            idhistory_req = session.get(idhistory_url, headers=basic_header)
            idhistory_json = json_web_cleaner(idhistory_req)
            list_history_json.extend(idhistory_json['result']['commentList'])
    return list_history_json