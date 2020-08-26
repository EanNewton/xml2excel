#TODO choice between group by mod or by def type for workshop
#TODO pause / cancel

import os
import time
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
	for (dirpath, _, filenames) in os.walk(dirName[0]):
		listOfFiles += [os.path.join(dirpath, file) for file in filenames if fileType in file.split('.')[-1]]
	return listOfFiles


def scanXMLfiles(filename, modName, progress):
	""" Get raw data contained in XML files """
	rimsheets_support.setSubProgress('Scanning XML:\n{}'.format(filename), progress)
	try:
		tree = ET.parse(filename)
		scanned = ['!BREAK!', ['Source', modName]]
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
		return scanned
	except:
		return ['']


def parseXML(listOfFiles):
	""" Convert and categorize raw data into a python dict() """
	dictOfDefs = dict()
	i = 1
	for elem in listOfFiles:
		progress = (int(i) * 100) / int(len(listOfFiles))

		try:
			#Finding names of worksheets
			#for grouping data
			if regexpSearch('RimWorld/Data/Core/Defs', elem):
				category = elem.split('/Defs/')[-1]
				category = category.split('/')[-2]
				modName = 'Core'
			elif regexpSearch('RimWorld/Data/Royalty/Defs', elem):
				category = elem.split('/Defs/')[-1]
				category = category.split('/')[-2]
				modName = 'Royalty'
			elif regexpSearch('Steam/steamapps/workshop/content/294100/', elem):
				category = elem.split('/294100/')[-1]
				category = category.split('/')[0]
				modName = 'Workshop'
			else:
				category = elem.split('/')[-2:]
				modName = 'Custom Mod'
		except:
			if LOGGING:
				with open('./log.txt', 'a') as f:
					f.write('UnknownModException on {}\n'.format(elem))

		#Pull the data out of the file and insert to proper group / worksheet
		if elem.split('.')[-1] == 'xml' and category not in EXCLUDED:
			if category in dictOfDefs:
				newR = dictOfDefs[category] + scanXMLfiles(elem, modName, progress)
				dictOfDefs[category] = newR
			else:
				dictOfDefs[category] = scanXMLfiles(elem, modName, progress)
		i += 1

	return dictOfDefs


def toDF(filename, data, isPostponed=False):
	"""Convert parsed XML data of the same kind (eg HediffDefs) to single pandas dataframes"""
	listOfDf = list()
	df = dict()
	listOfDicts = [[], []]
	
	i = 0
	for each in data:
		if each != '!BREAK!':
			listOfDicts[i].append(each)
		else:
			i += 1
			listOfDicts.append([''])

	#Convert defs to pandas dataframes
	i = 1
	for idx, def_ in enumerate(listOfDicts):
		progress = (int(idx+1) * 100) / int(len(listOfDicts))
		for each in def_:
			try:
				df[each[0]] = each[1]	
				rimsheets_support.setSubProgress('Creating {} data:\n{}\n{} / {}'.format(
					filename, each[0], idx+1, len(listOfDicts)), progress)
			except:
				pass
			
		listOfDf.append(pd.DataFrame(df, index=[i]))
		i += 1
	
	try:
		result = pd.concat(listOfDf).drop_duplicates('defName').set_index('defName')
	except KeyError:
		try:
			if LOGGING:
				with open('./log.txt', 'a') as f:
					f.write('KeyError on {}. Trying again without \'defName\' filtering. \n'.format(filename))
			result = pd.concat(listOfDf)
			if LOGGING:
				with open('./log.txt', 'a') as f:
					f.write('Success on {}.'.format(filename))
		except:
			if LOGGING:
				with open('./log.txt', 'a') as f:
					f.write('Unknown Error on {}\n'.format(filename))
	return [filename, result]
	


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
			#In the even that two XML share a category but with different string cases
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
	return '{} hours {} minutes {} seconds'.format(hours, minutes, (round(seconds, 4)))


#The main entry point
def run():	
	ELAPSED_TIME = 0.0
	tic = time.perf_counter()
	toRun = list()

	rimsheets_support.setProgress('Collecting files to scan.', 0)
	if not SINGLE_FILE and len(DEFS) > 1:
		for each in DEFS:
			filename = '{}_{}'.format(OUTPUT_NAME, each[1])
			listOfFiles = getFileList(each)
			toRun.append([filename, parseXML(listOfFiles)])
	else:
		listOfFiles = list()
		for each in DEFS:
			listOfFiles.insert(0, getFileList(each))
		flat_list = [item for sublist in listOfFiles for item in sublist]
		toRun = [[OUTPUT_NAME, parseXML(flat_list)]]

	j = 1
	for filename, dictOfDefs in toRun:
		dfList = list()
		i = 1
		for key, val in dictOfDefs.items():
			
			try:
				progress = (int(i) * 100) / int(len(dictOfDefs))
				banner = 'Parsing\n{} / {}\n Working... Please be patient this may take a while.'.format(i, len(dictOfDefs))
		
				rimsheets_support.setProgress(banner, progress)
				df = toDF(key, val)
				if df:
					dfList.append(df)
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
	toc = time.perf_counter()
	ELAPSED_TIME = toc - tic
	rimsheets_support.setSubProgress('Done in {}.'.format(timeConvert(ELAPSED_TIME)), 100)
