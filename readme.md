# pyairbeam

`pyairbeam` is a python library and script to interact with iOS/OSX devices running AirBeam ( http://appologics.com/airbeam ).

## Why?

AirBeam is an excellent and inexpensive app to easily use iOS/OSX devices for remote monitoring.
However, I wanted to export 24x7 constant video streams from AirBeam devices to my own nas/s3 setup, using
the recording device to do compression as well. Since AirBeam only allowed motion detection (which
  I found to be unreliable), this module was written to interface with the REST interface AirBeam provides.

I initially started doing this because I had extra/older iOS devices I could use for remote monitoring. However when looking at similarly capable IP cameras, I realized its actually cheaper
and lower power to buy refurbished ipod touches from Apple and use them as cameras. This allows for numerous integrations since ipod touches are running iOS.

## Whats it do?

* Connects to the remote iOS/OSX device
* Turns on the camera and starts recording
* After specified time, rotates the file
* File is compressed by the iOS/OSX device
* After compression, remote file is downloaded and stored where specified
* File storage folder is monitored to maintain a max file size; deleting the oldest files when necessary

## Requirements

In a virtualenv, `pip install -r requirements.txt`

## Config

Edit the `config.yaml`, shown below:

```
# Logfile Details
log:
    file: cam_slurper.log
    format: '[%(asctime)s] [%(levelname)s] - %(message)s'
    dateformat: '%Y-%m-%d %H:%M:%S'

# Camera details
camera:
    name: ipad2
    hostname: http://blue.local
    store_path: /Volumes/Surveillance/videos/

# how often to rotate the files (in seconds) (900 is 15 minutes)
rotate_duration: 900

# maximum size (sum of files) in store_path, in MB. oldest files will be
# deleted is size exceeds this value.
max_dir_size: 50000
```

*log:file* - path and filename for the logfile.

*log:format* - logging format. You can leave this as is.

*log:dateformat* - datetime format. You can leav this as is.

*camera:name* - a nickname for your remote device

*camera:hostname* - http path to your device w/ AirBeam running.

*camera:store_path* - location to store retrieved recorded files.

*rotation_duration* - how often to create a new recording. Recommended between 15 - 60 minutes.
Files are compressed on the remote device and large files will take up more space and take much longer to compress.

*max_dir_size* - the maximum amount of space (in MB) you want the retrieved files to take up. When this size is
surpassed, the oldest file(s) will be deleted.

## Usage

```
usage: cam_slurper.py [-h] -c CONFIG [-d]

Python Script to ensure an AirBeam device is recording and we are downloading
the recordings periodically

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        (Required) YAML configuration file
  -d, --debug           Log debugging information
```

Alternatively, import the `CamSlurper` object and write your script. The methods are self-explanatory.
The HTTP server implemented by AirBeam has no protections - everything is just a simple GET request.
Do not internet expose your devices via port-fowarding. If you wish to access this remotely, you should
setup a VPN for your network, or push the recorded files to a remote location protected by auth (i.e., google drive, s3, etc).

## TODOs / Issues

See https://github.com/jfalken/pyairbeam/issues
