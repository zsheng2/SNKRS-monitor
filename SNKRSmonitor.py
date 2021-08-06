from random_user_agent.params import SoftwareName
from random_user_agent.user_agent import UserAgent

from fp.fp import FreeProxy

import requests as req
import urllib3

from datetime import datetime
import time

import json
import logging
import dotenv
#configuring log and load to a file
logging.basicConfig(filename ="Monitorlog.log", filemode = "a", format = "%(asctime)s - %(name)s - %(message)s", level=logging.DEBUG)

#assigning random user agents
software_names = [SoftwareName.CHROME.value]
user_agent_rotator = UserAgent(software_nammes= software_names)
CONFIG  = dotenv.dotenv_values()

proxyObject = FreeProxy(country_id = [CONFIG["LOCATION"]], rand=True)

INSTOCK = []

def scrape_site(headers, proxy):
    #Scapes SNKRS site and adds items to an array
    items = []
    headers = {"user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36"}
    #makes request to the site
    url = f'https://api.nike.com/product_feed/threads/v2/?anchor=0&count=60&filter=marketplace%28{CONFIG["LOC"]}%29&filter=language%28{CONFIG["LAN"]}%29&filter=channelId%28010794e5-35fe-4e32-aaff-cd2c74f89d61%29&filter=exclusiveAccess%28true%2Cfalse%29&fields=active%2Cid%2ClastFetchTime%2CproductInfo%2CpublishedContent.nodes%2CpublishedContent.subType%2CpublishedContent.properties.coverCard%2CpublishedContent.properties.productCard%2CpublishedContent.properties.products%2CpublishedContent.properties.publish.collections%2CpublishedContent.properties.relatedThreads%2CpublishedContent.properties.seo%2CpublishedContent.properties.threadType%2CpublishedContent.properties.custom%2CpublishedContent.properties.title'
    html = req.get(url=url, timeout=20, verify=False, headers=headers, proxies=proxy)
    output = json.loads(html.text)
    count = 0
    max = int(CONFIG["FRAMES"]) + 1
    # Stores details in array
    for item in output["objects"]:
        count += 1
        if count != max:
            items.append(item)
        else:
            break
         
    logging.info(msg="Successfully scapred SNKRS site!")
    return items

def checker(item):
    # Determines whether the product status has changed
    return item in INSTOCK

def test_webhook():
    '''
    Sends a test Discord webhook notification
    '''
    data = {
        "username": CONFIG['USERNAME'],
        "avatar_url": CONFIG['AVATAR_URL'],
        "embeds": [{
            "title": "Starting Monitor",
            "description": "Successfully started monitor! Please wait for a while...",
            "color": int(CONFIG['COLOUR']),
            "footer": {'text': 'Presented by EZWFNF'},
            "timestamp": str(datetime.utcnow())
        }]
    }

    result = req.post(CONFIG['WEBHOOK'], data=json.dumps(data), headers={"Content-Type": "application/json"})

    try:
        result.raise_for_status()
    except req.exceptions.HTTPError as err:
        logging.error(msg=err)
    else:
        print("Payload delivered successfully, code {}.".format(result.status_code))
        logging.info(msg="Payload delivered successfully, code {}.".format(result.status_code))


def discord_webhook(title, description, url, thumbnail, price, style_code, sizes):

    # Push an ubpate notification to the specified webhook url

    data = {
        "username" : CONFIG["USERNAME"],
        "avatar_url" : CONFIG["AVATAR_URL"],
        "embeds": [{
            "title" : title,
            "description" : description,
            "url" : url,
            "thumbnail" : {"url":thumbnail},
            "color" : int (CONFIG["COLOUR"]),
            "footer" : {"text":"Presented by EZWFNF"},
            "timestamp" : str(datetime.utcnow()),
            "fields" : [
                {"name":"Price", "value":price},
                {"name":"Style Code", "value":style_code},
                {"name":"Sizes", "value":sizes}
            ]
        }]
    }
   
    result = req.post(CONFIG['WEBHOOK'], data=json.dumps(data), headers={"Content-Type": "application/json"})

    try:
        result.raise_for_status()
    except req.exceptions.HTTPError as err:
        logging.error(msg=err)
    else:
        print("Payload posted successfully. Status Code: {}".format(result.status_code))
        logging.info(msg="Payload posted successfully. Status Code: {}".format(result.status_code))

def comparitor(j, start):
    first = 0
    sizes = ''
    # for each product, scrape its "availableSkus" key
    for k in j['availableSkus']:
        item = [j['merchProduct']['labelName'], j['productContent']['colorDescription'], k['id']]
        if k['available'] == True:
            if checker(item):
                pass
            else:
                INSTOCK.append(item)
                # for each product scrape its "skus" key
                for s in j['skus']:
                    if first == 0:
                        if s["id"] == k["id"]:
                            sizes = str(s['nikeSize']) + ': ' + str(k['level'])
                            # concatenate size and stock level
                            first = 1
                        
                    else:
                        if s["id"] == k["id"]:
                            # if not the first size entered
                            sizes += '\n' + str(s['nikeSize']) + ': ' + str(k['level'])
                        
        else:
            if checker(item):
                INSTOCK.remove(item)

    if sizes != '' and start == 1:
        print('Sending notification to Discord...')
        discord_webhook(
            title=j['merchProduct']['labelName'],
            description=j['productContent']['colorDescription'],
            url='https://www.nike.com/' + CONFIG['LOC'] + '/launch/t/' + j['productContent']['slug'],
            thumbnail=j['imageUrls']['productImageUrl'],
            price=str(j['merchPrice']['currentPrice']),
            style_code=str(j['merchProduct']['styleColor']),
            sizes=sizes)

def avoid_duplicate(j):
    shoestyle = str(j["merchProduct"]["styleColor"])
    shoefile = "Shoes.txt"
    with open(shoefile, "r") as rf:
        with open(shoefile, "a") as af:
            read = rf.read()
            if shoestyle not in read:
                af.write("\n" + shoestyle)
                return True
            else:
                return False
    


def monitor():
    """
    Initiates the monitor
    """
    print('STARTING MONITOR')
    logging.info(msg='Successfully started monitor')

    # Ensures that first scrape does not notify all products
    start = 1

    test_webhook()

    # Initialising proxy and headers
    headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}
    proxy_no = 0
    proxy_list = CONFIG['PROXY'].split('%')
    proxy = {"http": proxyObject.get()} if proxy_list[0] == "" else {"http": f"http://{proxy_list[proxy_no]}"}

    # Collecting all keywords (if any)
    keywords = CONFIG['KEYWORDS'].split('%')
    while True:
        # Makes request to site and stores products 
        items = scrape_site(proxy, headers)
        # items: stores a list of values of output["objects"]
        # these values are products
        for item in items:
            try:
                # for each product scrapes its value of item["productInfo"]
                for j in item['productInfo']:
                    # item["productInfo"] contains details of the product
                    # j is detail of each product
                    if j['availability']['available'] == True and j['merchProduct']['status'] == 'ACTIVE':
                        if avoid_duplicate(j):
                            if keywords == "":
                                # If no keywords set, checks whether item status has changed
                                comparitor(j, start)

                            else:
                                # For each keyword, checks whether particular item status has changed
                                for key in keywords:
                                    if key.lower() in j['merchProduct']['labelName'].lower() or key.lower() in j['productContent']['colorDescription'].lower():
                                        comparitor(j, start)            
                        else:
                            pass

                    else:
                        # if item not available, remove it from INSTOCK list
                        for item in INSTOCK:
                            if item[0] == j['merchProduct']['labelName'] and item[1] == j['productContent']['colorDescription']:
                                INSTOCK.remove(item)

            except req.exceptions.HTTPError as e:
                print(f"Exception found '{e}' - Rotating proxy and user-agent")
                logging.error(e)

                # Rotates headers
                headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}

                if CONFIG['PROXY'] == "":
                    # If no optional proxy set, rotates free proxy
                    proxy = {"http": proxyObject.get()}
                
                else:
                    # If optional proxy set, rotates if there are multiple proxies
                    proxy_no = 0 if proxy_no == (len(proxy_list) - 1) else proxy_no + 1
                    proxy = {"http": f"http://{proxy_list[proxy_no]}"}
            
            except Exception as e:
                pass

        # Allows changes to be notified
        start = 0

        # User set delay
        time.sleep(float(CONFIG['DELAY']))


if __name__ == '__main__':
    urllib3.disable_warnings()
    monitor()