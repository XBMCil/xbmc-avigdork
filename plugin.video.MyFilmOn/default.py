import xbmc, xbmcgui, xbmcplugin, xbmcaddon, json
import os, sys, datetime, re
import urllib, urllib2
import xml.etree.ElementTree as ET

isOldPy = False if sys.version_info >=  (2, 7) else True

UA = 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0'
iconPattern = 'http://static.filmon.com/couch/channels/<channelNum>/extra_big_logo.png'

AddonID = 'plugin.video.MyFilmOn'
Addon = xbmcaddon.Addon(AddonID)
localizedString = Addon.getLocalizedString
isLocalList = False if (Addon.getSetting('local_playlist').lower() == 'false') else True
remoteTxtListFile = Addon.getSetting('remoteTxtList')
remoteXmlListFile = Addon.getSetting('remoteXmlList')
localFolder = Addon.getSetting('localFolder')
if (localFolder == ''):
	localFolder = os.path.join(xbmc.translatePath('special://home/userdata').decode("utf-8"), 'addon_data', AddonID)
imagesFolder = os.path.join(Addon.getAddonInfo('path').decode("utf-8"), 'resources', 'images')
	
def GetChannelsList(background=None):
	listExt = Addon.getSetting('fileExt').lower()
	if (listExt == 'xml'):
		isCategories = False if (Addon.getSetting('categories').lower() == 'false') else True
		if (isCategories):
			GetChannelsInCategoriesList('root', background)
		else:
			GetChannelsInCategoriesList('', background)
	else:
		localPlaylist = os.path.join(localFolder, 'favoritesList.txt')
		lines = None
		if (isLocalList and os.path.isfile(localPlaylist)):
			f = open(localPlaylist, 'r')
			lines = f.readlines()
		else:
			txt = OpenURL(remoteTxtListFile).replace('\n','')
			print remoteTxtListFile
			print txt
			p = re.compile(r'\r')
			lines = p.split(txt)
		for w in lines[:]:
			tok = re.split('\.\W+', w)
			chNum = chName = chRef = None
			if len(tok) > 1:
				chNum = tok[0].strip()
				chName = tok[1].strip()
				if len(tok) > 2:
					chRef = tok[2].strip()
			addChannel(chNum, chName, chRef)

def GetStreamUrl ( stream , playpath ) :
	if re . search ( 'mp4' , playpath , re . IGNORECASE ) :
		try:
			pattern = re . compile ( 'rtmp://(.+?)/(.+?)/(.+?)/<' )
			tocks = pattern . search ( stream+'<' )
			app = '%s/%s/' % ( tocks . group ( 2 ) , tocks . group ( 3 ) )
			swfUrl = 'http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'
			URL = stream + playpath
		except :
			pass
		try:
			pattern = re . compile ( 'rtmp://(.+?)/(.+?)<' )
			tocks = pattern . search ( stream+'<' )
			app = '%s' % ( tocks . group ( 1 ) , tocks . group ( 2 ) )
			swfUrl = 'http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'
			URL = stream + '/' + playpath
		except :
			pass
	if re . search ( 'm4v' , playpath , re . IGNORECASE ) :
		app = 'vodlast'
		swfUrl = 'http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'
		URL = stream + '/' + playpath
	else :
		try :
			pattern = re . compile ( 'rtmp://(.+?)/live/(.+?)id=(.+?)<' )
			tocks = pattern . search ( stream+'<' )
			app = 'live/%sid=%s' % ( tocks . group ( 2 ) , tocks . group ( 3 ) )
			URL = stream
			swfUrl = 'http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'
		except :
			pass
		try :
			pattern = re . compile ( 'rtmp://(.+?)/(.+?)id=(.+?)"' )
			tocks = pattern . search ( stream+'<' )
			app = '%sid=%s' % ( tocks . group ( 2 ) , tocks . group ( 3 ) )
			swfUrl = 'http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf?v=28'
		except :
			pass
		try :
			pattern = re . compile ( 'rtmp://(.+?)/(.+?)/<' )
			tocks = pattern . search ( stream+'<' )
			app = '%s/' % ( tocks . group ( 2 ) )
			URL = stream + '/' + playpath
			swfUrl = 'http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'
		except :
			pass
	tcUrl = stream
	pageurl = 'http://www.filmon.com/'
	URL = str ( URL ) + ' playpath=' + str ( playpath ) + ' app=' + str ( app ) + ' swfUrl=' + str ( swfUrl ) + ' tcUrl=' + str ( tcUrl ) + ' pageurl=' + str ( pageurl ) + ' live=true'
	return URL
 
def PlayChannel(chNum, referrerCh=None, ChName=None):
	if referrerCh == None:
		prms = GetChannelJson(chNum)
	else:
		prms = GetChannelJson(referrerCh)
		
	if prms == None:
		print '--------- Playing Error: there is no channel with id="{0}" ---------'.format(chNum)
		xbmc.executebuiltin('Notification({0}, {1}, {2}, {3})'.format(AddonID, localizedString(55012).encode('utf-8'), 5000, os.path.join(imagesFolder, 'fail.png')))
		return
		
	#print "serverURL: {0}\nstreamName: {1}".format(prms["serverURL"], prms["streamName"])
	#srteam = GetStreamUrl(prms["serverURL"], prms["streamName"].replace('low','high'))
	#print "srteam: {0}".format(srteam)
	#return
	channelName, channelDescription, iconimage, streamUrl, tvGuide = GetChannelDetails(prms, chNum, referrerCh, ChName)

	channelName = "[B]{0}[/B]".format(channelName)
	
	if len(tvGuide) > 0:
		programme = tvGuide[0]
		programmeName = '[B]{0}[/B] [{1}-{2}]'.format(programme[2], datetime.datetime.fromtimestamp(programme[0]).strftime('%H:%M'), datetime.datetime.fromtimestamp(programme[1]).strftime('%H:%M'))
		#image = programme[4]
		if len(tvGuide) > 1:
			nextProgramme = tvGuide[1]
			channelName = "[COLOR yellow]{0}[/COLOR] - [COLOR white]Next: [B]{1}[/B] [{2}-{3}][/COLOR]".format(channelName, nextProgramme[2], datetime.datetime.fromtimestamp(nextProgramme[0]).strftime('%H:%M'), datetime.datetime.fromtimestamp(nextProgramme[1]).strftime('%H:%M'))
	else:
		programmeName = channelName
		channelName = "[COLOR yellow]{0}[/COLOR]".format(channelName)
		#image = iconimage
		
	print '--------- Playing: ch="{0}", name="{1}" ----------'.format(chNum, channelName)
	try:
		PlayUrl(streamUrl, channelName, iconimage, programmeName)
	except:
		PlayUrl(streamUrl.replace('high','low'), channelName, iconimage, programmeName)
	
def GetChannelDetails(prms, chNum, referrerCh=None, ChName=None):
	iconimage = iconPattern.replace('<channelNum>',str(chNum))
	pageUrl = "http://www.filmon.com/"
	swfUrl = 'http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf'
	url = prms["serverURL"]
	i = url.find('/', 7)
	app = url[i+1:]
	
	channelName = ""
	channelDescription = ""
	tvGuide = []
	
	if referrerCh <> None:
		channelName = ChName
		playPath = '{0}.high.stream'.format(chNum)
	else:
		channelName = prms["title"].encode('utf-8')
		if prms.has_key("description"):
			channelDescription = prms["description"].encode('utf-8')
		playPath = prms["streamName"].replace('low','high')
		
		programmename = ""
		description = ""
		startdatetime = 0
		enddatetime = 0
	
		server_time = int(prms["server_time"])
		if prms.has_key("tvguide") and len(prms["tvguide"]) > 1:
			tvguide = prms["tvguide"]
			for prm in tvguide:
				startdatetime = int(prm["startdatetime"])
				enddatetime = int(prm["enddatetime"])
				if server_time > enddatetime:
					continue
				description = prm["programme_description"]
				programmename = prm["programme_name"]
				image = None if not prm.has_key("images") or len(prm["images"]) == 0 else prm["images"][0]["url"]
				tvGuide.append((startdatetime, enddatetime, programmename.encode('utf-8'), description.encode('utf-8'), image))
		elif prms.has_key("now_playing") and len(prms["now_playing"]) > 0:
			now_playing = prms["now_playing"]
			startdatetime = int(now_playing["startdatetime"])
			enddatetime = int(now_playing["enddatetime"])
			
			if startdatetime < server_time and server_time < enddatetime:
				description = now_playing["programme_description"]
				programmename = now_playing["programme_name"]
				image = None if not prms.has_key("images") or len(prms["images"]) == 0 else prms["images"][0]["url"]
				tvGuide.append((startdatetime, enddatetime, programmename.encode('utf-8'), description.encode('utf-8'), image))
	
	streamUrl = "{0} tcUrl={0} app={1} playpath={2} swfUrl={3} swfVfy=true pageUrl={4} live=true".format(url, app, playPath, swfUrl, pageUrl)
	return channelName, channelDescription, iconimage, streamUrl, tvGuide

def PlayUrl(url, channelName, iconimage=None, programmeName=None):
	liz = xbmcgui.ListItem(path=url)
	liz.setInfo( type = "Video", infoLabels={ "Title": programmeName, "studio": channelName})
	liz.setProperty("IsPlayable","true")
	if iconimage:
		liz.setThumbnailImage(iconimage)
	xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=liz)
	
def ChannelGuide(chNum):
	prms = GetChannelJson(chNum)
	if prms == None:
		addDir('[COLOR red][B]No TV-Guide for this channel.[/B][/COLOR]', '.', 99, '', '')
		return
	
	channelName, channelDescription, iconimage, streamUrl, tvGuide = GetChannelDetails(prms, chNum)
	
	if len(tvGuide) == 0:
		addDir('[COLOR red][B]No TV-Guide for "{0}".[/B][/COLOR]'.format(channelName), '.', 99, iconimage, channelDescription, background=iconimage)
	else:
		addDir('------- [B]{0} - TV-Guide[/B] -------'.format(channelName), '.', 99, iconimage, channelDescription, background=iconimage)
		for programme in tvGuide:
			startdatetime=datetime.datetime.fromtimestamp(programme[0]).strftime('%d/%m %H:%M')
			enddatetime=datetime.datetime.fromtimestamp(programme[1]).strftime('%H:%M')
			programmename='[{0}-{1}] [B]{2}[/B]'.format(startdatetime,enddatetime,programme[2])
			description=programme[3]
			image = programme[4] if programme[4] else iconimage
			addDir(programmename, chNum, 99, image, description, background=image)
		
	xbmcplugin.setContent(int(sys.argv[1]), 'movies')
	xbmc.executebuiltin("Container.SetViewMode({0})".format(Addon.getSetting('EpgStyle')))
	
def OpenURL(url, headers={}, user_data={}, justCookie=False):
	if user_data:
		user_data = urllib.urlencode(user_data)
		req = urllib2.Request(url, user_data)
	else:
		req = urllib2.Request(url)
	
	req.add_header('User-Agent', UA)
	for k, v in headers.items():
		req.add_header(k, v)
	
	response = urllib2.urlopen(req)
	
	if justCookie == True:
		if response.info().has_key("Set-Cookie"):
			data = response.info()['Set-Cookie']
		else:
			data = None
	else:
		data = response.read()
	
	response.close()
	return data
	
def GetChannelHtml(chNum):
	url1 = 'http://www.filmon.com/tv/htmlmain'
	url2 = 'http://www.filmon.com/ajax/getChannelInfo'

	cookie = OpenURL(url1, justCookie=True)

	headers = {'X-Requested-With': 'XMLHttpRequest', 'Connection': 'Keep-Alive', 'Cookie': cookie}
	user_data = {'channel_id': chNum}
	
	response = OpenURL(url2, headers, user_data)
	return response
	
def GetChannelJson(chNum):
	html = GetChannelHtml(chNum)
	resultJSON = json.loads(html)
	if len(resultJSON) < 1 or not resultJSON.has_key("title"):
		return None
	return resultJSON
		
def GetChannelsInCategoriesList(categoryID, background=None):
	background1 = None 
	if background != None:
		background1 = background

	tree = getXmlList()
	condition = ''
	
	if (categoryID == ''):
		list1 = tree.findall('.//channel')
	elif (categoryID == 'root'):
		list1 = tree.findall('*')
	else:
		for elem in tree.findall(".//category"):
			if elem.attrib.get('id') == categoryID:
				list1 = elem.getchildren() if isOldPy else list(elem)
				break
		
	for elem in list1:
		elemID = elem.get('id')
		elemName = elem.get('name')
		if (elem.tag == 'channel'):
			referrerCh = elem.get('referrerCh')
			if referrerCh == '0':
				iconimage = elem.get('iconimage')
				addDir(elemName, elemID, 6, iconimage, '', background=background1)
			else:
				addChannel(elemID, elemName, referrerCh, background1)
		else:
			background = elem.get('background')
			addDir('[{0}]'.format(elemName), elemID, 4, '', '', background=background)
			
def getXmlList():
	localPlaylist = os.path.join(localFolder, 'favoritesList.xml')
	tree = None
	if (isLocalList and os.path.isfile(localPlaylist)):
		tree = ET.parse(localPlaylist)
	else:
		tree = ET.fromstring(OpenURL(remoteXmlListFile).replace('\n',''))
	return tree

def addDir(name, url, mode, iconimage, description, referrerCh=None, background=None):
	u = "{0}?url={1}&mode={2}".format(sys.argv[0], urllib.quote_plus(url), str(mode))
	if (referrerCh != None):
		u = "{0}&referrerch={1}&chname={2}".format(u, str(referrerCh), str(name))
	if (mode == 6):
		u = "{0}&iconimage={1}&chname={2}".format(u, urllib.quote_plus(iconimage), str(name))
	if (background != None):
		u = "{0}&background={1}".format(u, urllib.quote_plus(background))
	
	if (mode != 99):
		name = '[COLOR white]{0}[/COLOR]'.format(name)

	liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": description} )
	
	if (background != None):
		liz.setProperty('fanart_image',background)
		
	if (mode == 1):
		liz.setProperty('IsPlayable', 'true')
		if (referrerCh == None):
			items = []
			items.append(('TV Guide', 'XBMC.Container.Update({0}?url={1}&mode=2&iconimage={2})'.format(sys.argv[0], urllib.quote_plus(url), iconimage)))
			liz.addContextMenuItems(items = items)
	
	if (mode == 99 or mode == 1):
		isFolder = False
	else:
		isFolder=True

	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=isFolder)
	
def addChannel(channelNum, channelName, referrerCh=None, background=None):
	iconimage = iconPattern.replace('<channelNum>', channelNum)
	addDir(channelName, channelNum, 1, iconimage, '', referrerCh, background)

def CopyRemoteListToLocal(ext):
	if (ext == 'copyXML'):
		localPlaylist = os.path.join(localFolder, 'favoritesList.xml')
		txt = OpenURL(remoteXmlListFile).replace('\n','')
	else: #(ext == 'copyTXT'):
		localPlaylist = os.path.join(localFolder, 'favoritesList.txt')
		txt = OpenURL(remoteTxtListFile).replace('\r','')
	
	f = open(localPlaylist, 'w')
	f.write(txt)
	xbmc.executebuiltin('Notification({0}, {1}, {2}, {3})'.format(AddonID, localizedString(55011).encode('utf-8'), 5000, os.path.join(imagesFolder, 'ok.png')))
	
def get_params():
	param = []
	paramstring = sys.argv[2]
	if len(paramstring) >= 2:
		params = sys.argv[2]
		cleanedparams = params.replace('?','')
		if (params[len(params)-1] == '/'):
			params = params[0:len(params)-2]
		pairsofparams = cleanedparams.split('&')
		param = {}
		for i in range(len(pairsofparams)):
			splitparams = {}
			splitparams = pairsofparams[i].split('=')
			if (len(splitparams)) == 2:
				param[splitparams[0].lower()] = splitparams[1]
	return param

params=get_params()
url = None
mode = None
referrerCh = None
ChName = None
iconimage = None
background = None

try:
	url = urllib.unquote_plus(params["url"])
except:
	pass
try:        
	mode = int(params["mode"])
except:
	pass
try:        
	referrerCh = int(params["referrerch"])
except:
	pass
try:      
	ChName = urllib.unquote_plus(params["chname"])
except:
	pass
try:        
	iconimage = urllib.unquote_plus(params["iconimage"])
except:
	pass
try:        
	background = urllib.unquote_plus(params["background"])
except:
	pass

if mode == None or url == None or len(url) < 1:
	GetChannelsList(background)
elif mode == 1:
	PlayChannel(url, referrerCh, ChName)
elif mode == 2:
	ChannelGuide(url)
elif mode == 4:
	GetChannelsInCategoriesList(url, background)
elif mode == 5:
	CopyRemoteListToLocal(url)
	sys.exit()
elif mode == 6:
	PlayUrl(url, ChName, iconimage)

xbmcplugin.endOfDirectory(int(sys.argv[1]))