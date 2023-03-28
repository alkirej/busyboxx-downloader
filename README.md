# Busyboxx Downloader
Download files from busyboxx.com and related sites.

# *** SETUP - DON'T SKIP !!! ***
1. This utility requires the **Firefox** browser and was developed 
using Ubuntu Linux

2. Examine and update the **boxx-download.ini** file
   - [SETTINGS]
     1. min-time-between-downloads-in-seconds=60
        - Wait one minute between downloads.  This is required
            because busyboxx requires no more than 5 files to
            be downloaded in 5 minutes.
     2. wait-between-pages=5
     3. wait-until-duration=15
        - These wait settings allow pauses between activities
            to allow the browser to finish its work before
            continuing.
     3. **hide-browser**=Yes
        - Default setting is **Yes**.
        - If you want to do some debugging, comment out this 
            line and the browser and the utility's interaction
            with the website(s) will be displayed on your screen.
   - [BOXX SITE URLS] 
     1. animation-boxx=www.animation-boxx.com
     2. busy-boxx=www.busyboxx.com
     3. canvas-boxx=www.canvas-boxx.com
     4. title-boxx=www.title-boxx.com
     5. wipe-boxx=www.wipe-boxx.com
     - By default, each of these sites will be visited and checked
        for downloads.  Comment out or remove the ones you do not
        need to visit.  The url's are used to reach the site in 
        question.  The option names (busy-boxx, wipe-boxx, etc.)
        are the values to use on the command line to only visit
        a single site.
   - [DIRECTORIES]
     1. base-dir=/nfs/Media-2/media-store/Graphic-Design/boxx
     - Once a file has been downloaded from a **busyboxx**
            website, it will be moved to another location.
            The utility will create a directory under this
            **base-dir** for each **busyboxx** website and
            a subdirectory under each website directory for
            each item purchased from that website.  The 
            downloaded files for that
            item will be placed within this directory.
     2. download-dir=/home/jeff/Downloads/boxx-downloads
     - This is the directory the browser will use to download files
            from **busyboxx**.  IMPORTANT: THIS DIRECTORY SHOULD
            BE RESERVED FOR THIS UTILITY'S USE ONLY!!! This 
            directory is emptied when the program is started
            and is monitored closely by the utility.  Adding
            subdirectories or files will cause problems.
     3. animation-boxx=animation-boxx
     4. busy-boxx=busy-boxx
     5. canvas-boxx=canvas-boxx
     6. title-boxx=title-boxx
     7. wipe-boxx=wipe-boxx
     - These settings are the names of the subdirectories that
        will be created under the **base-dir**.  One for each
        **busyboxx** related site.
     
3. Supply your **username** and **password** to the utility.
   - Find the **boxx-download.bash** file and edit it in your
        favorite text editor.
   - Set the value of **BOXX_USER** to your **e-mail** associated
        with your **busyboxx** account.
   - Set the value of **BOXX_PW** to your account's password.
   
# USAGE:
Execute the script from command line:
   - **boxx-download.bash \[site\] \[item\]**
      - site and item are optional arguments that can be
            used to limit the amount of work the utility
            attempts to do.  (By default, it will process
            all the boxx websites it knows about,check
            each for each item and download any that are 
            not in the correct location under **base-dir**.)
   
# ADDITIONAL NOTES:
- If you use the provided bash script, the output from the utility 
will be automatically stored into files in the working directory.
**download.out** contains the same information that the utility
displays to the screen, and **download.err** captures any
errors that occur.  In particular, it will list any files that
were unable to be downloaded.  This will allow you to manually
download one or two files if some unforeseeable problem occurs.
It is a good habit to always check this file at the conclusion
of execution.