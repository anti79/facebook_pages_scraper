# Installation
* Install dependencies: `pip install -r requirements.txt`
* Make sure you have Chrome version 106 installed. 
Alternatively, check your Chrome version and download a corresponding ChromeDriver executable from here:
 https://chromedriver.chromium.org/downloads
 Then, replace the file in the 'drivers' folder.
 * Before using the script to scrape data, run `python scraper.py --login` to log into your Facebook account, as Facebook requires you to be logged in in order to be able to search.
 
 # Running

```
usage: scraper.py
       [-h] [-l]
       [-s SCRAPE]
       [-loc LOCATIONS]
       [-c COUNTRY]

optional arguments:
  -h, --help
    show this
    help message
    and exit
  -l, --login
    log into a
    Facebook
    account
  -s SCRAPE, --scrape SCRAPE
    search for a
    given query
    in given
    locations
    and then
    scrape the
    found data
  -loc LOCATIONS, --locations LOCATIONS
    CSV or TXT
    file from
    where the
    list of
    locations
    will be
    loaded. 'loc
    ations.csv'
    is used by
    default.
  -c COUNTRY, --country COUNTRY
    Country that
    locations
    will be
    searched in.
    Use this in
    case there
    are multiple
    cities with
    the same
    name.
```

# Examples

* `python scraper.py --scrape "coffee" --country Israel` 

For all cities in `locations.csv`,
specify that they are in Israel, to avoid a problem when a city with the same name exists in multiple countries. Then search for *coffee* in each city. Save the result to `results/coffee` directory.

* `python scraper.py --scrape "car wash" --locations my-cities.txt` 

Import cities from `my-cities.txt` instead of default `locations.csv` (first line of the file is skipped).
Then search for *car wash* in each city. Country is not specified. Save the result to `results/carwash` directory.

