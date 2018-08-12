#!/usr/bin/python3

import requests, re, pickle
from bs4 import BeautifulSoup, SoupStrainer
from datetime import datetime, timedelta

# https://www.gumtree.com.au/s-[<category>/][<location>/][<search-term>/][page-<page-number>/][<keyword-code "k0">][<category-code "c20045">][<location-code "l3003795">]

# destination pickle file to store posts
dest_file = 'master_post_list.pak'
# expected format of Gumtree search results
# important - {0} is expected to be the keyword to search, and {1} the page number
URL_FORMAT = "https://www.gumtree.com.au/s-{0}/page-{1}/k0" # {0} = keyword, {1} = page-number
# keywords to search
search_terms = ["keyboard", "gateron", "ibm+keyboard", "mechanical+keyboard", "cherry+mx", "topre", "novatouch"]

master_post_list = {}
export_list = []

# Regex for scraping data from listings
re_price = re.compile('Price: (?:\$([0-9,]+\.[0-9]+|)|not listed)')
re_location = re.compile('Location: ([^.]+)')
re_date = re.compile('Ad listed ([^.]+)')

re_dt = re.compile('([0-9]+) ([a-z]+) ago')

# SoupStrainer expressions for scraping listings and their data
str_post = SoupStrainer('a', { 'class': 'user-ad-row' })
str_img = SoupStrainer('img')
str_desc_title = SoupStrainer('p')

# Pase date strings scraped from Gumtree listings
def parse_date(date_str):
	match = re_dt.search(date_str)
	parsed = None
	print(date_str)
	if match:
		dtnow = datetime.now()
		value = match.group(1)
		unit = match.group(2)
		
		if unit == "hours" or unit == "hour":
			delta = timedelta(hours=int(value))
			parsed = dtnow - delta
		elif unit == "minutes" or unit == "minute":
			delta = timedelta(minutes=int(value))
			parsed = dtnow - delta
	elif date_str == "Yesterday":
		parsed = datetime.now() - timedelta(days=1)
	else:
		parsed = datetime.strptime(date_str, "%d/%m/%Y")
	
	return parsed

# Scrape data from given html source
def gumtree_parse(html):
	gtsoup = BeautifulSoup(html, "lxml")
	post_list = []
	gt_listings = gtsoup.find_all(str_post)
	for node in gt_listings:
		post_dict = {}
		post_data = node.get('aria-label')
		
		post_dict["link"] = "https://www.gumtree.com.au" + node.get("href")
		post_img = node.find_all(str_img)
		if post_img != None and len(post_img) > 0:
			post_dict["img"] = post_img[0].get('src')
		else:
			post_dict["img"] = ""
			
		p_search = node.find_all(str_desc_title)
		
		post_dict["description"] = ""
		if p_search[1].string: post_dict["description"] = str(p_search[1].string.encode("ascii","ignore"), "ascii").replace('\n', '<div></div>')
		post_dict["title"] = str(p_search[0].string.encode("ascii","ignore"), "ascii")
		post_dict["price"] = re_price.search(post_data).group(1)
		post_dict["location"] = re_location.search(post_data).group(1)
		post_dict["date"] = re_date.search(post_data).group(1)
		post_dict["dt"] = parse_date(post_dict["date"])
		
		post_list.append(post_dict)
	
	return post_list

# Iterate through every list search term
for term in search_terms:
    # Iterate through pages until a page has less then 30 items or we've hit 50 pages
	i = 1
	while True:
        # Retrieve, then parse html data for search pages
		request_data = requests.get(URL_FORMAT.format(term, i))
		page_list = gumtree_parse(request_data.text)
		
		for post in page_list:
			if post['link'] not in master_post_list:
				master_post_list[post['link']] = post
		
		print(page_list)
		print("Page:", i)
		print("Items:", len(page_list))
		
		if len(page_list) != 30 or i > 50: break
		i = i + 1
		
# Sort the final list to prepare for export
export_list = sorted(list(master_post_list.values()), key=lambda r: r["dt"], reverse=True)

# Export list as a pickle
if len(export_list) > 0:
	print('Saving master_post_list')
	with open(dest_file, 'wb') as f:
		pickle.dump(export_list, f, -1)