# -*- Mode: Python; coding: utf-8; indent-tabs-mode: t; c-basic-offset: 4; tab-width: 4 -*-

from urllib import urlencode
from datetime import datetime, timedelta
from tornado.ioloop import IOLoop
from tornado.gen import coroutine, Task
from tornado.web import authenticated
from tornado.httpclient import HTTPError
from pyquery import PyQuery
from controller.base import BaseHandler

class LearnHandler(BaseHandler):
	@authenticated
	@coroutine
	def post(self):
		username = self.get_secure_cookie('username')
		password = self.get_secure_cookie('password')
		courseID = self.get_argument('courseID')

		yield self.login(username, password)

		#register
		r = yield self.client.fetch(self.courseListUrl, headers=self.cookieHeader)
		d = PyQuery(r.body.decode('utf-8', 'ignore'))

		postData = {
			'__EVENTTARGET': '',
			'__EVENTARGUMENT': '',
			'__VIEWSTATE': d('#__VIEWSTATE').attr('value'),
			'__EVENTVALIDATION': d('#__EVENTVALIDATION').attr('value'),
			'hidPageID': 294,
			'ctl05$hdIsDefault': 1,
			'selectSearch': 'txtKeyword',
			'ctl10$gvCourse$ctl20$checkone': courseID,
			'ctl10$btnMuti.x': '51',
			'ctl10$btnMuti.y': '11',
			'ctl10$HFID': ',%s,' % courseID
		}

		try:
			r = yield self.client.fetch(self.courseListUrl, method='POST', headers=self.cookieHeader, body=urlencode(postData))
		except HTTPError as e:
			r = e.response

		#start play
		r = yield self.client.fetch(self.playUrl + str(courseID), headers=self.cookieHeader)

		#get sid and initParam
		postData = {
			"method": "initParam",
			"courseID": courseID,
			"userID": username
		}
		r, d = yield [self.client.fetch(self.courseUrl + str(courseID), headers=self.cookieHeader), self.client.fetch(self.progressUrl, method='POST', headers=self.cookieReferHeader, body=urlencode(postData))]

		d = PyQuery(r.body.decode('utf-8', 'ignore'))
		sidList = d('.table2 table td:last-child').text().split(' ')
		del sidList[0]

		unitDelta = timedelta(seconds=1)
		#learn all
		for sid in sidList:
			#start one
			postData = {
				'method': 'setParam',
				'lastLocation': 0,
				'SID': sid,
				'curtime': datetime.now().isoformat(' '),
				'STime': 1,
				'state': 'S',
				'courseID': courseID,
				'userID': username
			}
			r = yield self.client.fetch(self.progressUrl, method='POST', headers=self.cookieReferHeader, body=urlencode(postData))

			yield Task(IOLoop.instance().add_timeout, unitDelta)

			#finish one
			postData = {
				'method': 'setParam',
				'lastLocation': 10050,
				'SID': sid,
				'curtime': (datetime.now() + unitDelta).isoformat(' '),
				'STime': 1,
				'state': 'C',
				'courseID': courseID,
				'userID': username
			}
			r = yield self.client.fetch(self.progressUrl, method='POST', headers=self.cookieReferHeader, body=urlencode(postData))

		if 'null' in r.body:
			self.write('ok')
		else:
			self.write('more')