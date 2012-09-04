# coding: utf-8
# 
# put.io xbmc addon
# Copyright (C) 2009  Alper Kanat <alper@put.io>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# 

import os
import sys
import re

import xbmc
import xbmcaddon as xa
import xbmcgui as xg
import xbmcplugin as xp

import resources.lib.putio2 as putio2


PLUGIN_ID = "plugin.video.putiov2"

pluginUrl = sys.argv[0]
pluginId = int(sys.argv[1])
itemId = sys.argv[2].lstrip("?")
addon = xa.Addon(PLUGIN_ID)

class PutioAuthFailureException(Exception):
    def __init__(self, header, message, duration = 10000, icon = "error.png"):
        self.header = header
        self.message = message
        self.duration = duration
        self.icon = icon

def populateDir(pluginUrl, pluginId, listing):    
   
    for item in listing:                        
        if item.screenshot:
            screenshot = item.screenshot
        else:
            screenshot = item.icon

        url = "%s?%s" % (pluginUrl, item.id)
        listItem = xg.ListItem(
            item.name,
            item.name,
            screenshot,
            screenshot
        )

        if "application/x-directory" != item.content_type:
            listItem.setProperty('IsPlayable', 'true')
            listItem.setProperty('Video', 'true')
            niceTitle = re.sub(r'\.\w{3}$', '', item.name)
            niceTitle = re.sub(r'\.', ' ', niceTitle)

            episodeMatch = re.match(r'(.*?)S(\d+)E(\d+)', niceTitle)

            if episodeMatch:
                niceTitle = "%s: Season %s Episode %s" % episodeMatch.groups()

            listItem.setInfo(type='video', infoLabels={'Title': niceTitle})

        xp.addDirectoryItem(
            pluginId,
            url,
            listItem,
            "application/x-directory" == item.content_type
        )
        
    xp.endOfDirectory(pluginId)


def play(item, subtitle=None):
    item = xg.ListItem(path=item.stream_url)
    xp.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)

    if subtitle:
        player = xbmc.Player()
        player.setSubtitles(subtitle)

    #if item.is_mp4_available:
    #    player.play(item.mp4_stream_url)
    #else:
    #    player.play(item.stream_url)    
    #if subtitle:
    #    player.setSubtitles(subtitle)

class PutioApiHandler(object):
    """
    Class to handle putio api calls for XBMC actions
    
    """
    subtitleTypes = ("srt", "sub")    
    
    def __init__(self, pluginId):        
        self.addon = xa.Addon(pluginId)
        self.oauthkey = self.addon.getSetting("oauthkey").replace('-', '')        
        if not self.oauthkey:
            raise PutioAuthFailureException(
                self.addon.getLocalizedString(3001),
                self.addon.getLocalizedString(3002)
            )
            
        self.apiclient = putio2.Client(self.oauthkey)
        
    def getItem(self, itemId):
        return self.apiclient.File.GET(itemId)
    
    def getRootListing(self):
        items = []        
        for item in self.apiclient.File.list(parent_id=0):
            if item.content_type:
                if self.showable(item):
                    items.append(item)                            
        return items
    
    def showable(self, item):
        if 'audio' in item.content_type:
            return True
        elif 'video' in item.content_type:
            return True
        elif "application/x-directory" in item.content_type:
            return True
        else:
            return False
                
    def getFolderListing(self, folderId, isItemFilterActive = True):
        items = []        
        for item in self.apiclient.File.list(parent_id=folderId):
            if isItemFilterActive and not self.showable(item):
                continue
            items.append(item)        
        return items
    
    def getSubtitle(self, item):
        fileName, extension = os.path.splitext(item.name)        
        for i in self.getFolderListing(item.parent_id, False):
            if item.content_type != "application/x-directory":
                fn, ext = os.path.splitext(i.name)                
                if i.name.find(fileName) != -1 and (ext.lstrip(".") in self.subtitleTypes):
                    return i.stream_url

try:
    putio = PutioApiHandler(addon.getAddonInfo("id"))
    if itemId:
        item = putio.getItem(itemId)
        if item.content_type:
            if item.content_type == "application/x-directory":
                populateDir(pluginUrl, pluginId, putio.getFolderListing(itemId))
            elif "video" in item.content_type:
                play(item, subtitle = putio.getSubtitle(item))
            else:
                play(item)
    else:
        populateDir(pluginUrl, pluginId, putio.getRootListing())
except PutioAuthFailureException, e:
    xbmc.executebuiltin("XBMC.Notification(%s, %s, %d, %s)" % (
        e.header,
        e.message,
        e.duration,
        os.path.join(addon.getAddonInfo("path"), "resources", "images", "error.png")
    ))
