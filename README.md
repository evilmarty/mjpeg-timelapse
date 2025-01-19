# Mjpeg Timelapse integration for Home Assistant

[![Repository Stars](https://img.shields.io/github/stars/evilmarty/mjpeg-timelapse)](https://github.com/evilmarty/mjpeg-timelapse)
[![Github Activity](https://img.shields.io/github/commit-activity/m/evilmarty/mjpeg-timelapse)](https://github.com/evilmarty/mjpeg-timelapse/commits/main)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![BuyMeCoffee](https://badgen.net/badge/icon/buymeacoffee?icon=buymeacoffee&label&color=yellow)](https://www.buymeacoffee.com/evilmarty)

## Description

Provides a simple camera platform that captures the image for playback. This is similar to the Generic IP Camera platform but captures and stores the image periodically to playback as a MJPEG video.

## New Features

### Time Window
Specify a start and end time for when images will be captured.  Useful for capturing images every day at a specific time (e.g noon) or during working hours.
### Enabling Entity
Specify a sensor (binary_sensor, sensor, or input_text domains) that must be on (true) frames to be captured.  Example use cases include only capturing frames dring motion events or when lux is above a certain level.   Hint - use a template sensor to read another sensor such that its output is true when the desired capture conditions are met.  It's also helpful to set a high fetch_interval rate (e.g. 1 frame per second) and a high frame_rate (e.g. 15 frames per second) if only capturing frames when the enabling entity is a motion sensor, especially if you specify a short max duration (below).
### Max Duration (Minutes)
Specifying an enabling entity makes it virtually impossible to calculate the effective length of the MJPEG using frames.  When specifying an enabling entity, Max Duration effectively becomes a rolling time window. As such you can create MJPEG loops of a maximum duration that only contain images when the enabling entity is true.  If the enabling entity is false, the frames outside the current specified duration will be left intact until new frames are captured.


## Installation

There are two ways this integration can be installed into [Home Assistant](https://www.home-assistant.io).

The easiest way is to install the integration using [HACS](https://hacs.xyz).

Alternatively, installation can be done manually by copying the files in this repository into the custom_components directory in the HA configuration directory:
1. Open the configuration directory of your HA configuration.
2. If you do not have a custom_components directory, you need to create it.
3. In the custom_components directory create a new directory called mjpeg_timelapse.
4. Copy all the files from the custom_components/mjpeg_timelapse/ directory in this repository into the mjpeg_timelapse directory.
5. Restart Home Assistant
6. Add the integration to Home Assistant (see `Configuration`)

### Configuration

After you have installed the custom component (see above):

1. Goto the Configuration -> Integrations page.
2. On the bottom right of the page, click on the + Add Integration sign to add an integration.
3. Search for Mjpeg Timelapse. (If you don't see it, try refreshing your browser page to reload the cache.)
4. Click Submit so add the integration.

Alternatively, you can add entries in your `configuration.yaml` file.

```
camera:
  - platform: mjpeg_timelapse
    image_url: http://example.com/foobar.gif
    name: Example
    fetch_interval: 30
    start_time: 00:00
    end_time: 23:59:59
    max_duration_minutes: 1440 # 24 hours
    max_frames: 10
    framerate: 3
    quality: 50
    loop: false
    headers:
      X-Custom-Header: Some Value
```

### Configuration Variables

**image_url**
- (string)(Required)The URL of the image.

**name**
- (string)(Optional)The name of the entity.

**fetch_interval**
- (integer)(Optional)The time interval in seconds between fetching the image. Default is 60 seconds.

**start_time**
- (time)(Optional)The time of day to start capturing images.  Useful if you only want to capture a few frames per day at a specific time.

**end_time**
- (time)(Optional)The time of day to stop capturing images.

**enabling_entity_id**
- (string)(Optional)Sensor name (binary_sensor, sensor, or input_text) that must be on (true) for the capture to occur.
 
**max_frames**
- (integer)(Optional)The number of frames to keep. Default is 100.

**framerate**
- (integer)(Optional)The playback framerate of the timelapse. Default is 2.

**quality**
- (integer)(Optional)The image quality between 1 and 100. Default is 75.

**loop**
- (boolean)(Optional)Loop the playback of the timelapse. Default is true.

**headers**
- (boolean)(Optional)Additional headers to the image request.
