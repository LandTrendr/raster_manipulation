#!/usr/bin/env python
'''
Replace Pixel Value.

Usage:
  replacePixelValue.py <input> <output> <operators> <invals> <outvals> [--meta=<m>] [--inband=<b>...] [--calcmap=<cm>] [--calcband=<cb>]
  replacePixelValue.py -h | --help
  
Options:
  -h --help             Show this screen.
  --inband=<b>          Band(s) of source file to apply calcs.
  --meta=<m>			Additional notes for meta.txt file.
  --calcmap=<cm>		Map to base operators on if different from input map.
  --calcband=<cb>		Band to base operators on if not all bands of calcmap.
'''
import sys, os, gdal
import numpy as np
from gdalconst import *
from lthacks.lthacks import *
from lthacks.intersectMask import *
import docopt
import functools

def combine2(f, g):
		return lambda x: f(x) & g(x)

def combine(*functions):
	return functools.reduce(combine2, functions)

def getFunction(operator_string, value_string):

	operator_string=operator_string.strip().lower()
	op_strings = operator_string.split("+")

	value_string=value_string.strip().lower()
	val_strings = [float(i) for i in value_string.split("+")]

	strings = zip(op_strings, val_strings)

	functions = []
	for string in strings:

		operator = string[0]
		value = string[1]

		if operator == ">":
			def func(anarray, value=value):
				return (anarray > value)

		elif operator == "<":
			def func(anarray, value=value):
				return (anarray < value)

		elif (operator == "<=") or (operator == "=<"):
			def func(anarray, value=value):
				return (anarray <= value)

		elif (operator == ">=") or (operator == "=>"):
			def func(anarray, value=value):
				return (anarray >= value)

		elif (operator == "=") or (operator == "=="):
			def func(anarray, value=value):
				return (anarray == value)

		elif (operator == "!=") or (operator == "=!"):
			def func(anarray, value=value):
				return (anarray != value)		

		else:
			raise NameError("Operator input not understood:" + operator)

		functions.append(func)

	combined = combine(*functions) 

	return combined


def main(inputds, inputbands, output, operators, invals, outvals,
 calcmap=None, calcband=None, meta=None):
	
	replacements = zip(operators, invals, outvals)
	replace_list = []
	for replacement in replacements:
		func = getFunction(replacement[0], replacement[1])
		replace_list.append({'function': func,
							 'outvalue': replacement[2]})

	#get input raster info
	projection = inputds.GetProjection()
	transform = inputds.GetGeoTransform()
	driver = inputds.GetDriver()
	numbands = inputds.RasterCount
	dt = inputds.GetRasterBand(1).DataType
	
	#read calculation raster if exists
	if calcmap:
		print "\nApplying operators to map: '" + calcmap + "'"
		calcds = gdal.Open(calcmap, GA_ReadOnly)
		if calcband:
			print "\tBand " + str(calcband)
			calcband = calcds.GetRasterBand(int(calcband))
			calcdata = calcband.ReadAsArray()
			calc_data_set = True
		else:
			calc_data_set = False
			print "\tAll bands."

	else:
		if calcband:
			print "\nApplying operators to input map."
			print "\tBand " + str(calcband)
			calcband = inputds.GetRasterBand(int(calcband))
			calcdata = calcband.ReadAsArray()
			calc_data_set = True
		else:
			calc_data_set = False
			calcdata = None
			print "\nApplying operators to input map."
			print "\tAll bands."
	
	#initialize output
	outdata = [0]*numbands
	
	#loop thru bands & replace values
	for b in range(1, numbands+1):
		
		print "\nWorking on input band {0}...".format(str(b))

		#if current band is not included in input bands, return band as is
		if b not in inputbands:

			inband = inputds.GetRasterBand(b)
			indata = inband.ReadAsArray()
			outdata[b-1] = indata
			del indata
			continue
	
		for i,item in enumerate(replace_list):
	
			print "\tWorking on converting from ", operators[i], invals[i], " to ", item['outvalue'], " ..."

			#determine if this is the first replacement
			if i == 0:	
			
				inband = inputds.GetRasterBand(b)
				indata = inband.ReadAsArray()
				origdata = indata
		
			else:
			
				indata = outdata[b-1]
				
			#determine data to apply replacement operator
			if not calc_data_set:
				if not calcmap:
					calcdata = origdata
				else:
					calcband = calcds.GetRasterBand(b)
					calcdata = calcband.ReadAsArray()

			#locate pixels to replace
			bools = item['function'](calcdata)

			#replace those pixels with specified out value
			indata[bools] = item['outvalue']

			#save band
			outdata[b-1] = indata
			del indata
		
	#save new arrays as a (multiband) raster
	saveArrayAsRaster_multiband(outdata, transform, projection, driver, output, dt)
	
	#save a metadata file
	fullpath = os.path.abspath(__file__)
	createMetadata(sys.argv, output, description=meta, lastCommit=getLastCommit(fullpath))
	
	
if __name__ == '__main__':

    try:
        #parse arguments, use file docstring as parameter definition
		args = docopt.docopt(__doc__)
		
		#format arguments
		operators = args['<operators>'].split(",")
		invals = args['<invals>'].split(",")
		outvals = [float(i) for i in args['<outvals>'].split(",")]
		
		inputds = gdal.Open(args['<input>'], GA_ReadOnly)
		numbands = inputds.RasterCount
		
		if not args['--inband']:
			inputbands = range(1,numbands+1)
		else:
			inputbands = [int(i) for i in args['--inband']]
			
		try:
			calcband = int(args['--calcband'])
		except TypeError:
			calcband = None

		#call main function
		main(inputds, inputbands, args['<output>'], operators, invals, outvals, 
		calcmap=args['--calcmap'], calcband=calcband, meta=args['--meta'])

    #handle invalid options
    except docopt.DocoptExit as e:
        print e.message
	