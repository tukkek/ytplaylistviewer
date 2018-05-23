#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys,operator,math
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from oauth2client.file import Storage

def get_authenticated_service():
  flow=InstalledAppFlow.from_client_secrets_file("client_secret.json", ['https://www.googleapis.com/auth/youtube.force-ssl'])
  storage = Storage('credentials.storage')
  credentials=storage.get()
  if credentials==None:
    credentials=flow.run_local_server(
        host='localhost',
        port=8080, 
        authorization_prompt_message='Please visit this URL: {url}', 
        success_message='The auth flow is complete; you may close this window.',
        open_browser=True)
    try:
        storage.put(credentials)
    except AttributeError as e:
        pass #for some reason credentials doesn't have 
  return build('youtube', 'v3', credentials = credentials)
service=get_authenticated_service()

DEBUG=False
MAXRESULTS=50
RELATEDRESULTS=9

def pages(service,request,follow=True): #TODO return items
  i=0
  while request:
    try:
      response=request.execute()
    except Exception as e:
      print(e)
      continue
    for item in response['items']:
      yield item
    if not follow:
      return
    request=service.list_next(request,response)
    
def go():
  try:
    #yt playlist viewer
    videosids=[] 
    playlistsservice=service.playlists()
    if len(sys.argv)==1:
        print('Usage: ./ytplaylistviewer.py playlistId [playlistId playlistId ...]')
        sys.exit(1)
    for target in sys.argv[1:]:
      for pl in pages(playlistsservice,playlistsservice.list(part='id,snippet',maxResults=MAXRESULTS,id=target)):
        title=pl['snippet']['title']
        print('expand='+str(len(videosids))+' results='+str(len(videosids))+' now: '+title)
        playlistitems=service.playlistItems()
        count=0
        for video in pages(playlistitems,playlistitems.list(part='snippet',playlistId=pl['id'],maxResults=MAXRESULTS)):
          count+=1
          if count%100==0:
            print(title+' #'+str(count))
          videoid=video['snippet']['resourceId']['videoId']
          if not videoid in videosids:
            videosids.append(videoid)
        if DEBUG:
          break
    i=-1
    #print('videos '+str(100*i/(len(videosids)))+'% '+str(relatedcount)+' found')
    videos=[]
    requests=math.ceil(len(videosids)/float(MAXRESULTS))
    nrequests=0
    while len(videosids)!=0: #video info
      print('videos '+str(int(100*(nrequests/requests)))+'%')
      nrequests+=1
      ids=videosids[:MAXRESULTS]
      idscsv=''
      for i in ids:
        idscsv+=i+','
      idscsv=idscsv[:-1]
      videosservice=service.videos()
      try:
        for video in pages(videosservice,videosservice.list(part='statistics,snippet,id,contentDetails',id=idscsv,maxResults=MAXRESULTS)):
          snippet=video['snippet']
          title=snippet['title']
          videoid=video['id']
          stats=video['statistics']
          likes=stats['likeCount'] if 'likeCount' in stats else '0'
          dislikes=stats['dislikeCount'] if 'dislikeCount' in stats else '9000'
          videos.append({ #TODO can probably just pass original dict
            'id':videoid,
            'channel':snippet['channelTitle'],
            'channelId':snippet['channelId'],
            'title':title,
            'description':snippet['description'],
            'lpd':float(likes)/(float(dislikes)+1),
            'likes':likes,
            'dislikes':dislikes,
            'length':video['contentDetails']['duration'],
            'image':snippet['thumbnails']['default']['url'],
            })
        videosids=videosids[MAXRESULTS:]
      except: #TODO
        print('BadStatusLine wtf!! '+idscsv)
    print('Total videos: '+str(len(videos)))
    out=open('ytuidata.js','w')
    out.write('var ytuidata=[];\n')
    i=0
    for related in sorted(videos,reverse=True,key=operator.itemgetter('lpd')): #output
      item='ytuidata['+str(i)+']'
      out.write(item+'=[];\n')
      for data in [
        ['likes',str(int(related['likes']))],
        ['dislikes',str(int(related['dislikes']))],
        ['channel',related['channel']],
        ['id',related['id']],
        ['duration',related['length']],
        ['title',str(int(related['lpd']))+'. '+related['title']],
        ['image',related['image']],
        ['channelId',related['channelId']],
        ['description',related['description']],
        ]:
        value=data[1]
        for substitution in [
          ['\\','\\\\"'],
          ['"','\\"'],
          ['\n','\\n'],
          ['\r',''],
          [u'\u2028','\\n'],
          ]:
          value=value.replace(substitution[0],substitution[1])
        out.write(item+'["'+data[0]+'"]="'+value+'";\n')
      i+=1
  except Exception as e:
   raise e
go()
