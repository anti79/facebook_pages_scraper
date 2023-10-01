import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from colorama import Fore, Back, Style
import pandas as pd
import numpy as np
import warnings
from bs4 import BeautifulSoup as bs
from bs4 import Tag
import argparse
from dataclasses import dataclass
from typing import List
from selenium.webdriver.remote.webelement import WebElement
from collections import namedtuple
import os
import traceback
import platform
from colorama import init
from urllib3 import Timeout
init()
warnings.filterwarnings('ignore')
argparser = argparse.ArgumentParser()
argparser.add_argument("-l","--login", help="log into a Facebook account", action="store_true")
argparser.add_argument("-s","--scrape", help="search for a given query in given locations and then scrape the found data", type=str)
argparser.add_argument("-loc","--locations", help="TXT or CSV file from where the list of locations will be loaded. 'locations.txt' is used by default. If using CSV, make sure the city name is the first value in each line.", type=str)
argparser.add_argument("-c","--country", help="Country that locations will be searched in. Use this in case there are multiple cities with the same name. ", type=str)
args = argparser.parse_args()

SEARCH_URL = "https://www.facebook.com/search/pages?q="
LOGIN_URL = "https://facebook.com/login.php"
LOCATIONS_FILE="locations.txt"
MAX_TIMEOUT = 9223372036854775808

class Logger:
	def info(text):
		print(Fore.CYAN + "[*] " + text + Fore.RESET)
	def success(text):
		print(Fore.GREEN + "[+] " + text + Fore.RESET)
	def error(text):
		print(Fore.RED + "[X] " + text + Fore.RESET)
	def warning(text):
		print(Fore.YELLOW + "[!] " + text + Fore.RESET)

	
def load_locations(filename):
	Logger.info("Loading locations..")
	locations = []
	try:
		with open(filename, 'r') as file:
			for i,line in enumerate(file):
			#assuming city name is the first value
				city = line.split(',')[0]
				city = city.replace('"', '')
				city = city.replace('\n', '').replace('\r', '')
				if(city==''):
					continue
				locations.append(city)
		Logger.success(f"Location list loaded: {str(len(locations))} locations found.\n")
		return locations
	except Exception as e:
		Logger.error("Error while loading locations from file: " + str(e))
		exit()

class SheetWriter:
	def write(queryname, results, location):
		illegal_symbols = "$&@\{\}/\\*?|`+=!'\": <>"
		for s in illegal_symbols:
			if(s in queryname):
				queryname = queryname.replace(s, '')
		for s in illegal_symbols:
			if(s in location):
				location = location.replace(s, '')
		dir = f"results/{queryname}"
		try:
			if not os.path.isdir(dir):
				os.makedirs(dir)
			results = pd.DataFrame(results)
			filepath = os.path.join(dir, location+".xlsx")
			#with open(filepath, 'w', encoding='utf-8') as f:
			#	f.write("sep=,\n")
			#results.to_csv(filepath, sep=',', mode='a', encoding = 'utf-8')	
			results.to_excel(filepath, encoding = 'utf-8')
			#np.savetxt(filepath, results, delimiter=',',)
	
		except Exception as e:
			Logger.error("Error while writing files: " + str(e))
			

		


class FBPageParser:

	def __init__(self, driver):
		self.driver = driver

	def identify_page_type(self):
		
		#TYPE1_IDENTIFIER = """.x193iq5w.xeuugli.x13faqbe.x1vvkbs.x10flsy6.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x1tu3fi.x3x7a5m.x1lkfr7t.x1lbecb7.x1s688f.xi81zsa"""
		TYPE2_IDENTIFIER = """.x1i10hfl.xjbqb8w.x6umtig.x1b1mbwd.xaqea5y.xav7gou.x9f619.x1ypdohk.xt0psk2.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16tdsg8.x1hl2dhg.xggy1nq.x1a2a7pz.xt0b8zv.xi81zsa.x1s688f"""


		#if(len(self.driver.find_elements(By.CSS_SELECTOR , TYPE1_IDENTIFIER))>0):
		#	return 1
		if(len(self.driver.find_elements(By.CSS_SELECTOR , TYPE2_IDENTIFIER))>0):
			return 2
		else:
			return 1
			#raise Exception("Unknown page type")

	def get_about_link(self, link:str):
		about_link = link
		if("profile.php" in link):
			about_link+="&sk=about"
		else:
			if(about_link[-1]!='/'):
				about_link+='/'
			about_link += "about"
		return about_link

	def identify_entry_type(self, entry:WebElement):
		IconIdentifier = namedtuple("IconIdentifier", ['name','type1', 'type2'])
		identifiers = [
			IconIdentifier("phone", 
			'background-image: url("https://static.xx.fbcdn.net/rsrc.php/v3/y8/r/IGUsNLvGQao.png"); background-position: 0px -402px;',
			"https://static.xx.fbcdn.net/rsrc.php/v3/yl/r/mxbGn5aKz1f.png"),
			IconIdentifier("phone", 
			'background-position: 0px -1076px; ',
			"???????????"),
			IconIdentifier("likes",
			'background-image: url("https://static.xx.fbcdn.net/rsrc.php/v3/yH/r/D7dpTwWRm74.png"); background-position: -84px -166px;',
			"???????"
			),
			IconIdentifier("likes",
			'background-image: url("https://static.xx.fbcdn.net/rsrc.php/v3/yY/r/2HomLwJCr3u.png"); background-position: 0px -866px;',
			"???????"),
			IconIdentifier("follows",
			'background-image: url("https://static.xx.fbcdn.net/rsrc.php/v3/yM/r/qP7YdshNOfA.png"); background-position: 0px -117px;',
			"???????"),
			IconIdentifier("follows",
			'background-image: url("https://static.xx.fbcdn.net/rsrc.php/v3/yz/r/iSEpr556uug.png"); background-position: 0px -440px;',
			"???????"),
			IconIdentifier("category",
			'background-image: url("https://static.xx.fbcdn.net/rsrc.php/v3/y8/r/IGUsNLvGQao.png"); background-position: 0px -171px;',
			"https://static.xx.fbcdn.net/rsrc.php/v3/yr/r/lhdCVH10kLz.png"),
			IconIdentifier("website",
			'background-image: url("https://static.xx.fbcdn.net/rsrc.php/v3/ym/r/9l88KfQQZWY.png"); background-position: 0px -733px;',
			"https://static.xx.fbcdn.net/rsrc.php/v3/yf/r/R8NeZY3_bOP.png"),
			IconIdentifier("website",
			'background-position: 0px -845px;',
			"????????"),
			IconIdentifier("address",
			'background-image: url("https://static.xx.fbcdn.net/rsrc.php/v3/ym/r/9l88KfQQZWY.png"); background-position: 0px -985px;',
			"https://static.xx.fbcdn.net/rsrc.php/v3/yS/r/poZ_P5BwYaV.png"),
			IconIdentifier("address",
			'background-image: url("https://static.xx.fbcdn.net/rsrc.php/v3/yY/r/2HomLwJCr3u.png"); background-position: 0px -1097px;',
			"???????"),
			IconIdentifier("email",
			'background-position: 0px -607px;',
			"https://static.xx.fbcdn.net/rsrc.php/v3/yi/r/VtfpQ9pmUXR.png"),
			IconIdentifier("email",
			'background-position: 0px -761px;',
			"????????????"),
			
			]

		tag = None
		imgs = entry.find_elements(By.TAG_NAME, 'img')
		if(len(imgs)>0):
			tag = imgs[0]
		else:
			tag = entry.find_element(By.TAG_NAME, 'i')
			pass
		
		img = ""
		if(tag.tag_name=='i'):
			img = tag.get_attribute("style")
			
			
		elif(tag.tag_name=="img"):
			img = tag.get_attribute("src")

		for id in identifiers:
			if(((id[1] in img) or (id[2] in img))):
				return id[0]
		return "unknown"
	
	def parse(self, link: str):
		
		UNKNOWN_VAL = "unknown"
		about = {
			"category": UNKNOWN_VAL,
			"address": UNKNOWN_VAL,
			"phone": UNKNOWN_VAL,
			"name": UNKNOWN_VAL,
			"link": UNKNOWN_VAL,
			"email": UNKNOWN_VAL,
			"website": UNKNOWN_VAL

		}

		about_link = self.get_about_link(link)
		about_page = self.driver.get(about_link)
		
		#Wait(driver, timeout=10).until(do)
		Wait(self.driver, timeout=5).until(lambda d: d.execute_script("return document.readyState") == "complete")
		Wait(self.driver, timeout=5).until(lambda d: len(d.find_elements(By.TAG_NAME, 'g'))>1)
		#there are two types of facebook pages for some stupid reason. they have different layouts
		
		page_type = self.identify_page_type()

		TYPE1_INFO_ENTRY = ".x9f619.x1n2onr6.x1ja2u2z.x78zum5.x2lah0s.x1nhvcw1.x1cy8zhl.xozqiw3.x1q0g3np.x1pi30zi.x1swvt13.xexx8yu.xykv574.xbmpl8g.x4cne27.xifccgj"
		TYPE2_INFO_ENTRY = ".x9f619.x1n2onr6.x1ja2u2z.x78zum5.x2lah0s.x1nhvcw1.x1qjc9v5.xozqiw3.x1q0g3np.xexx8yu.xykv574.xbmpl8g.x4cne27.xifccgj"
		#TODO: waits
		value_span = ' span[dir="auto"]'
		if(page_type==1):
			entry_elements = self.driver.find_elements(By.CSS_SELECTOR, TYPE1_INFO_ENTRY)
		elif(page_type==2):
			entry_elements = self.driver.find_elements(By.CSS_SELECTOR, TYPE2_INFO_ENTRY)


		for entry in entry_elements:
			entry_type = self.identify_entry_type(entry)
			links = entry.find_elements(By.TAG_NAME, value='a')
			if(len(links)>0):
				value = links[0].text #for website link parsing
			else:
				value = entry.get_attribute('innerText')
			if(entry_type!="unknown"):
				value = value.split('\n')[0]
				value = value.replace("\nEmail", '')
				value = value.replace("\nAddress", '')
				about[entry_type] = value
		try:
			if(page_type==1):
				about["name"] = Wait(self.driver, timeout=5).until(lambda d: d.find_element(By.CSS_SELECTOR, "span.x193iq5w.xeuugli.x13faqbe.x1vvkbs.x1xmvt09.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x1ill7wo.x41vudc.x1q74xe4.xyesn5m.x1xlr1w8.xzsf02u.x1yc453h span")).text
			elif(page_type==2):
				about["name"] = Wait(self.driver, timeout=5).until(lambda d: self.driver.find_element(By.TAG_NAME, "h1")).text
			about["link"] = link
		except TimeoutException as e:
			Logger.error(e.msg)
			Logger.error("This is really not supposed to happen.")
		return about
			


		
		
	def parse_all(self, search_results, query):
		parsed = 0
		Logger.info("Parsing pages..")
		
		for location, links in search_results.items():
			loc_results = []
			for link in links:
				try:
					about = self.parse(link)
					parsed+=1
					print(about)
					print("--------------")
					loc_results.append(about)
				except Exception as e:
					Logger.error(f"Couldn't parse page {link} due to error: ")
					Logger.error(str(e))
					Logger.error("Trying to continue..")
					continue
				
			SheetWriter.write(queryname=query,
					results=loc_results, 
					location=location)
				
		Logger.success(f"{parsed} pages parsed.")
		return results

class FBSearchDriver:

	def __init__(self, driver):
		self.driver = driver

	def login(self):
			try:
				self.driver.get(LOGIN_URL)
				HOME_BTN = ".x1i10hfl.xjbqb8w.xjqpnuy.xa49m3k.xqeqjp1.x2hbi6w.x13fuv20.xu3j5b3.x1q0q8m5.x26u7qi.x972fbf.xcfux6l.x1qhh985.xm0m39n.x9f619.x1ypdohk.xdl72j9.x2lah0s.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.x2lwn1j.xeuugli.x1n2onr6.x16tdsg8.x1hl2dhg.xggy1nq.x1ja2u2z.x1t137rt.x1o1ewxj.x3x9cwd.x1e5q0jg.x13rtm0m.x1q0g3np.x87ps6o.x1lku1pv.x1a2a7pz.x6s0dn4.x78zum5.xc73u3c.x5ib6vp.x1y1aw1k.xwib8y2"
				wait = Wait(self.driver, MAX_TIMEOUT)
				wait.until(EC.title_is("Facebook"))
				Wait(self.driver, timeout=5).until(lambda d: d.find_element(By.CSS_SELECTOR, HOME_BTN)) 
				Logger.success("Logged in.")
				self.driver.quit()
				exit(0)
			except Exception as e:
				Logger.error("Error while logging in: " + str(e))
				exit(1)

	def search(self, query, locations, country):
		Logger.info(f"Starting search for '{query}' in each location.")
		if(country!=None and country!=''):
			Logger.info(f'Country: {country}')
			country = ", " + country
		else:
			country = ''
		self.driver.get(SEARCH_URL + query)
		results = {}
		total = 0
		for location in locations:
			results[location] = []
			try:
				raw_location = location
				location = location + country
				#location = location.replace('\n', '')
				Logger.info(f"Searching in {location}..")
				LOC_BUTTON = 'div[aria-label="Location"]'
				#loc_button = Wait(self.driver, timeout=3).until(lambda d: d.find_element(By.CSS_SELECTOR, LOC_BUTTON)) 
				Wait(self.driver, timeout=5).until(EC.visibility_of_element_located(((By.CSS_SELECTOR, LOC_BUTTON))))
				loc_button = Wait(self.driver, timeout=5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, LOC_BUTTON)))
				#facebook has to be in english
				loc_button.click()
				LOC_SEARCH_INPUT = 'input[aria-label="Location"]'
				loc_input = self.driver.find_element(By.CSS_SELECTOR, LOC_SEARCH_INPUT)
				loc_input.send_keys(location)
				FIRST_LOC_SEARCH_RESULT = 'ul > li[role="option"]'
				loc_result = Wait(self.driver, timeout=3).until(lambda d: d.find_element(By.CSS_SELECTOR, FIRST_LOC_SEARCH_RESULT))
				loc_result.click()
			
				Wait(self.driver, timeout=5).until(lambda d: d.execute_script("return document.readyState") == "complete")
				

				RESET_LOC_BUTTON = f'div > div[aria-label~="Clear"]'
				#loc_reset = Wait(self.driver, timeout=3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, RESET_LOC_BUTTON)))
				#loc_reset.click()
				RESET_JS = f"document.querySelector('{RESET_LOC_BUTTON}').click()"
				END_OF_RESULTS = "//span[text()='End of results']"

				while True: #scroll down till end
					self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
					if(len(self.driver.find_elements(By.XPATH, END_OF_RESULTS)) != 0):
						break
				
				page_links = Wait(self.driver, timeout=3).until(lambda d: d.find_elements(By.CSS_SELECTOR, 'a[role="presentation"]'))
				
				urls = [] #scrape links
				for el in page_links:
					url = el.get_attribute("href")
					urls.append(url)
				results[raw_location] = urls
				Logger.info(f"Found {len(urls)} pages.")
				total+=len(urls)

				#reset location filter
				Wait(self.driver, timeout=5).until(lambda d: d.execute_script("return document.readyState") == "complete")
				Wait(self.driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'a')))
				self.driver.execute_script(RESET_JS)
				
			except WebDriverException as e:
				
				Logger.error("Error while searching. ")
				traceback.print_exc()
				Logger.warning("Make sure your Facebook language is set to English and you are logged in.")
				self.driver.quit()
				exit(1)
				
		Logger.success("Search finished.")
		Logger.success(f"Total pages found: {total}")
		
		return results
		

def start_driver():
	options = Options()
	options.add_argument("--disable-notifications")
	options.add_argument("--log-level=3")
	dir_path = os.getcwd()
	options.add_argument(f'user-data-dir={dir_path}/selenium')
	try:
		system = platform.system()
		if(system=="Windows"):
			exec = "drivers/chromedriver.exe"
		elif(system=="Linux"):
			exec="drivers/chromedriver"
		elif(system=="Darwin"):
			Logger.error("")
		fb = FBSearchDriver(driver=webdriver.Chrome(executable_path=exec, options=options))
		return fb
	except WebDriverException as ex:
		Logger.error("Error while starting Chrome: " + ex.msg)
		Logger.warning("Try closing all browser windows before starting the script.")
		exit(1)
	


#cmd args
if (args.login):
	fb = start_driver()
	fb.login()
elif (args.scrape):
	fb = start_driver()
	locations = None

	if(args.locations!=None):
		locations=load_locations(args.locations)	
	else:
		locations=load_locations(LOCATIONS_FILE)

	
	results = fb.search(args.scrape, locations=locations, country=args.country)
	parser = FBPageParser(fb.driver)
	parser.parse_all(results, args.scrape)
	#print(results)
	
else:
	argparser.print_help()
