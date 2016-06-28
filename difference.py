'''
difference.py
Script to create a difference raster stack.

Author: Tara Larrue (tlarrue2991@gmail.com)

Inputs:
- input path
- output path
- metadata description (opt.)

Output:
- raster of difference of input bands

Usage:
python difference.py {input} {output} [{metadata_description}]
'''

import sys, gdal, os
from gdalconst import *
import lthacks.intersectMask as im
from lthacks.lthacks import *

FILEPATH = os.path.abspath(__file__)

def main(input, output, metaDesc=None):

	#open raster & get info
	ds = gdal.Open(input, GA_ReadOnly)
	numBands = ds.RasterCount
	transform = ds.GetGeoTransform()
	projection = ds.GetProjection()
	driver = ds.GetDriver()
	
	#loop thru bands & calc new bands
	print "\n{0} total bands.".format(str(numBands))
	outbands = []
	
	for b in range(1,numBands+1):
	
		print "Working on band {0} of {1}...".format(str(b), str(numBands))
		
		#read band
		curr_band = ds.GetRasterBand(b)
		curr_band_array = curr_band.ReadAsArray()
		
		if b==1:
			#add zeros to first band
			zeros = np.zeros(curr_band_array.shape)
			outbands.append(zeros)
			dt = curr_band.DataType
			last_band_array = curr_band_array
			
		else:
			#add differences to all other bands
			diff = curr_band_array - last_band_array
			outbands.append(diff)
			last_band_array = curr_band_array
			
	#save raster
	im.saveArrayAsRaster_multiband(outbands, transform, projection, driver, output, dt)
	
	#save metadata
	createMetadata(sys.argv, output, description=metaDesc, 
	lastCommit=getLastCommit(FILEPATH))
			

if __name__ == '__main__':

	args = sys.argv[1:]
	
	if (len(args) != 2) and (len(args) != 3):
	
		errMsg = "\nInputs not understood. Usage:\n\npython difference.py \
		{input} {output} [{metadata_description}]"
		sys.exit(errMsg)
		
	else:
	
		sys.exit(main(*args))