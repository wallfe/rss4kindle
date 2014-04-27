#!/usr/bin/env python
# -*- coding:utf-8 -*-
#A GAE web application to aggregate rss and send it to your kindle.
#Visit https://github.com/cdhigh/KindleEar for the latest version
#中文讨论贴：http://www.hi-pda.com/forum/viewthread.php?tid=1213082
#Contributors:
# rexdf <https://github.com/rexdf>

import hashlib, gettext, datetime

import web
from apps.BaseHandler import BaseHandler
from apps.dbModels import *
from books import BookClasses, BookClass

from config import *

#import main

class Login(BaseHandler):
    __url__ = "/login"
    def CheckAdminAccount(self):
        #判断管理员账号是否存在
        #如果管理员账号不存在，创建一个，并返回False，否则返回True
        u = KeUser.all().filter("name = ", 'admin').get()
        if not u:            
            myfeeds = Book(title=MY_FEEDS_TITLE,description=MY_FEEDS_DESC,
                    builtin=False,keep_image=True,oldest_article=7)
            myfeeds.put()
            au = KeUser(name='admin',passwd=hashlib.md5('admin').hexdigest(),
                kindle_email='',enable_send=False,send_time=8,timezone=TIMEZONE,
                book_type="mobi",device='kindle',expires=None,ownfeeds=myfeeds,merge_books=False)
            au.put()
            return False
        else:
            return True
            
    def GET(self):
        # 第一次登陆时如果没有管理员帐号，
        # 则增加一个管理员帐号admin，密码admin，后续可以修改密码
        tips = ''
        if not self.CheckAdminAccount():
            tips = _("Please use admin/admin to login at first time.")
        else:
            tips = _("Please input username and password.")
        
        if main.session.get('login') == 1:
            web.seeother(r'/')
        else:
            return self.render('login.html',"Login",tips=tips)
        
    def POST(self):
        name, passwd = web.input().get('u'), web.input().get('p')
        if name.strip() == '':
            tips = _("Username is empty!")
            return self.render('login.html',"Login",nickname='',tips=tips)
        elif len(name) > 25:
            tips = _("The len of username reached the limit of 25 chars!")
            return self.render('login.html',"Login",nickname='',tips=tips,username=name)
        elif '<' in name or '>' in name or '&' in name:
            tips = _("The username includes unsafe chars!")
            return self.render('login.html',"Login",nickname='',tips=tips)
        
        self.CheckAdminAccount() #确认管理员账号是否存在
        
        try:
            pwdhash = hashlib.md5(passwd).hexdigest()
        except:
            u = None
        else:
            u = KeUser.all().filter("name = ", name).filter("passwd = ", pwdhash).get()
        if u:
            main.session.login = 1
            main.session.username = name
            if u.expires: #用户登陆后自动续期
                u.expires = datetime.datetime.utcnow()+datetime.timedelta(days=180)
                u.put()
                
            #修正从1.6.15之前的版本升级过来后自定义RSS丢失的问题
            for fd in Feed.all():
                if not fd.time:
                    fd.time = datetime.datetime.utcnow()
                    fd.put()
            
            #1.7新增各用户独立的白名单和URL过滤器，这些处理是为了兼容以前的版本
            if name == 'admin':
                for wl in WhiteList.all():
                    if not wl.user:
                        wl.user = u
                        wl.put()
                for uf in UrlFilter.all():
                    if not uf.user:
                        uf.user = u
                        uf.put()
                        
            #如果删除了内置书籍py文件，则在数据库中也清除
            #放在同步数据库是为了推送任务的效率
            for bk in Book.all().filter('builtin = ', True):
                found = False
                for book in BookClasses():
                    if book.title == bk.title:
                        if bk.description != book.description:
                            bk.description = book.description
                            bk.put()
                        found = True
                        break
                
                if not found:
                    for fd in bk.feeds:
                        fd.delete()
                    bk.delete()
            
            raise web.seeother(r'/my')
        else:
            tips = _("The username not exist or password is wrong!")
            main.session.login = 0
            main.session.username = ''
            main.session.kill()
            return self.render('login.html',"Login",nickname='',tips=tips,username=name)

class Logout(BaseHandler):
    __url__ = "/logout"
    def GET(self):
        main.session.login = 0
        main.session.username = ''
        main.session.lang = ''
        main.session.kill()
        raise web.seeother(r'/')