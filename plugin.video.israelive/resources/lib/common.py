# -*- coding: utf-8 -*-
import sys, os, io, re, time, base64, hashlib
import urllib, urllib2, json
import xbmc, xbmcgui, xbmcaddon
import multiChoiceDialog
import itertools, operator

AddonID = "plugin.video.israelive"
Addon = xbmcaddon.Addon(AddonID)
AddonName = Addon.getAddonInfo("name")
localizedString = Addon.getLocalizedString
user_dataDir = xbmc.translatePath(Addon.getAddonInfo("profile")).decode("utf-8")
listsDir = os.path.join(user_dataDir, 'lists')

def downloader_is(url, name, showProgress=True):
	import downloader, extract

	addonsDir = xbmc.translatePath(os.path.join('special://home', 'addons')).decode("utf-8")
	packageFile = os.path.join(addonsDir, 'packages', 'isr.zip')

	if showProgress:
		dp = xbmcgui.DialogProgress()
		dp.create(AddonName, "Downloading", name, "Please Wait")
		downloader.download(url, packageFile, dp)
		dp.update(0, "", "Extracting Zip Please Wait")
		extract.all(packageFile, addonsDir, dp)
	else:
		urllib.urlretrieve(url, packageFile)
		extract.all(packageFile, addonsDir)
		
	try:
		os.remove(packageFile)
	except:
		pass
			
	xbmc.executebuiltin("UpdateLocalAddons")
	xbmc.executebuiltin("UpdateAddonRepos")

def isFileOld(file, deltaInSec):
	lastUpdate = 0 if not os.path.isfile(file) else int(os.path.getmtime(file))
	now = int(time.time())
	isFileNotUpdate = True if (now - lastUpdate) > deltaInSec else False 
	return isFileNotUpdate
	
def UpdateFile(file, url, zip=False, forceUpdate=False):
	lastModifiedFile = "{0}LastModified.txt".format(file[:file.rfind('.')])
	if (zip == False and not os.path.isfile(file)) or not os.path.isfile(lastModifiedFile):
		fileContent = ""
	else:
		f = open(lastModifiedFile,'r')
		fileContent = f.read()
		f.close()
	
	last_modified = None
	try:
		req = urllib2.Request(url)
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0')
		req.add_header('Referer', 'http://www.IsraeLIVE.org/')
		response = urllib2.urlopen(req)
		headers = response.info()
		etag = headers.getheader("ETag")
		last_modified = headers.getheader("Last-Modified")
		if not last_modified:
			last_modified = etag
	except Exception as ex:
		print ex
		return False
		
	if last_modified is None:
		return False
		
	isNew = forceUpdate or (fileContent != last_modified)
	
	if isNew:
		if zip:
			urllib.urlretrieve(url, file)
		else:
			try:
				data = response.read().replace('\r','')
			except:
				return False
			
			f = open(file, 'w')
			f.write(data)
			f.close()
		
		f = open(lastModifiedFile, 'w')
		f.write(last_modified)
		f.close()
		
	response.close()
	return isNew
	
def ReadList(fileName):
	try:
		with open(fileName, 'r') as handle:
			content = json.load(handle)
	except Exception as ex:
		print ex
		content=[]

	return content

def WriteList(filename, list):
	try:
		with io.open(filename, 'w', encoding='utf-8') as handle:
			handle.write(unicode(json.dumps(list, indent=2, ensure_ascii=False)))
		success = True
	except Exception as ex:
		print ex
		success = False
		
	return success
	
def GetUpdatedList(file, url, forceUpdate=False):
	UpdateFile(file, Decode(url), forceUpdate=forceUpdate)
	return ReadList(file)
	
def UpdateZipedFile(file, url, forceUpdate=False):
	import extract
	zipFile = "{0}.zip".format(file[:file.rfind('.')])
	if UpdateFile(zipFile, Decode(url), zip=True, forceUpdate=forceUpdate):
		extract.all(zipFile, user_dataDir)
		try:
			os.remove(zipFile)
		except:
			pass
		return True
	return False
	
def GetEncodeString(str):
	import chardet
	try:
		str = str.decode(chardet.detect(str)["encoding"]).encode("utf-8")
	except:
		pass
	return str

def UpdatePlx(url, file, refreshInterval=0, forceUpdate=False):
	isListUpdated = False
	if isFileOld(file, refreshInterval):
		isListUpdated = UpdateFile(file, Decode(url), forceUpdate=forceUpdate)

	if isListUpdated:
		if not os.path.exists(listsDir):
			os.makedirs(listsDir)
	
		dic_list = GetListFromPlx(fullScan=True)
		dic_list.sort(key=operator.itemgetter('group'))
		categories_list = []
		for key, group in itertools.groupby(dic_list, lambda item: item["group"]):
			list1 = [{"url": item["url"], "image": item["image"], "name": item["name"].decode("utf-8"), "type": item["type"], "group": item["group"].decode("utf-8")} for item in group]
			filename = os.path.join(listsDir, "{0}.list".format(hashlib.md5(key.strip()).hexdigest()))
			WriteList(filename, list1)
			categories = [{"name": item["name"], "image": item["image"], "group": item["group"]} for item in list1 if item['type'] == "playlist"]
			if len(categories) > 0:
				for category in categories:
					categories_list.append(category)

		WriteList(os.path.join(listsDir, "categories.list"), categories_list)
		
	return isListUpdated
		
def OKmsg(title, line1, line2="", line3=""):
	dlg = xbmcgui.Dialog()
	dlg.ok(title, line1, line2, line3)
	
def GetMenuSelected(title, list, autoclose=0):
	dialog = xbmcgui.Dialog()
	answer = dialog.select(title, list, autoclose=autoclose)
	return answer

def GetMultiChoiceSelected(title, list):
	dialog = multiChoiceDialog.MultiChoiceDialog(title, list)
	dialog.doModal()
	selected = dialog.selected[:]
	del dialog #You need to delete your instance when it is no longer needed because underlying xbmcgui classes are not grabage-collected. 
	return selected
	
def Encode(string, key=None):
	if key is None:
		key = GetKey()
	encoded_chars = []
	for i in xrange(len(string)):
		key_c = key[i % len(key)]
		encoded_c = chr(ord(string[i]) + ord(key_c) % 256)
		encoded_chars.append(encoded_c)
	encoded_string = "".join(encoded_chars)
	return base64.urlsafe_b64encode(encoded_string)
 
def Decode(string, key=None):
	if key is None:
		key = GetKey()
	decoded_chars = []
	string = base64.urlsafe_b64decode(string.encode("utf-8"))
	for i in xrange(len(string)):
		key_c = key[i % len(key)]
		decoded_c = chr(abs(ord(string[i]) - ord(key_c) % 256))
		decoded_chars.append(decoded_c)
	decoded_string = "".join(decoded_chars)
	return decoded_string
	
def GetKey():
	return AddonName
	
def GetAddonDefaults(addon):
	try:
		f = open(os.path.join(addon.getAddonInfo("path").decode("utf-8"), 'resources', 'settings.xml') ,'r')
		data = f.read()
		f.close()
		matches = re.compile('^.*?<setting id="(.*?)".*?default="(.*?)".*?$',re.I+re.M+re.U+re.S).findall(data)
		dict = {}
		for match in matches:
			dict[match[0]] = match[1]
		return dict

	except Exception as ex:
		print ex
	return dict
	
def GetRemoteSettingsUrl():
	remoteSettingsUrl = Addon.getSetting("remoteSettingsUrl")
	if Addon.getSetting("forceRemoteDefaults") == "true":
		defaultRemoteSettingsUrl = GetAddonDefaults(Addon)["remoteSettingsUrl"]
		if defaultRemoteSettingsUrl != remoteSettingsUrl:
			remoteSettingsUrl = defaultRemoteSettingsUrl
			Addon.setSetting("remoteSettingsUrl", remoteSettingsUrl)
	return remoteSettingsUrl
	
def GetListFromPlx(filterCat="israelive", includeChannels=True, includeCatNames=True, fullScan=False):
	plxFile = os.path.join(user_dataDir, "israelive.plx")
	f = open(plxFile,'r')
	data = f.read()
	f.close()
	
	matches = re.compile('^type(.+?)#$',re.I+re.M+re.U+re.S).findall(data)
	categories = ["israelive"]
	list = []
	for match in matches:
		item=re.compile('^(.*?)=(.*?)$',re.I+re.M+re.U+re.S).findall("type{0}".format(match))
		item_data = {}
		for field, value in item:
			item_data[field.strip().lower()] = value.strip()
		if not item_data.has_key("type"):
			continue
		
		url = item_data['url']
		thumb = "" if not item_data.has_key("thumb") else item_data['thumb']
		channelName = GetEncodeString(item_data['name'])
		
		if item_data["type"] == 'audio' and item_data["url"] == '':
			if channelName.find("-") != 0:
				categories.append(channelName)
				item_data["type"] = "playlist"
				if not includeCatNames:
					continue
			else:
				del categories[-1]
				continue
		elif not includeChannels:
			continue
		
		lenCat = len(categories)
		subCat = categories[lenCat-1] if item_data["type"] != "playlist" else categories[lenCat-2]

		if subCat == filterCat or fullScan:
			list.append({"url": url, "image": thumb, "name": channelName, "type": item_data["type"], "group": subCat})
		
	return list
	
def GetChannels(categoryName):
	fileName = os.path.join(listsDir, "{0}.list".format(hashlib.md5(categoryName.strip()).hexdigest()))
	return ReadList(fileName)
	
def MergeGuides(globalGuideFile, filmonGuideFile, fullGuideFile):
	guideList = ReadList(globalGuideFile)
	filmonGuideList = ReadList(filmonGuideFile)
	WriteList(fullGuideFile, guideList + filmonGuideList)
	MakeCatGuides(fullGuideFile, os.path.join(listsDir, "categories.list"))
	
def MakeCatGuides(fullGuideFile, categoriesFile):
	if not os.path.exists(listsDir):
		os.makedirs(listsDir)
		
	epg = ReadList(fullGuideFile)
	
	categories = ReadList(categoriesFile)
	categories.append({"name": "Favourites"})

	for category in categories:
		MakeCatGuide(fullGuideFile, category["name"], epg)
	
def MakeCatGuide(fullGuideFile, categoryName, epg=None):
	if epg is None:
		epg = ReadList(fullGuideFile)
		
	filename = os.path.join(listsDir, "{0}.guide".format(hashlib.md5(categoryName.encode("utf-8").strip()).hexdigest()))
	channels = GetChannels(categoryName.encode("utf-8")) if categoryName != "Favourites" else ReadList(os.path.join(user_dataDir, 'favorites.txt'))
	categoryEpg = []
	for channel in channels:
		if channel["type"] == 'video' or channel["type"] == 'audio':
			channelName = channel['name'].encode("utf-8").replace("[COLOR yellow][B]", "").replace("[/B][/COLOR]", "")
			try:
				ch = [x for x in epg if x["channel"].encode('utf-8') == channelName]
				if not any(d.get('channel', '').encode('utf-8') == channelName for d in categoryEpg):
					categoryEpg.append(ch[0])
			except Exception, e:
				pass
	WriteList(filename, categoryEpg)
		
def GetGuide(categoryName):
	fileName = os.path.join(listsDir, "{0}.guide".format(hashlib.md5(categoryName.strip()).hexdigest()))
	return ReadList(fileName)
	
def CheckNewVersion():
	versionFile = os.path.join(user_dataDir, "addonVersion.txt")
	if not os.path.isfile(versionFile):
		version = ""
	else:
		f = open(versionFile,'r')
		version = f.read()
		f.close()
	
	newVersion = Addon.getAddonInfo("version")
	if version != newVersion:
		if Addon.getSetting("useIPTV") == "true":
			OKmsg("{0}{1}".format(localizedString(30200).encode('utf-8'), newVersion), localizedString(30201).encode('utf-8'))
		f = open(versionFile, 'w')
		f.write(newVersion)
		f.close()
