from os import walk as os_walk
from os.path import join as os_join
from time import perf_counter
from pathlib import Path
from re import search as regexpSearch
import xml.etree.ElementTree as ET

import pandas as pd

import rimsheets_support

EXCLUDED = {}
DEFS = list()
LOG = './log.txt'

TIMEOUT_VAL = 0
LOGGING = True 

OUTPUT_LOCATION = './' 
OUTPUT_NAME = '' 
SINGLE_FILE = False


def getFileList(dirName, fileType='xml'): 
	listOfFiles = list()
	for (dirpath, _, filenames) in os_walk(dirName[0]):
		listOfFiles += [os_join(dirpath, file) for file in filenames if fileType in file.split('.')[-1]]
	if LOGGING:
		message = '\n'.join(listOfFiles)
		with open('./log.txt', 'a') as f:
			f.write('\n\nFILE LIST:\n')
			f.write(message)
	return listOfFiles


def scanXMLfiles(filename, modName, progress):
	""" Get raw data contained in XML files """
	rimsheets_support.setSubProgress('Scanning XML:\n{}'.format(filename), progress)
	try:
		tree = ET.parse(filename)
		scanned = [
			'!BREAK!', 
			['Source', '{}_{}'.format(modName, filename.split('/')[-1])], 
			['File Path', filename]
			]
		topleveltag = ''

		for idx, elem in enumerate(tree.iter()):
			tag = 'NaN'
			text = 'NaN'

			if idx == 1:
				topleveltag = elem.tag
			if elem.tag == topleveltag:
				#Add break tags in between each top level element
				#These become individual rows in the sheets
				scanned.append('!BREAK!')
			if elem.tag:
				tag = elem.tag.strip()
			if elem.text:
				text = elem.text.strip()
			scanned.append([tag, text])
		scanned.append('!BREAK!')
		return scanned
	except:
		return ['']


def categorizeFile(filename):
	try:
		#Finding names of worksheets for grouping data
		if regexpSearch('RimWorld/Data/Core/Defs', filename):
			category = filename.split('/Defs/')[-1]
			category = category.split('/')[-2]
			modName = 'Core'
		elif regexpSearch('RimWorld/Data/Royalty/Defs', filename):
			category = filename.split('/Defs/')[-1]
			category = category.split('/')[-2]
			modName = 'Royalty'
		elif regexpSearch('Steam/steamapps/workshop/content/294100/', filename):
			category = filename.split('/294100/')[-1]
			category = category.split('/')[0]
			modName = 'Workshop'
		else:
			category = filename.split('/')[-1]
			modName = 'Custom Mod'

		return category, modName

	except:
		if LOGGING:
			with open('./log.txt', 'a') as f:
				f.write('UnknownModException on {}\n'.format(filename))
		return None, None


def parseXML(listOfFiles):
	""" Convert and categorize raw data into a python dict() """
	dictOfDefs = dict()
	
	for idx, elem in enumerate(listOfFiles):
		progress = (int(idx) * 100) / int(len(listOfFiles))
		category, modName = categorizeFile(elem)

		#Pull the data out of the file and insert to proper group / worksheet
		if category is not None and modName is not None:
			#Sanity check but should not be needed
			if elem.split('.')[-1] == 'xml' and category not in EXCLUDED:
				if category in dictOfDefs:
					newR = dictOfDefs[category] + scanXMLfiles(elem, modName, progress)
					dictOfDefs[category] = newR
				else:
					dictOfDefs[category] = scanXMLfiles(elem, modName, progress)

	return dictOfDefs


def toDF(filename, data):
	"""Convert parsed XML data of the same kind (eg HediffDefs) to single pandas dataframes"""
	listOfDf = list()
	counters = dict()
	df = dict()
	progLength = len(data)

	for idx, each in enumerate(data):
		progress = ((int(idx) * 100) / progLength)
		banner = 'Converting:\n{}\n{} / {}'.format(filename, idx+1, progLength)
		rimsheets_support.setSubProgress(banner, progress)
		
		#Check for "!BREAK!"
		if type(each) is list:
			if each[1] != '':
				if each[0] in df:
					#counters associates multiple items across categories with a tag
					if each[0] in counters:
						counters[each[0]] += 1
					else:
						counters[each[0]] = 2
					newTMP = '{}, {}: {}'.format(df[each[0]][0], counters[each[0]], each[1])
					df[each[0]] = [newTMP]
				else:
					df[each[0]] = [each[1]]
			else:
				pass

	
		else:
			if len(df) > 0:
				listOfDf.append(pd.DataFrame.from_dict(df))
				df = dict()
				counters = dict()

	result = pd.concat(listOfDf, ignore_index=True)
	return [filename, result], progLength


def toExcel(dfList, filename):
	"""Save XML data as an Excel xlxs workbook"""
	if LOGGING:
		with open('./log.txt', 'a') as f:
			f.write("Saving: {}{}.xlsx".format(OUTPUT_LOCATION, filename))
	Excelwriter = pd.ExcelWriter("{}{}.xlsx".format(OUTPUT_LOCATION, filename), engine="xlsxwriter")

	i = 0
	for sheetName, df in dfList:
		#Excel does not support worksheet names longer than 31 characters
		if len(sheetName) > 31:
			sheetName = sheetName[:30]
		try:
			#In the event that two XML share a category but with different string cases
			#e.g. ran into Core --> 'Storyteller' and Royalty --> 'StoryTeller'
			#pandas / Excel cannot differentiate the two and throws an error
			try:
				df.to_excel(Excelwriter, sheet_name=str(sheetName))
			except:
				df.to_excel(Excelwriter, sheet_name=str('{}_{}'.format(sheetName, i)))
		except:
			#In case the user does not have disk write permission or other unknown errors
			if LOGGING:
				with open('./log.txt', 'a') as f:
					f.write('ERROR DURING WRITE OF: {}'.format(filename))
			rimsheets_support.msg_output('ERROR DURING WRITE OF: {}'.format(filename))
			
	Excelwriter.save()


#Keeping this separate from toExcel() for allowing various output types in the future
#e.g. json, xml, csv
def cleanup(dfList, filename):
	if LOGGING:
		with open('./log.txt', 'a') as f:
			f.write("Sorting: {}".format(filename))
	dfList.sort(key=lambda x: x[0])
	toExcel(dfList, filename)	


def timeConvert(seconds):
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	if hours > 0:
		banner = '{} hours {} minutes {} seconds'.format(int(hours), int(minutes), (round(seconds, 4)))
	elif minutes > 0:
		banner = '{} minutes {} seconds'.format(int(minutes), (round(seconds, 4)))
	else:
		banner = '{} seconds'.format((round(seconds, 4)))
	return banner


#The main entry point
def run():	
	ELAPSED_TIME = 0.0
	tic = perf_counter()
	toRun = list()
	elementCount = 0

	rimsheets_support.setProgress('Collecting files to scan.', 0)
	if not SINGLE_FILE and len(DEFS) > 1:
		for each in DEFS:
			filename = '{}_{}'.format(OUTPUT_NAME, each[1])
			listOfFiles = getFileList(each)
			fileCount = len(listOfFiles)
			toRun.append([filename, parseXML(listOfFiles)])
	else:
		listOfFiles = list()
		for each in DEFS:
			listOfFiles.insert(0, getFileList(each))
		flat_list = [item for sublist in listOfFiles for item in sublist]
		fileCount = len(flat_list)
		toRun = [[OUTPUT_NAME, parseXML(flat_list)]]

	j = 1
	for filename, dictOfDefs in toRun:
		dfList = list()
		i = 1
		progLength = int(len(dictOfDefs))
		for key, val in dictOfDefs.items():
			try:
				progress = (int(i) * 100) / progLength
				banner = 'Parsing\n{} / {}\n Working... Please be patient this may take a while.'.format(i, progLength)
				rimsheets_support.setProgress(banner, progress)
				
				df, count = toDF(key, val)
				if df:
					dfList.append(df)
					elementCount += count
			except:
				pass
			i += 1
		
		if not SINGLE_FILE:
			rimsheets_support.setProgress('Cleaning and exporting {} with {} sheets.'.format(filename, len(dfList)), ((j * 100) / len(toRun)))
			cleanup(dfList, filename)

	if SINGLE_FILE:
		rimsheets_support.setProgress('Cleaning and exporting {} with {} sheets.'.format(filename, len(dfList)), 100)
		cleanup(dfList, filename)

	rimsheets_support.setProgress('', 100)
	toc = perf_counter()
	ELAPSED_TIME = toc - tic
	rimsheets_support.setSubProgress('Completed {} files and {} elements in:\n{}.'.format(fileCount, elementCount, timeConvert(ELAPSED_TIME)), 100)
