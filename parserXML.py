import os
import time
import signal
import datetime as dt
import functools
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
#import hashlib #TODO: implement hashing to prevent repeat scanning on updates

import rimsheets_support

EXCLUDED = {'Patches', 'Keyed',}
DEFS = list()
#TODO: Auto detect / manual set RW directory
DIR_CORE_DEFS = ["/home/user/.local/share/Steam/steamapps/common/RimWorld/Data/Core/Defs", 'Core']
DIR_ROYAL_DEFS = ["/home/user/.local/share/Steam/steamapps/common/RimWorld/Data/Royalty/Defs", 'Royal']
DIR_WORKSHOP_DEFS = ["/home/user/.local/share/Steam/steamapps/workshop/content/294100", 'Workshop']

LOG = './log.txt'

TIMEOUT_VAL = 0
VERBOSE = False
LOGGING = True
ELAPSED_TIME = 0.0

OUTPUT_TYPE = 'xlxs' #TODO: file type choice
OUTPUT_LOCATION = './'
OUTPUT_NAME = '' #unused TODO: save file location / name
SINGLE_FILE = False

FAILED_FILES = list()    

class TimeOutException(Exception):
    pass


def alarm_handler(signum, frame):
    print("Function has timed out after {} seconds.".format(TIMEOUT_VAL))
    raise TimeOutException()


times = list()
def timer(func):
	"""Print the function execution time"""
	@functools.wraps(func)
	def wrapper_timer(*args, **kwargs):
		tic = time.perf_counter()
		value = func(*args, **kwargs)
		toc = time.perf_counter()
		elapsed_time = toc - tic
		times.append(elapsed_time)
		print(f"Elapsed time: {elapsed_time:0.4f} seconds")
		return value
	return wrapper_timer


def debug(func):
    """Print the function signature and return value"""
    @functools.wraps(func)
    def wrapper_debug(*args, **kwargs):
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        print(f"Calling {func.__name__}({signature})\n")
        value = func(*args, **kwargs)
        print(f"{func.__name__!r} returned {value!r}\n")
        return value
    return wrapper_debug


def parseXML(filename, modName, progress):
	"""Get data contained in XML files"""
	try:
		root = ET.parse(filename)
		parsedXML = [['modNumber', modName]]
		
		for elem in root.iter():
			rimsheets_support.setProgress(
				'Scanning XML:\n{}\nWorking... Please be patient this may take a while'.format(elem),
				progress)

			if elem.tag == 'filter':
				pass
			elif elem.tag != 'li':
				parsedXML.append([str(elem.tag).strip(), str(elem.text).strip()])
			else:
				parsedXML.append([str(elem.text).strip()])
			parsedXML.append('!BREAK!')
		
		return parsedXML
	except:
		return [''] #In case some modder left an empty XML file


def toDF(filename, data):
	"""Convert parsed XML data to pandas dataframes"""
	if VERBOSE: print(filename)
	listOfDf = list()
	listOfDicts = [[], []]
	df = dict()

	#Break defs within XML files into individual items
	i = 0
	for each in data:
		if each != '!BREAK!':
			listOfDicts[i].append(each)
		else:
			i += 1
			listOfDicts.append([''])

	#Convert defs to pandas dataframes
	for idx, def_ in enumerate(listOfDicts):
		for each in def_:
			try:
				df[each[0]] = each[1]
			except:
				pass
		listOfDf.append(pd.DataFrame(df, index=[idx]))

	try:
		return [filename, pd.concat(listOfDf).drop_duplicates('defName').set_index('defName')]
	except KeyError:
		try:
			#Some files (e.g. SongDefs) do not contain a 'defName' tag but are still wanted so we dump them raw
			return [filename, pd.concat(listOfDf)]
		except:
			pass
		if VERBOSE: print('KEY ERROR ON: {}'.format(filename))
		FAILED_FILES.append('KEY ERROR ON: {}'.format(filename))
		pass


def toExcel(dfList, filename):
	"""Save XML data as an Excel xlxs workbook"""
	Excelwriter = pd.ExcelWriter("{}{}.xlsx".format(OUTPUT_LOCATION, filename), engine="xlsxwriter")

	try:
		for i, df in dfList:
			df.to_excel(Excelwriter, sheet_name=str(i))
	except:
		if VERBOSE: print('ERROR DURING WRITE OF: {}'.format(filename))
		FAILED_FILES.append('ERROR DURING WRITE OF: {}'.format(filename))
		pass
	
	Excelwriter.save()


def toCSV(dfList, filename):
	"""Save XML data as a raw CSV file"""
	try:
		dfList.to_csv('{}{}.csv'.format(OUTPUT_LOCATION, filename))
	except:
		if VERBOSE: print('ERROR DURING WRITE OF: {}'.format(filename))
		pass
	

def getFileList(dirName, fileType='xml'): 
	listOfFiles = list()
	for (dirpath, dirnames, filenames) in os.walk(dirName[0]):
		listOfFiles += [os.path.join(dirpath, file) for file in filenames if fileType in file.split('.')[-1]]
	return listOfFiles


def scanXML(dirName, listOfFiles):
	dictOfDefs = dict()

	i = 1
	for elem in listOfFiles:
		if VERBOSE: print('Scanning XML... {} / {}'.format(i, len(listOfFiles)))
		progress = (int(i) * 100) / int(len(listOfFiles))

		if dirName[1] == 'Workshop':
			modName = elem.split('294100')[-1]
			modName = modName.split('/')[0]
		else:
			modName = dirName[1]

		if elem.split('.')[-1] == 'xml':
			defType = elem.split('/')[-2]
			if defType not in EXCLUDED:
				if defType in dictOfDefs:
					newR = dictOfDefs[defType] + parseXML(elem, modName, progress)
					dictOfDefs[defType] = newR
				else:
					dictOfDefs[defType] = parseXML(elem, modName, progress)
			i += 1
	
	return dictOfDefs


def cleanup(dfList, modType):
	if VERBOSE: print("sorting...")
	dfList.sort(key=lambda x: x[0])
			
	if VERBOSE: print('exporting...')
	{
		'xlxs': lambda: toExcel(dfList, modType[1]),
		'csv': lambda: toCSV(dfList, modType[1]),
	}.get(OUTPUT_TYPE, lambda: None)()

	if VERBOSE: print('DONE!')
	if VERBOSE: print('Max: {}'.format(max(times)))
	if VERBOSE: print('Min: {}'.format(min(times)))
	if VERBOSE: print('Total: {}'.format(sum(times)))
	if VERBOSE: print('Average: {}'.format(sum(times) / len(times)))


def run():	
	tic = time.perf_counter()
	for modType in DEFS:
		dfList = list()
		dictOfDefs = dict()
		if VERBOSE: print('Starting scan on {}'.format(modType[1]))	
		listOfFiles = getFileList(modType)
		dictOfDefs = scanXML(modType, listOfFiles)

		i = 1
		for key, val in dictOfDefs.items():
			if VERBOSE: print('Converting... {} / {}'.format(i, len(dictOfDefs)))
			
			signal.signal(signal.SIGALRM, alarm_handler)
			signal.alarm(TIMEOUT_VAL)
			try:
				progress = (int(i) * 100) / int(len(dictOfDefs))
				banner = 'Parsing: {}\n{} / {}\n Working... Please be patient this may take a while'.format(
					key, i, len(dictOfDefs))
    
				rimsheets_support.setProgress(banner, progress)
				df = toDF(key, val)
				if df:
					if VERBOSE: print('ON: {}'.format(df[0]))
					dfList.append(df)

			except TimeOutException:
				FAILED_FILES.append('TIME OUT ON: {}'.format(key))
			signal.alarm(0)
			i += 1

		if not SINGLE_FILE:
			cleanup(dfList, modType[1])

	if SINGLE_FILE:
		cleanup(dfList, 'RimSheets')

	toc = time.perf_counter()
	ELAPSED_TIME = toc - tic

	if len(FAILED_FILES) > 0:
		with open(LOG, 'w') as f:
			for each in FAILED_FILES:
				f.write('{}\n'.format(each))
		rimsheets_support.setProgress(
			'Done in {} seconds.\nErrors were encountered, see log for details.'.format(round(ELAPSED_TIME, 4)), 100)
	else:
		rimsheets_support.setProgress('Done in {} seconds.'.format(round(ELAPSED_TIME, 4)), 100)

'''

def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
    for block in bytesiter:
        hasher.update(block)
    return hasher.hexdigest() if ashexstr else hasher.digest()

def file_as_blockiter(afile, blocksize=65536):
    with afile:
        block = afile.read(blocksize)
        while len(block) > 0:
            yield block
            block = afile.read(blocksize)

def scanFileChanges():
	storedHashes = []
	hashes = [(fname, hash_bytestr_iter(file_as_blockiter(open(fname, 'rb')), hashlib.sha256()))
		for fname in listOfFiles]

	try:
		with open('./data/checksums.txt', 'r') as f:
			storedHashes = f.readlines()
	except FileNotFoundError:
		with open('./data/checksums.txt', 'w') as f:
			for each in hashes:
				f.write('{} : {}\n'.format(each[0], each[1]))

	hashes.sort()
	storedHashes.sort()
	print(len(storedHashes))
	print(len(hashes))
	print(storedHashes[0].split(' : '))
	print(hashes[0])

	if len(storedHashes) == len(hashes):
		for old, new in zip(storedHashes, hashes):
			if old.split(' : ')[] != new:
				pass
'''