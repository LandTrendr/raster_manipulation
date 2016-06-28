#!/usr/bin/env python
'''
Clip Raster. 
This routine clips a sourceFile by using a clipFile. 
If provided clipFile is a raster, it will be converted to a polygon (.shp) before clipping.
Unlike in clipRasters, the polygon is only of the 0/NonZero values in the raster

Usage: 
    clipRaster.py <source> <clip> <output> [--poly_band=<pb>] [--nodata=<n>] [--field=<f>] [--attr=<a>...] 
    clipRaster.py (-h | --help)

Options:
    -h --help               Show this screen
    --poly_band=<pb>        Band of source file to be clipped [default: 1]         
    --nodata=<n>            Specify no data value for output file 
    --field=<f>             Field name for shapefile [default: 'FIELD1']
    --attr=<a>              Attributes to be included in the cropped output
'''
import docopt, os
from osgeo import gdal, ogr, osr
import numpy

POLY_CMD_TEMP = 'gdal_polygonize.py {0} -b {1} -f "ESRI Shapefile" {2} {3} {4}'
CLIP_CMD_TEMP1 = 'gdalwarp {0} {1} -cutline {2} -crop_to_cutline -dstnodata {3} -of ENVI'
CLIP_CMD_TEMP2 = 'gdalwarp {0} {1} -cutline {2} {3} -crop_to_cutline -dstnodata {4} -of ENVI'

def main(source, clip, output, band, nodata, field, attributes):
    #convert clip raster to shapefile
    if not clip.endswith('.shp'):
        print "\nConverting raster to shapefile..."
        outDir = os.path.dirname(output) 
        
        #Read Raster and get Nonzeros
        clipfile = gdal.Open(clip)
        #projInfo = clipfile.GetProjection()
        mask = clipfile.GetRasterBand(1).ReadAsArray() != 0
        print mask.shape
        
        #Write Mask Geotiff
        driver = gdal.GetDriverByName('GTiff')
        maskfile = driver.Create('temp.tif', mask.shape[1], mask.shape[0], 1, gdal.GDT_Byte)
        geotransform = clipfile.GetGeoTransform()
        maskfile.SetGeoTransform((geotransform[0], geotransform[1], 0, geotransform[3], 0, geotransform[5]))
        maskfile.GetRasterBand(1).WriteArray(mask)
        maskfile = None
        mask = None
        
        outDir = os.path.dirname(output) 
        shapefile = os.path.join(outDir, os.path.splitext(os.path.basename(clip))[0] + '.shp')
        layer = shapefile.replace('.shp', '.lyr')
        poly_statement = POLY_CMD_TEMP.format('temp.tif', band, shapefile, layer, field)
        print "\n" + poly_statement + "\n"
        os.system(poly_statement)
        
        
        
        # Make KML shapefile
       # shapefile = os.path.join(outDir, os.path.splitext(os.path.basename(clip))[0] + '.shp')
       # spatialRef = osr.SpatialReference()
       # spatialRef.ImportFromWkt(projInfo)
       # drv = ogr.GetDriverByName("ESRI Shapefile")
       # kml_ds = drv.CreateDataSource(shapefile)
       # kml_layer = kml_ds.CreateLayer( "FIELD1", srs = spatialRef)
               
        # Polygonize
       # gdal.Polygonize(maskfile.GetRasterBand(1), maskfile.GetRasterBand(1), kml_layer, -1, [], callback=None )

        
        print "Shapefile available here: " + shapefile
    else:
        shapefile = clip

    #use shapefile to clip raster       
    if not attributes:
        clip_statement = CLIP_CMD_TEMP1.format(source, output, shapefile, nodata)
    else:
        #construct where clause if attributes specified
        query = '-cwhere "{0}={1}'.format(field, "'"+ attributes[0] +"'")
        if len(attributes) > 1:
            addQuery = " OR {0}='".format(field) + "' OR {0}='".join(attributes[1:]).format(field) + "'" + '"'
        else:
            addQuery = '"'
        query = query + addQuery
        clip_statement = CLIP_CMD_TEMP2.format(source, output, shapefile, query, nodata)

    #delete -dstnodata clause if nodata not specified
    if not nodata: clip_statement.replace(' -dstnodata None', '') 
    print "\n" + clip_statement + "\n"
    os.system(clip_statement)

  
if __name__ == '__main__':

    try:
        #parse arguments, use file docstring as parameter definition
        args = docopt.docopt(__doc__)
        #call main function
        main(args['<source>'], args['<clip>'], args['<output>'], args['--poly_band'], args['--nodata'], args['--field'], args['--attr'])

    #handle invalid options
    except docopt.DocoptExit as e:
        print e.message
