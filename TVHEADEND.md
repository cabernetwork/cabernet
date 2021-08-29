## tvheadend-locast
You have found the tvheadend-locast README. 
To allow for easy insertion of the locast2plex baseline, most of the top level files are directly from locast2plex including the main README.md.

Additional information is provided on the [Wiki](https://github.com/rocky4546/tvheadend-locast/wiki) pages.

### Purpose:
This application has two primary purposes along with many minor updates.  

The first purpose is to provide a TVHeadend interface which allows for automatic population of the mux, services and EPG with a standard naming convention, so that, the channels will map the EPG to the services correctly and provide automated updates as needed.

Second, is to update the application to support the free locast account version with TVHeadend.

### Relationship to locast2plex:
The application is setup to use most of the locast2plex software.  As fixes are addressed in that project, those changes are folded into this application. Key areas, such as, managing the cached files and station lists, logging into locast, using Docker and supporting SSDP are all maintained by locast2plex.

### Use of ffmpeg software
There are many locast interface applications popping up everywhere; many try to not use ffmpeg executables.  Although python could do what ffmpeg does, it would be slower and use more CPU.  Since it should be available on Linux systems and we have addressed it on Windows, use of this executable should not be an issue.  One solution for subscription-based accounts is to detect if ffmpeg is not present and then to use a python-based method for streaming the data to the end device.

### Important Legal Notice:
As stated by locast2plex.  Do not use this product in an illegal way to obtain channels outside of your general market area.  To have locast continue broadcasting and to have this product available is to use it legally.

### Developers Notes:
Pull requests are welcome.  If you cannot submit a PR, then write an issue/enhancement with as much detail as possible and it will be reviewed.

### Submitting Issues/Enhancements
All issues will be triaged and labeled.  Before writing an issue, check the issue list for duplicates to see if there are any fixes for similar issues.  If you are not sure, write a new issue.  The issue may be associated with locast2plex software.  In this case, it will be determined whether we can make the fix or have you follow up with locast2plex.  Initially, add as much detail as possible to reproduce the issue.  Logs, hardware and OS info is not important up front, but may be requested based on the issue.

When posting logs, you can turn the locast2plex logging off by setting the [main][quiet_print] setting to True.  This should remove most of the sensitive information.  Always review any data you post for sensitive info before you post.

## Credits
Thank you to all the people at [locast2plex](https://github.com/tgorgdotcom/locast2plex) for creating the initial product.
