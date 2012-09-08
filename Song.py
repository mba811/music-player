class Song:
	def __init__(self, fn=None): # we must support an empty init for PersistentObject
		self.url = fn
		self.f = None
		self._fileMetadata = None
		self._metadata = None
	def __nonzero__(self): # this is mostly for noninited Song objects
		return bool(self.url)
	def openFile(self):
		if not self.f:
			self.f = open(self.url)

	# { ffmpeg player interface
	def readPacket(self, bufSize):
		s = self.f.read(bufSize)
		return s
	def seekRaw(self, offset, whence):
		r = self.f.seek(offset, whence)
		return self.f.tell()
	# ffmpeg player interface end }
	
	def close(self):
		self.f = None
	
	def __repr__(self):
		return "Song(%r)" % self.url

	def __str__(self):
		import os
		return "Song(%s)" % os.path.basename(self.url)

	@property
	def metadata(self):
		if self._metadata is not None: return self._metadata
		import State
		player = State.state.player
		if self._fileMetadata is None:
			if player and player.curSong is self:
				self._fileMetadata = player.curSongMetadata or {}
			else:
				# try to read the metadata manually
				try:
					# make a new songObj. this prevents any multithreading issues
					songObj = Song(self.url)
					songObj.openFile()
					import ffmpeg
					self._fileMetadata = ffmpeg.getMetadata(songObj) or {}
				except: pass # couldn't open or so
		if self._fileMetadata is not None:
			m = dict([(key.lower(),value) for (key,value) in self._fileMetadata.items()])
			self._metadata = m # only save attrib if this is from player. otherwise we might get later some better results
		else:
			m = {}
		if hasattr(self, "rating"): m["rating"] = self.rating
		self.fixupMetadata(m)
		self.guessMetadata(m)
		return m

	def fixupMetadata(self, metadata=None):
		if not metadata: metadata = self.metadata
		def fixString(key):
			if key in metadata:
				metadata[key] = metadata[key].strip()
			else:
				return
			if metadata[key] in ["", "Unknown", "Unknown " + key]:
				del metadata[key]
		fixString("artist")
		fixString("title")

	_guessRegexps = [
		"^(.*/)*(?P<artist>.+?)/(?P<album>.+?)/(?P<track>\d+)(\s*-)?\s*(?P<title>.+)$",
		"^(.*/)*(?P<artist>.+?)\s-\s(?P<title>.+)$",
		"^(.*/)*(?P<artist>.+?)-(?P<title>.+)$",
		"^(.*/)*(?P<artist>.+?)/(?P<album>.+?)/(?P<title>.+)$",
	]

	def guessMetadata(self, metadata=None):
		""" guesses metadata from filename. the current metadata is expected to be fixed (fixupMetadata). """
		if not metadata: metadata = self.metadata
		if "artist" in metadata and "title" in metadata: return # that's enough for most usage, no need to guess
		import re, os
		fn = os.path.splitext(self.url)[0]
		# For now, just take the first matching.
		# Later improvement might be:
		#  - Collect all matching.
		#  - Calculate some likelihood for each (e.g. guess that number-only strings are probably not artist names, etc.)
		for r in self._guessRegexps:
			match = re.match(r, fn)
			if not match: continue
			match = match.groupdict()
			for key in match:
				if match[key] is not None:
					metadata[key] = match[key]
			#print "guessed metadata:", metadata, "from", fn
			return

	@property
	def artist(self):
		return self.metadata.get("artist", "Unknown artist").strip()

	@property
	def album(self):
		return self.metadata.get("album", "Unknown album").strip()
		
	@property
	def title(self):
		return self.metadata.get("title", "Unknown title").strip()

	@property
	def track(self):
		return self.metadata.get("track", 0)

	@property
	def date(self):
		return self.metadata.get("date", "").strip()

	@property
	def composer(self):
		return self.metadata.get("composer", "Unknown composer").strip()
		
	@property
	def duration(self):
		return self.metadata.get("duration", -1)

	@property
	def genre(self):
		return self.metadata.get("genre", "")

	# dict from tag to value [0,1] (weighted tagmap, tag fuzzy set)
	@property
	def tags(self):
		taglist = self.metadata.get("genre", "").split(",")
		taglist = map(str.strip, taglist)
		taglist = filter(None, taglist)
		return dict([(tag,1.0) for tag in taglist])

	@property
	def fileext(self):
		import os
		return os.path.splitext(self.url)[1][1:]

	@property
	def userString(self):
		artist = self.metadata.get("artist", "").strip()
		title = self.metadata.get("title", "").strip()
		if artist and title: return artist + " - " + title
		import os
		return os.path.basename(self.url)

def test():
	s = Song("/yyy/xxx/Tool/Lateralus/12 Triad.flac")
	assert s.metadata["artist"] == "Tool"
	assert s.metadata["album"] == "Lateralus"
	assert s.metadata["title"] == "Triad"
	assert s.metadata["track"] == "12"
	s = Song("/yyy/xxx/Tool/Lateralus/Triad.flac")
	assert s.metadata["artist"] == "Tool"
	assert s.metadata["album"] == "Lateralus"
	assert s.metadata["title"] == "Triad"
	s = Song("/zzz/yyy/xxx/abc - foo - bar")
	assert s.metadata["artist"] == "abc"
	assert s.metadata["title"] == "foo - bar"

if __name__ == "__main__":
	print "*** testing"
	test()
