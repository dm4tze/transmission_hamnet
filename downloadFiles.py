#!/usr/bin/python
# -*- coding: utf-8 -*-
# downloadFiles.py
from scipy.optimize import minimize
from datetime import date
from progress.bar import Bar, IncrementalBar
from datetime import datetime, timedelta
import sys
import subprocess
import time
import os
import settings as set
import check
#import hamnetFromGraph as hfg

FNULL = open(os.devnull, 'w')
set.readNodes()

def checkTransmissionContainer():
    FNULL = open(os.devnull, 'w')
    sum = 0
    supernode = [False] * len(set.servers)
    bar1 = IncrementalBar('Checking tracker(s)', max = len(set.servers))
    while sum < len(set.servers):
        for node in set.servers:
            if supernode[set.servers.index(node)] == False:
                if 'opentracker' in subprocess.check_output(['docker exec mn.%s docker image ls' % node],shell=True):
                    sum = sum + 1
                    supernode[set.servers.index(node)] = True
                    bar1.next()
    print ('\nTracker(s) running\n')

def downloadFile(image, iterations, outage = False, oNr = 0, oTime = 0):
    #print '1'

    for node in set.name:
        subprocess.call(['docker cp mn.%s:var/log/transmission/transmission.log measurements/%s/%s/0/time/%s.txt&' % (node, currentInstance, currentTest, node)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
    #subprocess.call(['rm -fR measurements/%s/%s/0/time/*' % (currentInstance,currentTest)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True) #root/.small-dragonfly/logs/*

    image = image.strip()

    milestone = [0] * len(set.name)
    for iteration in range(int(iterations)):


        #Tracker Restart
        #for node in set.servers:
            #subprocess.call(['docker exec mn.%s docker restart opentracker' % (node)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
        print ('\n###\nTest #%s\n###' % (iteration + 1))
        iStart = datetime.now()
        print iStart

        #checkTransmissionContainer()
        subprocess.call(['mkdir measurements/%s/%s/%s/' % (currentInstance,currentTest,(iteration + 1))],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
        subprocess.call(['mkdir measurements/%s/%s/%s/time/' % (currentInstance,currentTest,(iteration + 1))],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
        subprocess.call(['mkdir measurements/%s/%s/%s/traffic/' % (currentInstance,currentTest,(iteration + 1))],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)

        with open('measurements/%s/torrentsNr.txt' % currentInstance,'r+') as current:
            lines = current.readlines()
            torrentsNr = int(lines[-1])
            print 'Torrent #%s' % torrentsNr
        doc = open('measurements/%s/torrentsNr.txt' % currentInstance,'w+')
        doc.write(str(torrentsNr + 1)+'\n')
        doc.close()

        #delete existing file and log files on hosts
        sum = 0
        #deleted = [False] * len(set.name)
        seederPrep = [False] * len(set.seeder)
        complete = [False] * len(set.name)
        bar_restart = IncrementalBar('Deleting existing files ', max = len(set.name))
        for node in set.name:
            if not node in set.servers:
                subprocess.call(['docker exec -it mn.%s docker image rm -f %s' %(node, image)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            else:
                subprocess.call(['docker exec -it mn.%s sh -c "(docker stop opentracker && docker rm opentracker && export IP=%s && docker-compose -f stack_server.yml up -d)"' % (node, set.ip[set.name.index(node)])],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(["docker exec -it mn.%s sh -c 'rm -rf downloads/*'" % node],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(["docker exec -it mn.%s sh -c 'rm -rf torrents/*'" % node],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(["docker exec -it mn.%s sh -c 'rm -rf root/.config/transmission-daemon/resume/*'" % node],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(['docker exec -it mn.%s transmission-remote -t %s -r' % (node, str(torrentsNr))],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(["docker exec -it mn.%s sh -c 'rm -rf root/.config/transmission-daemon/torrents/*'" % node],stdout=FNULL, stderr=subprocess.STDOUT,shell=True) #root/.small-dragonfly/logs/*
            subprocess.call(["docker exec mn.%s sh -c 'iptables -Z'" % node ],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            bar_restart.next()

        print ''
        check.check()
        while check.repeat == True:
            check.check()

        bar_restart.finish()
        print ('%s deleted on every host\n' % image)



        #Prepare seeder
        #bar2 = IncrementalBar('Prepare seeder(s)', max = len(set.seeder))
        for node in set.seeder:
            if iteration == 0:
                subprocess.call(['docker exec -it mn.%s docker pull %s' %(node, image)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(['docker exec mn.%s docker save -o downloads/%s%s.tar %s' %(node, image, torrentsNr, image)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(["'docker exec mn.%s sh -c 'iptables -Z'" % node ],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)

            #bar2.next()
        #time.sleep(1)
        #bar2.finish()



        #Creating torrent and sharing torrent
        bar_sharing = IncrementalBar('Creating and sharing torrent', max = len(set.name))
        trackerAdr = ''
        for node in set.servers:
            #trackerAdr = trackerAdr + ' -t udp://' + set.ip[set.name.index(node)] + ':6969'
            trackerAdr = '%s -t udp://%s:6969' % (trackerAdr, set.ip[set.name.index(node)])

        subprocess.call(['docker exec mn.%s transmission-create -o torrents/%s%s.torrent%s downloads/%s%s.tar' % (set.seeder[0], image, torrentsNr, trackerAdr, image, torrentsNr)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
        subprocess.call(['docker cp mn.%s:torrents/%s%s.torrent measurements/%s/%s/torrents/%s%s.torrent' % (set.seeder[0], image, torrentsNr, currentInstance, currentTest, image, torrentsNr)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
        for node in set.name:
            subprocess.call(['docker cp measurements/%s/%s/torrents/%s%s.torrent mn.%s:torrents/%s%s.torrent' % (currentInstance, currentTest, image, torrentsNr, node, image, torrentsNr)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            bar_sharing.next()
        bar_sharing.finish()



        #Start download
        sum = 0
        bar_download = IncrementalBar('Waiting for download(s)', max = len(set.name))
        for node in set.name:
            subprocess.call(['docker exec mn.%s transmission-remote -a torrents/%s%s.torrent &' % (node, image, torrentsNr)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            if node in set.seeder:
                complete[set.name.index(node)] = True
                bar_download.next()
                sum = sum + 1

        #Server outage
        if outage == True:
            print ('\nWaiting %s seconds for outage...' % oTime)
            time.sleep(int(oTime))
            for i in range(int(oNr)):
                print set.servers[i]
                subprocess.call(['docker exec mn.%s docker stop opentracker &' % (set.servers[i])],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)

        while sum < len(set.name):
            time.sleep(120)
            for node in set.name:
                if complete[set.name.index(node)] == False:
                    if ('%s%s.tar' % (image, str(torrentsNr) ) in subprocess.check_output(['docker exec mn.%s ls downloads/' % node],shell=True)): #and not (file + '.part' in subprocess.check_output(['docker exec mn.' + node + ' ls downloads/'],shell=True)):
                        subprocess.call(['docker cp mn.%s:var/log/transmission/transmission.log measurements/%s/%s/%s/time/%s.txt' % (node, currentInstance, currentTest, (iteration + 1), node)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
                        with open('measurements/%s/%s/%s/time/%s.txt' % (currentInstance, currentTest, (iteration + 1), node)) as tmp:
                            lines = tmp.readlines()
                            #print
                            for i in range(milestone[set.name.index(node)],len(lines)):
                                if '%s%s.tar State changed from "Incomplete" to "Complete"' % (image, torrentsNr) in lines[i]:
                                #if not image + str(torrentsNr) + '.part' in subprocess.check_output(['docker exec mn.%s ls downloads/' % node],shell=True):
                                    sum = sum + 1
                                    complete[set.name.index(node)] = True
                                    milestone[set.name.index(node)] = i + 1
                                    bar_download.next()
                                    break
                                #subprocess.call(['docker cp mn.%s:var/log/transmission/transmission.log measurements/%s/%s/%s/time/%s.txt&' % (node, currentInstance, currentTest, iteration, node)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)

        #time.sleep(1)
        bar_download.finish()
        print 'Download(s) successful'
        for node in set.name:
            subprocess.call(["docker exec mn.%s sh -c 'iptables -L INPUT -n -v -x > tmp_IN.txt'" % node ],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(['docker cp mn.%s:tmp_IN.txt measurements/%s/%s/%s/traffic/%s_IN.txt' % (node, currentInstance, currentTest, (iteration + 1), node)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(["docker exec mn.%s sh -c 'iptables -L OUTPUT -n -v -x > tmp_OUT.txt'" % node ],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(['docker cp mn.%s:tmp_OUT.txt measurements/%s/%s/%s/traffic/%s_OUT.txt' % (node, currentInstance, currentTest, (iteration + 1), node)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(["docker exec mn.%s sh -c 'iptables -L FORWARD -n -v -x > tmp_OUT.txt'" % node ],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
            subprocess.call(['docker cp mn.%s:tmp_OUT.txt measurements/%s/%s/%s/traffic/%s_FOR.txt' % (node, currentInstance, currentTest, (iteration + 1), node)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)

        # if outage == True:
        #     time.sleep(int(oTime))
        #     for i in range(int(oNr)):
        #         subprocess.call(['docker exec mn.%s docker start opentracker' % (set.servers[i])],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)

    set.measureTime(image, False, currentInstance, currentTest, iterations, torrentsNr)
    set.measureTraffic(image, False, currentInstance, currentTest, iterations)

    doc = open('./measurements/%s/%s/results/setup.txt' % (currentInstance, currentTest), 'w+')
    doc.write('Server:%s\nHosts:%s\nSeeders:%s\nImage:%s\nServer outage:%s\nOutage number:%s\nOutage start:%s' % (str(len(set.servers)), str(len(set.name)), str(len(set.seeder)), image, outage, oNr, oTime))
    doc.close()



with open('measurements/currentInstance.txt','r+') as current:
        lines = current.readlines()
        currentInstance = str(lines[-1])
            #print torrentsNr

currentTest = datetime.strftime(datetime.now(),'%Y%m%d%H%M')
subprocess.call(['mkdir measurements/%s/%s/' % (currentInstance, currentTest)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
subprocess.call(['mkdir measurements/%s/%s/results/' % (currentInstance, currentTest)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
#subprocess.call(['mkdir measurements/%s/%s/results/time/' % (currentInstance, currentTest)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
subprocess.call(['mkdir measurements/%s/%s/0/' % (currentInstance, currentTest)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
subprocess.call(['mkdir measurements/%s/%s/0/time/' % (currentInstance, currentTest)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)
subprocess.call(['mkdir measurements/%s/%s/torrents/' % (currentInstance, currentTest)],stdout=FNULL, stderr=subprocess.STDOUT,shell=True)

testImage = raw_input("Please enter image: ")
serverOutage = set.chooseBoolean()
outageNr = 0
outageTime = 0
if serverOutage == True:
    outageNr = raw_input("Please enter number of servers to be shut down (max. %s): " % len(set.servers))
    outageNr = outageNr.strip()
    outageTime = raw_input("Please enter time in seconds when server(s) shut(s) down: ")
    outageTime = outageTime.strip()
#testNumber = raw_input("Please enter number of tests: ")
downloadFile(testImage, set.testIterations(), serverOutage, outageNr, outageTime)

#print set.testIterations()

print ('Output in: measurements/%s/%s/' % (currentInstance, currentTest))
#if set.useDownload() == True:
    #set.measureTime(testImage,True)
#else:
    #print 'Results are discarded'
#os.path.getctime(path)
#print set.name
#print ip