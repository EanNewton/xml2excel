#TODO choice between group by mod or by def type for workshop

import os
import time
import re
import signal
import datetime as dt
import functools
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
#import hashlib #TODO: implement hashing to prevent repeat scanning on updates

import rimsheets_support

#TODO: Checkbox selection for skip directories
EXCLUDED = {}
#EXCLUDED = {'Patches', 'Keyed', 'ThingDefs_Buildings'}
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

OUTPUT_TYPE = 'csv' #TODO: file type choice
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
	tic = time.perf_counter()
	try:
		tree = ET.parse(filename)
		root = tree.getroot()
		parsedXML = [['modNumber', modName]]
		topleveltag = ''

		try:
			for idx, elem in enumerate(root.iter()):
				if idx == 2:
					topleveltag = elem.tag
					with open('./tags.txt', 'a') as f:
						f.write('{} : {}\n\n'.format(filename, topleveltag))
				if elem.tag == topleveltag:
					parsedXML.append('!BREAK!')
				if elem.attrib:
					parsedXML.append([elem.tag, elem.attrib, elem.text.strip()])
				else:
					parsedXML.append([elem.tag, elem.text.strip()])
		except AttributeError as ex:
			pass
    
		#for elem in root.iter():
		#	parsedXML.append([str(elem.tag).strip(), str(elem.text).strip()])
			'''
			if elem.tag == 'filter':
				pass
			#elif elem.tag != 'li':
			#	parsedXML.append([str(elem.tag).strip(), str(elem.text).strip()])
			else:
				parsedXML.append([str(elem.tag).strip(), str(elem.text).strip()])
			#	parsedXML.append([str(elem.text).strip()])
			'''
		#parsedXML.append('!BREAK!')
		
		passedTime = time.perf_counter() - tic
		rimsheets_support.setSubProgress(
				'Scanning XML:\n{}\n{}'.format(elem, (100 - int(progress))), progress)
		'''
		rimsheets_support.setSubProgress(
				'Scanning XML:\n{}\nWorking... Please be patient this may take a while\n{}'.format(
					elem, (100 - progress * passedTime)), progress)
		'''
		#print(parsedXML)
		if re.search('ThingDefs_Misc', filename):
			with open('./out.txt', 'a') as f:
				f.write('{}\n\n'.format(parsedXML))
		#input()
		return parsedXML
	except:
		return [''] #In case some modder left an empty XML file
	

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
			modName = modName.split('/')[1]
			defType = modName
		else:
			if re.search('Steam/steamapps/common/RimWorld/Data/Core/Defs', elem):
				category = elem.split('Steam/steamapps/common/RimWorld/Data/Core/Defs/')[-1]
				category = '.'.join(category.split('/')[:-1])
			elif re.search('Steam/steamapps/common/RimWorld/Data/Royalty/Defs', elem):
				category = elem.split('Steam/steamapps/common/RimWorld/Data/Core/Defs/')[-1]
				category = '.'.join(category.split('/')[:-1])
			modName = dirName[1]
			#defType = elem.split('/')[-1]
			defType = category

		if elem.split('.')[-1] == 'xml':
			if defType not in EXCLUDED:
				if defType in dictOfDefs:
					newR = dictOfDefs[defType] + parseXML(elem, modName, progress)
					dictOfDefs[defType] = newR
				else:
					dictOfDefs[defType] = parseXML(elem, modName, progress)
			i += 1
	#input()
	return dictOfDefs


def listToChunks(filename, list_, chunkSize):
	for i in range(0, len(list_), chunkSize):
		yield [filename, list_[i : i + chunkSize]]




def toDF(filename, data, isPostponed=False):
	"""Convert parsed XML data of the same kind (eg HediffDefs) to single pandas dataframes"""
	if VERBOSE: print(filename)
	listOfDf = list()
	df = dict()
	
	#Some files (e.g. SongDefs) do not contain a 'defName' tag but are still wanted so we dump them raw
	if not isPostponed:
		listOfDicts = [[], []]
		#Break defs within XML files into individual items
		i = 0
		for each in data:
			if each != '!BREAK!':
				listOfDicts[i].append(each)
			else:
				i += 1
				listOfDicts.append([''])

		#Ran out of memory while operating on 44k df, trying to avoid that again
		if len(listOfDicts) > 10000:
				return ['postpone', filename, listOfDicts]
	else:
		listOfDicts = data

	with open('./data/{}.txt'.format(filename), 'w') as f:
		for val in listOfDicts:
			f.write('{}\n\n'.format(val))
	#Convert defs to pandas dataframes
	i = 1
	for idx, def_ in enumerate(listOfDicts):
		tic = time.perf_counter()
		for each in def_:
			try:
				df[each[0]] = each[1]	
				progress = (int(idx) * 100) / int(len(listOfDicts))
				rimsheets_support.setSubProgress('Creating {} data:\n{}\n{} / {}'.format(
					filename, each[0], idx, len(listOfDicts)), progress)
			except:
				pass
		#df['!BREAK'] = '!BREA
		listOfDf.append(pd.DataFrame(df, index=[i]))
		i += 1
		passedTime = time.perf_counter() - tic
		rimsheets_support.setProgress('Estimated time: {}'.format((100 - int(progress))), 33)
	
	#listOfDf.append(pd.DataFrame(df, index=[idx]))	
	
	try:
		result = pd.concat(listOfDf, ignore_index=True).drop_duplicates('defName').set_index('defName')
	except KeyError:
		result = pd.concat(listOfDf, ignore_index=True)
	return [filename, result]
	#TODO try to concat individual sublists
	#TODO Make sure filename isn't overwriting data due to sublist
	


def toExcel(dfList, filename):
	"""Save XML data as an Excel xlxs workbook"""
	print("{}{}.xlsx".format(OUTPUT_LOCATION, filename))
	filename = 'test1'
	#input()
	Excelwriter = pd.ExcelWriter("{}{}.xlsx".format(OUTPUT_LOCATION, filename), engine="xlsxwriter")
	#for i, df in dfList:
#		print(i)
#		df.to_excel(Excelwriter, sheet_name=str(i))
	
	try:
		for i, df in dfList:
			print(i)
			if len(i) > 31:
				i = i[:30]
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



def cleanup(dfList, modType):
	if VERBOSE: print("sorting...")
	dfList.sort(key=lambda x: x[0])
	
	toExcel(dfList, modType[1])	
	toCSV(dfList, modType[1])
	if VERBOSE: print('exporting...')
	
	#if OUTPUT_TYPE == 'xlxs':
	#	toExcel(dfList, modType[1])
	#elif OUTPUT_TYPE == 'csv':
	#	toCSV(dfList, modType[1])

	print('DONE!')
	'''
	if VERBOSE: print('Max: {}'.format(max(times)))
	if VERBOSE: print('Min: {}'.format(min(times)))
	if VERBOSE: print('Total: {}'.format(sum(times)))
	if VERBOSE: print('Average: {}'.format(sum(times) / len(times)))
	'''



def run(postponed=None):	
	if postponed:
		dfList = list()
		superlist = list(listToChunks(postponed[0], postponed[1], 10000))

		for each in superlist:
			signal.signal(signal.SIGALRM, alarm_handler)
			signal.alarm(TIMEOUT_VAL)
			try:
				df = toDF(each[0], each[1])
				if df:
					if VERBOSE: print('ON: {}'.format(df[0]))
					dfList.append(df)

			except TimeOutException:
				FAILED_FILES.append('TIME OUT ON: {}'.format(postponed[0]))
			signal.alarm(0)
				
		cleanup(dfList, postponed[0])

	else:	
		tic = time.perf_counter()
		rimsheets_support.setProgress('Collecting list of files.', 0)

		#listOfFiles = list()
		#TODO combine file lists rather than enumerate over them
		for idx, modType in enumerate(DEFS):
			#listOfFiles.append(modType)

			dfList = list()
			dictOfDefs = dict()
			if modType[1] == 'Workshop':
				postponed = list()

			if VERBOSE: print('Starting scan on {}'.format(modType[1]))	
			listOfFiles = getFileList(modType)
			
			rimsheets_support.setProgress('Extracting data package {} of {}.'.format(idx+1, len(DEFS)), 25)
			dictOfDefs = scanXML(modType, listOfFiles)

			rimsheets_support.setProgress('Converting data package {} of {}.'.format(idx+1, len(DEFS)), 50)
			
			i = 1
			for key, val in dictOfDefs.items():
				if VERBOSE: print('Converting... {} / {}'.format(i, len(dictOfDefs)))
				
				signal.signal(signal.SIGALRM, alarm_handler)
				signal.alarm(TIMEOUT_VAL)
				try:
					progress = (int(i) * 100) / int(len(dictOfDefs))
					banner = 'Parsing: {}\n{} / {}\n Working... Please be patient this may take a while.'.format(
						key, i, len(dictOfDefs))
		
					rimsheets_support.setSubProgress(banner, progress)
					df = toDF(key, val)
					if df:
						if df[0] == 'postpone':
							postponed.append([df[1], df[2]])
						else:
							if VERBOSE: print('ON: {}'.format(df[0]))
							dfList.append(df)

				except TimeOutException:
					FAILED_FILES.append('TIME OUT ON: {}'.format(key))
				signal.alarm(0)
				i += 1

			print(len(dfList))
			if not SINGLE_FILE:
				rimsheets_support.setProgress('Cleaning up.', 75)
				cleanup(dfList, modType[1])

		if SINGLE_FILE:
			rimsheets_support.setProgress('Cleaning up.', 75)
			cleanup(dfList, 'RimSheets')

	if postponed:
		for idx, each in enumerate(postponed):
			progress = (int(idx) * 100) / len(postponed)
			message = 'Large data subset {} detected\nMaking second pass on set {} of {}.'.format(each[1], idx, len(postponed)) 
			rimsheets_support.setProgress(message, progress)
			FAILED_FILES.append('TOO LARGE, SENT TO POSTPONED: {}'.format(each[1]))
			run(each)

	toc = time.perf_counter()
	ELAPSED_TIME = toc - tic

	rimsheets_support.setProgress('', 100)
	if len(FAILED_FILES) > 0:
		with open(LOG, 'w') as f:
			for each in FAILED_FILES:
				f.write('{}\n'.format(each))
		rimsheets_support.setSubProgress(
			'Done in {} seconds.\nErrors were encountered, see log for details.'.format(round(ELAPSED_TIME, 4)), 100)
	else:
		rimsheets_support.setSubProgress('Done in {} seconds.'.format(round(ELAPSED_TIME, 4)), 100)

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