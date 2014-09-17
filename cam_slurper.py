#!/usr/bin/env python

''' Do things w/ AirBeam devices; see github repo for readme '''

import yaml
import argparse
import pickle
import requests
import logging
import sys
import time
import os
from lxml import etree
from BeautifulSoup import BeautifulSoup


def setup_logging(args, config):
    ''' stdout for warning/errors, logfile for everything '''

    if args.debug:
        print 'Debugging to log file'
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(filename=config['log']['file'],
                        format=config['log']['format'],
                        datefmt=config['log']['dateformat'],
                        level=level)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    formatter = logging.Formatter(fmt=config['log']['format'],
                                  datefmt=config['log']['dateformat'])
    console.setFormatter(formatter)
    logging.getLogger('requests').propagate = False
    logging.getLogger('').addHandler(console)

    return logging

class CamSlurper:
    ''' CamSlurper object to do things w/ AirBeam devices '''

    def __init__(self, name, hostname, store_path):
        self.hostname = hostname
        self.name = name.replace(' ','_')
        self.storage_path = store_path

    def _rget(self, path):
        ''' Generic wrapper for requests get method '''
        url = self.hostname + '/' + path
        r = requests.get(url)
        if r.status_code == 200:
            return r
        else:
            logging.error('[%s] Error getting %s: -> %s' % (self.name, url, str(sys.exc_info())))

    def info(self):
        ''' Gets current info from recording device, returns JSON object of
            status items I care about '''
        r = self._rget('info')
        doc = etree.fromstring(r.content)
        out = { 'camera_status'   : doc.xpath('//camera/available')[0].text,
                'record_status'   : doc.xpath('//recording/status')[0].text,
                'record_avail'    : doc.xpath('//recording/available')[0].text,
                'record_duration' : doc.xpath('//recording/duration')[0].text,
                'device_name'     : doc.xpath('//name')[0].text
              }
        return out

    def get_duration(self):
        ''' returns duration of recording, in number of seconds '''
        info = self.info()
        time = info['record_duration']
        logging.debug('[%s] Raw Duration time: %s' % (self.name,time))
        try:
            hours, mins, secs = time.split(':')
            duration = int(secs) + (int(mins) * 60) + (int(hours) * 3600)
            logging.debug('[%s] Current Duration: %d' % (self.name,duration))
            return duration
        except:
            return 0

    def start_record(self):
        ''' Starts Recording '''
        r = self._rget('record')
        logging.info('Device [%s]: Recording Started' % self.name)
        time.sleep(10) # wait required due to start time lag on some devices

    def stop_record(self):
        ''' Stops Recording '''
        r = self._rget('stoprecord')
        logging.info('Device [%s]: Recording Stopped' % self.name)

    def start_camera(self):
        ''' Turns on the Camera (must be turned on before we record) '''
        r = self._rget('startcamera')
        logging.debug('Device [%s]: Camera Turned on' % self.name)

    def stop_camera(self):
        ''' Turns off the Camera '''
        r = self._rget('stopcamera')
        logging.info('Device [%s]: Camera Turned off' % self.name)

    def list_recordings(self):
        ''' Returns a list of recording filenames '''
        r = self._rget('recordings.html')
        html = r.content
        parsed_html = BeautifulSoup(html)
        recordings = set()
        for link in parsed_html.findAll('a'):
            l = link.get('href')
            if l.startswith('/recording/'):
                recordings.add(l.split('/')[-1])
        logging.debug('[%s] Current files: %s' % (self.name,str(recordings)))
        return recordings

    def download_recording(self, file_name):
        url = self.hostname + '/recording/' + file_name
        path = self.storage_path + '/' + self.name + '_' + str(time.time())[:10] + '_' + file_name
        with open(path, 'wb') as handle:
            response = requests.get(url, stream=True)

            if not response.ok:
                logging.error('[%s] Could not download/write file -> %s' % (self.name, sys.exc_info()))
                return 'not ok'

            for block in response.iter_content(1024):
                if not block:
                    break

                handle.write(block)
        logging.info('[%s] Downloaded file %s; saved to %s' % (self.name, file_name, path))
        return 'ok'

    def delete_recording(self, file_name):
        ''' Deletes a recording '''
        r = self._rget('delete/' + str(file_name))
        logging.info('[%s] "%s" deleted file on remote device.' % (self.name, str(file_name)))

    def get_storage_dir_size(self):
        ''' returns the size of the storage dir (in MB) '''
        total_size = 0
        p = self.storage_path
        for dirpath, dirnames, filenames in os.walk(p):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size / (1024*1024)

    def remove_oldest_file(self):
        ''' Deletes the oldest file in the storage directory, if dir size
            is greater than specified in the config '''
        files = os.listdir(self.storage_path)
        filel = []
        for f in files:
            if f.endswith('.mov'): filel.append(f)
        files = sorted(filel, reverse=True)
        delfile = self.storage_path + '/' + files[-1]
        os.remove(delfile)
        logging.info('Exceeded directory size limit. Deleted old file %s' % delfile)

def main(args, config):
    logging = setup_logging(config=config, args=args)

    while True:
        cameras = config['cameras']
        rotate  = config['rotate_duration']
        for camera in cameras:
            cname      = camera['name']
            hostname   = camera['hostname']
            store_path = camera['store_path']

            try:
                cs = CamSlurper(name=cname,
                                hostname=hostname,
                                store_path=store_path)

                logging.debug('[%s] Init.' % cs.name)

                # Make sure Camera is OK to record
                info = cs.info()
                if info['record_avail'] != 'YES': cs.start_camera()

                # Check how long we've been recording for
                duration = cs.get_duration()
                # if we're not recording, start it.
                if duration == 0:
                    logging.debug('Duration == 0')
                    cs.start_record()
                # if we hit rotate time, rotate
                elif duration > rotate:
                    logging.info('Rotating file')
                    cs.stop_record()
                    cs.start_record()

                # check the size of files in the storage directory
                cur_size = cs.get_storage_dir_size()
                while cur_size > int(config['max_dir_size']):
                    logging.debug('Current storage dir size is %d' % cur_size)
                    cs.remove_oldest_file()
                    time.sleep(1)
                    cur_size = cs.get_storage_dir_size()

                # See if there are any files to download
                files = cs.list_recordings()
                if files:
                    duration = cs.get_duration()
                    for f in files:
                        # if we're not recording, don't copy files (it will delay recording start)
                        if duration == 0:
                            continue
                        logging.info('[%s] Downloading %s' % (cs.name, str(f)))
                        resp = cs.download_recording(f)
                        if resp == 'ok':
                            cs.delete_recording(f)

                logging.debug('[%s] Sleeping' % cs.name)
                time.sleep(5)
            except KeyboardInterrupt:
                print 'Quitting'
                sys.exit(0)
            except requests.exceptions.ConnectionError:
                logging.error('[%s] Problem Connecting to Camera: %s' % (cs.name, str(sys.exc_info())))
                time.sleep(60)
            except:
                logging.error('[%s] Unhandled Exception: %s' % (cs.name, str(sys.exc_info())))
                time.sleep(60)
                continue

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''Python Script to ensure an AirBeam
        device is recording and we are downloading the recordings periodically''')
    parser.add_argument('-c', '--config', dest='config', required=True,
                        help='(Required) YAML configuration file')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Log debugging information')
    args = parser.parse_args()

    try:
        config = yaml.load(open(args.config,'r').read())
    except:
        print 'Error: could not load the config file --> "%s"' % str(sys.exc_info()[1])
        sys.exit(1)

    main(args=args, config=config)
