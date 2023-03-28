"""
MODULE: boxx-download.py
"""
import glob
import os
import shutil
import sys
import time

from configparser import ConfigParser, NoOptionError
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

CONFIG = ConfigParser()
CONFIG.read("boxx-download.ini")

SECTION_SETTINGS = "SETTINGS"
SECTION_LOGIN = "LOGIN"
SECTION_URLS = "BOXX SITE URLS"
SECTION_DIRS = "DIRECTORIES"

DUR_BETW_PGS = int(CONFIG.get(SECTION_SETTINGS, "wait-between-pages"))
DUR_WAIT_UTL = int(CONFIG.get(SECTION_SETTINGS, "wait-until-duration"))
DUR_BETW_DLS = int(CONFIG.get(SECTION_SETTINGS, "min-time-between-downloads-in-seconds"))

BOXX_SITES = CONFIG.options(SECTION_URLS)

VISIBLE_MSG = "Starting browser in VISIBLE mode."


def print_error(*args, **kwargs):
    """ Print to standard error. Use the same as print() """
    print(*args, **kwargs)
    print(*args, file=sys.stderr, **kwargs)


def login(browser: webdriver, boxx_site: str) -> None:
    """
    Login the user to the appropriate boxx website.
    NOTE: the username is retrieved from the BOXX_USER environment variable
          and the password is retrieved from the BOXX_PW environment var.

    param browser: the browser object to interact with the website.
    param boxx_site: the boxx_site to download. (Used to lookup website url)
    """
    # SET BROWSER TO THE LOGIN FORM
    print("Begin login ...")
    url = "https://" + CONFIG.get(SECTION_URLS, boxx_site) + "/Login/"
    browser.get(url)
    time.sleep(2)

    # ENTER USER'S E-MAIL INTO THE LOGIN FORM
    try:
        user_field = browser.find_element("id", "EmailAddressTextBox")

        user_field.clear()
        user = os.environ["BOXX_USER"]
        user_field.send_keys(user)

    except KeyError:
        print("Could not find environment variable BOXX_USER.")
        print("  Please set to e-mail address associated with your Boxx account(s).")
        sys.exit(1)

    # ENTER USER'S PASSWORD INTO LOGIN FORM
    try:
        pwd_field = browser.find_element("id", "LoginPasswordTextBox")
        pwd = os.environ["BOXX_PW"]
        pwd_field.clear()
        pwd_field.send_keys(pwd)

    except KeyError:
        print("Could not find environment variable BOXX_PW.")
        print("  Please set to the password associated with your Boxx account(s).")
        sys.exit(1)

    # SIGN USER INTO THE SITE BY CLICKING THE SIGN IN BUTTON
    login_btn = browser.find_element(By.ID, "SignInButton")
    login_btn.click()
    time.sleep(DUR_BETW_PGS)
    print("Login complete.")


def get_item_download_pages(browser: webdriver) -> [(str, str)]:
    """
    Each purchased item has a page that lists each downloadable file. Get
    the list of such pages.  This requires the browser to currently be pointing to
    the "My Downloads" page.

    param browser: browser object that interacts with the browser for us.
    return: list of pairs.  Each pair is the url for the file to download and
                the name of the directory to save the file into.
    """
    # TRACK DOWNLOADABLE ITEMS IN THESE LISTS
    download_urls = []
    item_names = []

    # SEND BROWSER TO "MY DOWNLOADS" PAGE.
    print("Following My Downloads link ...")
    download_lnk = WebDriverWait(browser, timeout=DUR_WAIT_UTL).until(
        lambda br: br.find_element(By.LINK_TEXT, "My Downloads")
    )

    download_lnk.click()
    time.sleep(DUR_BETW_PGS)

    # EACH PURCHASED ITEM HAS A DOWNLOAD PAGE TO ALLOW DOWNLOAD
    # THE FILES ASSOCIATED WITH THE PURCHASE.
    #
    # GET THE URLS FOR EACH OF THOSE PAGES
    elems = browser.find_elements(By.TAG_NAME, "a")
    for elem in elems:
        href = elem.get_attribute('href')
        if href is not None:
            if "|" in href:
                new_href = href.replace("boxx.com/0~", "boxx.com/Downloads?path=0~")
                download_urls.append(new_href)

    # GET THE NAME OF EACH PURCHASED ITEM
    elems = browser.find_elements(By.CLASS_NAME, "contentsToDisplay")
    for elem in elems:
        volume = int(elem.find_element(By.CLASS_NAME, "ContentExtraInfoSuperTitle").text
                     .replace("VOLUME ", "").replace(":", "")
                     )
        item = elem.find_element(By.CLASS_NAME, "TitleText").text.lower().replace(" ", "-")
        item_names.append(f"{volume:03d}-{item}")

    # RETURN A LIST OF PAIRS (URL AND ITEM NAME)
    #   ONE FOR EACH DOWNLOAD PAGE FOUND.
    return zip(download_urls, item_names)


def element_found(browser: webdriver, class_name: str) -> [WebElement]:
    """
    Look for a specific class of element on the current page of the browser.
    If none is found, intercept the exception and return None

    param browser: object to interact with the browser for us.
    param class_name: Class name of objects to search for.
    return: A list of the elements of the given class or None if none
                are found.
    """
    try:
        return browser.find_elements(By.CLASS_NAME, class_name)
    except NoSuchElementException:
        return None


def download_page_found(browser: webdriver) -> [WebElement]:
    """ Search for DownloadPageText class objects """
    return element_found(browser, "DownloadPageText")


def wait_for_download_to_complete() -> int:
    """
    Ensure the download is complete.  This is done by checking for
    a file with the extension of .part.  If a .part file exists, then
    the download is not complete.

    In that case log the info, wait and check again and again ...

    return: The number of files in the download directory once
                the download is complete.
    """
    # VARIABLE SETUP
    complete = False
    dl_dir = CONFIG.get(SECTION_DIRS, "download-dir")

    # LOOP UNTIL DOWNLOAD IS COMPLETE
    while not complete:
        complete = True
        files = os.listdir(dl_dir)
        for filenm in files:
            if ".part" in filenm:
                print(f"      *** Waiting for download: {filenm} ***")
                time.sleep(DUR_WAIT_UTL)
                complete = False

    # RETURN THE NUMBER OF FILES IN THE DOWNLOAD DIR
    #   AFTER THE DOWNLOAD IS COMPLETE.  (1 IS GOOD,
    #   0 MEANS NOTHING WAS DOWNLOADED, AND 2+ MEANS
    #   WE HAVE AN EXTRA FILE WE SHOULD NOT HAVE).
    return len(os.listdir(dl_dir))


def clean_download_dir() -> None:
    """ Remove all .part files from the download directory before """
    try:
        # FIND DOWNLOAD TO DIRECTORY FROM CONFIG SETTINGS
        dl_dir = CONFIG.get(SECTION_DIRS, "download-dir")
        print("Empty the download directory. (", dl_dir, ")")

        # FIND ALL FILES IN THE DOWNLOAD DIRECTORY AND DELETE THEM.
        dir_cnts = os.listdir(dl_dir)
        for pth in dir_cnts:
            full_pth = os.path.join(dl_dir, pth)
            if os.path.isfile(full_pth):
                print("  -- deleting", pth, "from", dl_dir)
                os.remove(full_pth)
        print("Download directory is now empty.")

    except FileNotFoundError:
        # No files?  Nothing to do as we want the directory void of files.
        pass


def process_download(browser: webdriver, save_to: str, boxx_site: str, save_filename: str) -> None:
    """
    Wait for the download to complete, then move the newly downloaded file to
    the destination directory

    param browser: object to interact with the browser
    param save_to: The name of the individual item from the boxx site.
    param boxx_site: Which boxx website is the download from.
    param save_filename: Name to give the file once it is moved.
    """
    # BUSYBOXX LIMITS DOWNLOADS TO AVOID OVERTAXING THEIR SERVERS.
    # WAIT LONG ENOUGH TO MEET THERE GUIDELINES (CURRENTLY NO MORE
    # THAN 5 DOWNLOADS IN 5 MINUTES).  THIS ALSO GIVES THE FILE ENOUGH
    # TIME TO DOWNLOAD.
    time.sleep(DUR_BETW_DLS)

    # WAIT FOR DOWNLOAD
    dl_cnt = wait_for_download_to_complete()

    # CHECK THE NUMBER OF DOWNLOAD FILES. IF IT IS NOT 1, WE HAVE
    # AN ERROR.  CURRENTLY, WE HALT DOWNLOADS AND EXIT PROGRAM.
    # ALTERNATE POSSIBILITY WOULD BE TO LOG THE PROBLEM AND CONTINUE
    # ON TO THE NEXT FILE.
    if dl_cnt != 1:
        print(f"    DOWNLOADING ERROR. {dl_cnt} FILES FOUND (1 expected)")
        print_error(f"FAIL: {boxx_site.upper()} {save_to} {save_filename}")

        # Maybe: track files that could not be downloaded to inform
        #   the user of later and CONTINUE to next file.
        # browser.quit()
        # sys.exit(1)

    # DOWNLOAD APPEARS TO BE SUCCESSFUL. MOVE THE DOWNLOAD INTO
    # THE PERMANENT STORAGE LOCATION WHICH WILL LEAVE THE DOWNLOAD
    # DIRECTORY EMPTY AGAIN.
    else:
        print(f"      - Moving download to {build_save_location(boxx_site, save_to, save_filename)}")
        rename_and_move_dl_file(save_to, boxx_site, save_filename)


def download_item_files(browser: webdriver, url: str, boxx_site: str, item_name: str) -> None:
    """
    Download all files from the current "item".
        I know the function is kinda long, but IO tends to do that.

    param browser: object to interact with the browser for us
    param url: url for the item to download.  Each "item" will have many downloadable files.
    param boxx_site: which boxx site to visit?
    param item_name: the name of this item which becomes the name of the directory to
                    save the file(s) into.
    """
    # POINT THE BROWSER AT THE PROPER PAGE TO DOWNLOAD FILES FOR
    # THE PURCHASE WE ARE PROCESSING.
    browser.get(url)

    # WAIT UNTIL THE PAGE DOWNLOADS
    dl_elems = WebDriverWait(browser, timeout=DUR_WAIT_UTL).until(download_page_found)

    # PROCESS EACH ITEM FROM THE DOWNLOAD PAGE
    for dl_elem in dl_elems:
        # GET INFO TO USE IN FILE'S NAME SO IT CAN BE EASILY FOUND
        ttl = dl_elem.find_element(By.CLASS_NAME, "TitleText").text.lower().replace(" ", "-")
        cnt_name = dl_elem.find_element(By.CLASS_NAME, "Contentname").text.lower().replace(" ", "")
        dur = dl_elem.find_element(By.CLASS_NAME, "Duration").text.lower().replace(" : ", "")

        # EACH ITEM HAS AN SVG IMAGE THAT MUST BE CLICKED.
        # ONCE CLICKED, A LIST OF DOWNLOADS FOR THIS MEMBER OF OUR PURCHASE
        # WILL BE LISTED.
        dl_img = dl_elem.find_element(By.TAG_NAME, "svg")

        # CLICK BUTTON TO BRING UP DOWNLOADS FOR ITEM MEMBER
        dl_img.click()
        time.sleep(2)

    # COLLECT THE DOWNLOADS FOR THIS ITEM MEMBER.
        item_wrappers = browser.find_elements(By.CLASS_NAME, "DescriptionWrapper")

        # SOME OF THE PURCHASES ONLY HAVE A SINGLE FILE FOR EACH
        # ITEM MEMBER.  WHEN THAT IS THE CASE, THE DOWNLOAD WILL
        # START IMMEDIATELY.  THESE CASES REQUIRE SLIGHTLY DIFFERENT
        # PROCESSING
        if len(item_wrappers) > 0:
            downloads = []

            # COLLECT LIST IF FILES TO DOWNLOAD
            for elem in item_wrappers:
                descr = elem.find_element(By.CLASS_NAME, "ContentInfo").text.lower().replace(" ", "-")
                save_filename = f"{ttl}-{cnt_name}-{dur}-{descr}"
                downloads.append((save_filename, elem))

            # DOWNLOAD EACH FILE FOR THIS ITEM MEMBER
            for filename, elem in sorted(downloads):
                print(f"    Downloading: {filename} ...")
                if not file_exists(boxx_site, item_name, filename):
                    # THE FILE WAS NOT PREVIOUSLY DOWNLOADED, SO
                    # CLICK TO DOWNLOAD THE FILE THEN PROCESS IT
                    # (AKA: MOVE IT TO ITS PERMENANT LOCATION)
                    elem.click()
                    time.sleep(2)
                    process_download(browser, item_name, boxx_site, filename)

                else:
                    # THE FILE HAS ALREADY BEEN DOWNLOADED.  HOORAY!
                    # WE CAN MOVE ON THE THE NEXT FILE.
                    print("      - already exists, skipping download.")

        # THIS ITEM MEMBER ONLY HAS A SINGLE FILE TO DOWNLOAD
        else:
            filename = f"{ttl}-{cnt_name}-{dur}"
            print(f"    Downloading single: {filename} ...")

            if not file_exists(boxx_site, item_name, filename):
                process_download(browser, item_name, boxx_site, filename)

            else:
                # FILE PREVIOUSLY DOWNLOADED, SKIP TO NEXT FILE.
                print("      - already exists, skipping single download.")


def build_save_location(boxx_site: str, item_name: str, save_file: str) -> str:
    """
    Generate the final resting place and name of the downloaded file.
    ASSUMPTION: there is a single file in the browser's download
        directory, AND this is the most recent download that will
        be saved elsewhere.

    param boxx_site: The specifix busy-boxx site (and product type)
    param item_name: Name of the purchased item
    param save_file: Base name for the file when it is renamed.
    return: The full path to save the file into permanently.
    """
    # GET THE NAME OF THE FILE THE BROWSER DOWNLOADED.  IT WILL BE
    # THE ONLY FILE IN THE DOWNLOADS DIRECTORY.
    dl_filename = get_downloaded_filename()

    # GET THE EXTENSION OF THE DOWNLOAD FILE AND USE IT FOR THE STORED FILE
    file_ext = dl_filename[dl_filename.find("."):]

    # GET THE PATH TO STORE THE FILE IN
    dst_dir = get_save_dir(boxx_site, item_name)

    # RETURN THE FULL PATH TO STORE THE FILE
    return os.path.join(dst_dir, save_file) + file_ext


def get_downloaded_filename() -> str:
    """
    Look into the browser's download directory (check the .ini file
    for "download-dir" in the "DIRECTORIES" section) and return the
    name of the first file you find there.  There should only be a
    single file.

    return: The filename of the file in the download dir OR None
                if it empty for some reason.
    """
    # FIND BROWSER'S DOWNLOAD DIR
    dl_dir = CONFIG.get(SECTION_DIRS, "download-dir")

    # GET A LIST OF ALL FILES IN THE DOWNLOAD DIR
    files = os.listdir(dl_dir)

    # RETURN THE NAME OF THE FIRST FILE FOUND OR NONE IF IT IS EMPTY
    if len(files) > 0:
        return files[0]
    else:
        return None


def rename_and_move_dl_file(item_name: str, boxx_site: str, save_name: str) -> None:
    """
    Move a file from the downloaded location to the permanent storage location.
    Rename the file from the browser chosen filename into a longer, more
    descriptive name in the process.

    param item_name: The name of the individual item from the boxx site.
    param boxx_site: Which boxx website is the download from.
    param save_name: Name to give the file once it is moved.
    """
    # FIND THE FULL PATH TO THE DOWNLOADED FILE
    dl_dir = CONFIG.get(SECTION_DIRS, "download-dir")
    src_filenm = os.path.join(dl_dir, get_downloaded_filename())

    # CALCULATE THE PATH TO MOVE THE DOWNLOADED FILE TO
    dst_filenm = build_save_location(boxx_site, item_name, save_name)

    # MOVE THE FILE
    shutil.move(src_filenm, dst_filenm)


def start_browser() -> webdriver:
    """
    Start the web browser.
    return: the web browser object to allow program to interact with browser.
    """
    # FIND THE DOWNLOAD DIR FOR THE BROWSER TO USE
    dl_dir = CONFIG.get(SECTION_DIRS, "download-dir")

    # SETUP THE BROWSER'S OPTIONS
    opts = Options()
    try:
        # SET HEADLESS USAGE ON OR OFF BASED ON CONFIG
        if "yes" == CONFIG.get(SECTION_SETTINGS, "hide-browser").lower():
            print("Starting browser in HEADLESS (invisible) mode.")
            opts.add_argument("-headless")
        else:
            print(VISIBLE_MSG)

    except NoOptionError:
        print(VISIBLE_MSG)

    # THIS OPTION TELL FIREFOX TO USE A USER SPECIFIED DIRECTORY
    # FOR DOWNLOADS
    opts.set_preference("browser.download.folderList", 2)

    # THIS ONE SPECIFIES THE DIRECTORY
    opts.set_preference("browser.download.dir", dl_dir)

    # START THE BROWSER AND RETURN THE OBJECT FOR FUTURE INTERACTIONS
    return webdriver.Firefox(options=opts)


def ensure_save_dir_exists(boxx_site: str, item: str) -> bool:
    """
    Make sure the directory to save items from this item exists.
    param boxx_site: first directory under the save dir is for the specific boxx site
    param item: the 2nd dir under the save dir is for the individual item
                    from the individual boxx site.
    return: true if the directory previously existed.
    """
    pth = Path(get_save_dir(boxx_site, item))
    exist_before = os.path.exists(pth)
    pth.mkdir(parents=True, exist_ok=True)

    # AN EXISTING, BUT EMPTY DIRECTORY IS CONSIDERED NOT EXISTING.
    if exist_before:
        file_list = os.listdir()
        exist_before = len(file_list) > 0

    return exist_before


def file_exists(boxx_site: str, item: str, filename: str) -> bool:
    """
    Does the file for this file already exist?

    param boxx_site: Boxx website the item is from
    param item: the item's name - used as a dir name for saving
    param filename: name of the file withing the <item> dir.
    return: True if the file already exists (and, therefore doesn't
                need to be downloaded).
    """
    dst_dir = get_save_dir(boxx_site, item)
    path = os.path.join(dst_dir, filename) + ".*"
    filenames = glob.glob(path)
    return len(filenames) > 0


def get_save_dir(boxx_site: str, item: str) -> str:
    """
    Given a specific boxx website and an item name from that site, return
    the full path of the directory these files are to be saved into.
    param boxx_site: the boxx website the files are downloaded from
    param item: the name of the individual item from the site
    return: full path to save files into
    """
    save_dir = CONFIG.get(SECTION_DIRS, "base-dir")
    return f"{save_dir}/{boxx_site}/{item}"


def usage() -> None:
    """ Display simple usage to stdout and exit program. """
    print("USAGE:")
    print("  boxx-download.bash [site] [product]")
    print()
    print("EXAMPLES:")
    print("  boxx-download.bash")
    print("  boxx-download.bash title-boxx")
    print("  boxx-download.bash busy-boxx 005-modern-titles")
    print()
    sys.exit(1)


def verify_boxx_site(site: str) -> None:
    """
    Verify the provided site is a valid boxx site.  In this
    case it simply means it can be found in the .ini file.

    param site: the user specified boxx-site
    """
    if site not in BOXX_SITES:
        # INVALID SITE. PRINT ERROR AND EXIT
        print(f"{site} is not a valid site.")
        print(f"  Valid sites:")
        for s in BOXX_SITES:
            print(f"    {s}")
        print()
        print()
        usage()


def read_command_line() -> (str, str):
    """
    Parse and verify the command line arguments looking for a
    site and item provided by the user.

    If the command line is invalid, print usage and quit program.

    return: A pair of the site and item provided on the command-line.
                None indicates the user did not provide a
                value and wants them all.
    """
    site = None
    item = None

    if len(sys.argv) > 3:
        print("Too many command line arguments.")
        print()
        usage()

    if len(sys.argv) >= 2:
        site = sys.argv[1]
        verify_boxx_site(site)

    if len(sys.argv) == 3:
        item = sys.argv[2]

    return (site, item)


def filter_items(all_item_pgs: [(str, str)], valid_items: [str]) -> [(str,str)]:
    """

    param all_item_pgs: the list of possible items for the user to
                download (read from the websites downloads page)
    param valid_items: list of items the user wants to download
    return:  A list with only items in both lists
    """
    if len(valid_items) == 0:
        return all_item_pgs

    filtered_list = []
    for url, item in all_item_pgs:
        if item in valid_items:
            filtered_list.append((url, item))

    return filtered_list


def main():
    """
    Main program starts here.
    """
    site, cmdln_item = read_command_line()

    # EMPTY THE DOWNLOAD DIR FOR A CLEAN START
    clean_download_dir()

    # START UP THE BROWSER
    browser = start_browser()

    # LOOP THROUGH EACH BUSY-BOXX SITE THAT IS CONFIGURED FOR PROCESSING
    if site is None:
        site_list = BOXX_SITES
    else:
        site_list = [site]

    for boxx_site in site_list:
        print()
        print(f"*** *** *** DOWNLOAD FROM {boxx_site.upper()} *** *** ***")
        print()
        # LOGIN TO THE SITE
        login(browser, boxx_site)

        # GET A LIST OF ALL PURCHASED ITEMS
        item_pgs = get_item_download_pages(browser)
        pgs = filter_items(item_pgs, [cmdln_item])

        # DOWNLOAD THE FILES FOR EACH ITEM
        for (url, item) in pgs:
            print(f"  Follow link to detail page for {item}")
            if cmdln_item is not None or not ensure_save_dir_exists(boxx_site, item):
                print(f"    *** Download url: {url} ***")
                print(f"    *** Save to: {get_save_dir(boxx_site, item)} ***")
                download_item_files(browser, url, boxx_site, item)

            else:
                print(f"    --- Skip {get_save_dir(boxx_site, item)} - previously downloaded.")

    browser.quit()

if "__main__" == __name__:
    main()
