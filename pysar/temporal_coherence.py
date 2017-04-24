#! /usr/bin/env python
############################################################
# Program is part of PySAR v1.0                            #
# Copyright(c) 2013, Heresh Fattahi                        #
# Author:  Heresh Fattahi                                  #
############################################################
#
#


import sys
import os
import time
import datetime
import re

import h5py
import numpy as np

import pysar._readfile as readfile
import pysar._pysar_utilities as ut


######################################################################################################
def usage():
    print '''
***************************************************************************************
  Generates a parameter called temporal coherence for every pixel.

  Usage:
      temporal_coherence.py inteferograms_file timeseries_file [output_name]

  Example:
      temporal_coherence.py Seeded_unwrapIfgram.h5 timeseries.h5
      temporal_coherence.py Seeded_unwrapIfgram.h5 timeseries.h5 temporalCoherence.h5

  Reference:
      Tizzani, P., P. Berardino, F. Casu, P. Euillades, M. Manzo, G. P. Ricciardi, G. Zeni,
      and R. Lanari (2007), Surface deformation of Long Valley Caldera and Mono Basin, 
      California, investigated with the SBAS-InSAR approach, Remote Sens. Environ., 108(3),
      277-289, doi:10.1016/j.rse.2006.11.015.

      Gourmelen, N., F. Amelung, and R. Lanari (2010), Interferometric synthetic aperture
      radar-GPS integration: Interseismic strain accumulation across the Hunter Mountain 
      fault in the eastern California shear zone, J. Geophys. Res., 115, B09408, 
      doi:10.1029/2009JB007064.

***************************************************************************************
    '''


######################################
def main(argv):
    try:
        ifgramFile     = argv[0]
        timeSeriesFile = argv[1]
    except:
        usage() ; sys.exit(1)

    try:    tempCohFile = argv[2]
    except: tempCohFile = 'temporalCoherence.h5'

    ########################################################
    #print '\n********** Temporal Coherence ****************'
    print "load time series: "+timeSeriesFile
    atr_ts = readfile.read_attribute(timeSeriesFile)
    h5timeseries = h5py.File(timeSeriesFile)
    dateList = h5timeseries['timeseries'].keys()
    numDates = len(dateList)

    print 'number of acquisitions: '+str(numDates)
    dateIndex={}
    for ni in range(numDates):
        dateIndex[dateList[ni]]=ni 

    dset = h5timeseries['timeseries'].get(h5timeseries['timeseries'].keys()[0])
    nrows,ncols = np.shape(dset)
    timeseries = np.zeros((len(h5timeseries['timeseries'].keys()),np.shape(dset)[0]*np.shape(dset)[1]),np.float32)

    for i in range(numDates):
        date = dateList[i]
        dset = h5timeseries['timeseries'].get(date)
        d = dset[0:dset.shape[0],0:dset.shape[1]]
        timeseries[dateIndex[date]][:]=d.flatten(0)
        ut.print_progress(i+1,numDates,'loading:',date)
    del d
    h5timeseries.close()

    lt,numpixels=np.shape(timeseries)
    range2phase = -4*np.pi/float(atr_ts['WAVELENGTH'])
    timeseries = range2phase*timeseries

    ######################################################
    print "load interferograms: " + ifgramFile
    atr_ifgram = readfile.read_attribute(ifgramFile)
    h5ifgram   = h5py.File(ifgramFile)  
    ifgramList = sorted(h5ifgram['interferograms'].keys())
    ifgramList = ut.check_drop_ifgram(h5ifgram, atr_ifgram, ifgramList)
    date12_list = [str(re.findall('\d{6}-\d{6}', i)[0]) for i in ifgramList]
    numIfgrams = len(ifgramList)
    print 'number of interferograms: '+str(numIfgrams)
    A,B = ut.design_matrix(ifgramFile, date12_list)
    p   = -1*np.ones([A.shape[0],1])
    Ap  = np.hstack((p,A))

    print 'calculating temporal coherence ...'
    try:
        ref_x = int(atr_ts['ref_x'])
        ref_y = int(atr_ts['ref_y'])
        print 'find reference pixel in y/x: [%d, %d]'%(ref_y, ref_x)
    except ValueError:
        print 'No ref_x/y found! Can not calculate temporal coherence without it.'
    
    #data = np.zeros((numIfgrams,numpixels),np.float32)
    qq = np.zeros(numpixels)+0j
    for ni in range(numIfgrams):
        ## read interferogram
        igram = ifgramList[ni]
        data = h5ifgram['interferograms'][igram].get(igram)[:]
        data -= data[ref_y, ref_x]
        data = data.flatten(0)

        ## calculate difference between observed and estimated data
        ## interferogram by interferogram, less memory, Yunjun - 2016.06.10
        dataEst  = np.dot(Ap[ni,:], timeseries)
        dataDiff = data - dataEst
        qq += np.exp(1j*dataDiff)

        ## progress bar
        ut.print_progress(ni+1,numIfgrams,'calculating:',igram)
    del timeseries, data, dataEst, dataDiff
    h5ifgram.close()

    #qq=np.absolute(np.sum(np.exp(1j*dataDiff),0))/numIfgrams
    qq = np.absolute(qq)/numIfgrams
    Temp_Coh=np.reshape(qq,[nrows,ncols])

    ##### write temporal coherence file ####################
    print 'writing >>> '+tempCohFile
    h5TempCoh = h5py.File(tempCohFile,'w')
    group=h5TempCoh.create_group('temporal_coherence')
    dset = group.create_dataset(os.path.basename('temporal_coherence'), data=Temp_Coh, compression='gzip')
    for key , value in atr_ts.iteritems():
        group.attrs[key]=value
    group.attrs['UNIT'] = '1'
    h5TempCoh.close()


######################################################################################################
if __name__ == '__main__':
    main(sys.argv[1:])


