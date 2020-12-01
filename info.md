[![hacs][hacsbadge]](hacs)
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

## Mjpeg Timelapse

Provides a simple camera platform that captures the image for playback.

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

**loop**
- (boolean)(Optional)Loop the playback of the timelapse. Default is true.
