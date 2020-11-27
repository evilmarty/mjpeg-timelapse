# Mjpeg Timelapse integration for Home Assistant

[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE.md)
[![Code Style][blackbadge]][black]

[![hacs][hacsbadge]](hacs)
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

## Description

Provides a simple camera platform that captures the image for playback. This is similar to the Generic IP Camera platform but captures and stores the image periodically to playback as a MJPEG video.

## Installation

There are two ways this integration can be installed into [Home Assistant](https://www.home-assistant.io).

The easiest way is to install the integration using [HACS](https://hacs.xyz).

Alternatively, installation can be done manually by copying the files in this repository into the custom_components directory in the HA configuration directory:
1. Open the configuration directory of your HA configuration.
2. If you do not have a custom_components directory, you need to create it.
3. In the custom_components directory create a new directory called audiconnect.
4. Copy all the files from the custom_components/mjpeg_timelapse/ directory in this repository into the mjpeg_timelapse directory.
5. Restart Home Assistant
6. Add the integration to Home Assistant (see `Configuration`)

### Configuration
```
camera:
  - platform: mjpeg_timelapse
    image_url: http://example.com/foobar.gif
    fetch_interval: 30
    quality: 50
```

### Configuration Variables

**image_url**
- (string)(Required)The URL of the image.

**name**
- (string)(Optional)The name of the entity.

**fetch_interval**
- (integer)(Optional)The time interval in seconds between fetching the image. Default is 60 seconds.

**max_frames**
- (integer)(Optional)The number of frames to keep. Default is 100.

**framerate**
- (integer)(Optional)The playback framerate of the timelapse. Default is 2.

**quality**
- (integer)(Optional)The image quality between 1 and 100. Default is 75.
