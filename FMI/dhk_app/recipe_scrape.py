import os
import time
from datetime import datetime
from dateutil.parser import parse
import io
import json
import hashlib
import requests
import urllib
import logging
from slugify import slugify
from selenium import webdriver
from PIL import Image
from django.http import HttpRequest
from django.http import HttpResponse, FileResponse
from django.http import HttpResponseRedirect
import app.aws as aws
import app.workbook as workbook
import app.wb_excel as wb_excel
import dhk_app.recipe as recipe
from FMI.settings import BASE_DIR

logger = logging.getLogger(__name__)

global wd
wd = None

#Selector	Example
#Type selector          h1 {  }
#Universal selector     * {  }
#Class selector         .box {  }
#id selector            #unique { }
#Attribute selector     a[title] {  }, a{href="abc"] { }
#Attribute selector     p[class~="special"] (contains value), div[lang|="zh"] (begins with)
#Pseudo-class selectors p:first-child { }
#Pseudo-element selectors   p::first-line { }
#Descendant combinator  article p
#Child combinator       article > p
#Adjacent sibling       combinator	h1 + p
#General sibling        combinator	h1 ~ p
#
# added evaluater, starts with =

parser_site_recipe = {
    "www.leukerecepten.nl" : {
    'id'            : {'type': str, 'selectors' : ""},
    'title'         : {'type': str, 'selectors' : [".page-content__title"]},
    'published_date': {'type': datetime, 'selectors' : ["meta[property='article:modified_time']", "=.get_attribute('content')"]},
    'author'        : {'type': str, 'selectors' : []},
    'excerpt'       : {'type': str, 'selectors' : ["meta[name='description']", "=.get_attribute('content')"]},
    'description'   : {'type': str, 'selectors' : []},
    'categories'    : {'type': list, 'selectors' : []},
    'cuisiness'     : {'type': list, 'selectors' : []},
    'tags'          : {'type': list, 'selectors' : []},
    'images'        : {
        'properties' : {
            'image'     : {'type': str, 'selectors' : "image"},
            'location'  : {'type': str, 'selectors' : ["meta[property='og:image']", "=.get_attribute('content')"]},
            },
        },
    'reviews'       : {
        'properties' : {
            'review'    : None,
            }
        },
    'nutrition'     : None,
    'cooking_times' : None,
    'courses'       : {
        'properties' : {
            'title'        : {'type': str, 'selectors' : [".page-content__title"]},
            'ingredients_parts'   : {
                'properties'    : {
                    'part'          : {'type': int, 'selectors' : ["=0"]},
                    'ingredients'   : {
                        'selectors' : ["ul.page-content__ingredients-list"],
                        'properties' : {
                            'ingredient' : {'type': dict, 'selectors' : ["label"]},
                            }
                        }
                    }
                },
            'instructions'  : {
                'selectors' : [".page-content__recipe"],
                'properties' : {
                    'instruction' : {'type': dict, 'selectors' : [".step"]}
                    }
                }
            }
        }
    }
}


def webdriver_start():
    global wd

    if wd is None:
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument("--headless")
        wd = webdriver.Chrome(options=options)
    return wd

def webdriver_get(page):
    global wd
    
    wd.get(page)
    # wait for the element to load
    try:
        webdriver.support.ui.WebDriverWait(wd, 5).until(lambda s: s.find_element_by_tag_name("body").is_displayed())
        return wd
    except TimeoutException:
        print("TimeoutException: Element not found")
        return None


def webdriver_stop():
    global wd

    wd.close()
    wd.quit()


def carousel_scrape(query: str, max_links_to_fetch: int, sleep_between_interactions: float = 0.1):
    global wd

    def scroll_to_end(wd):
        wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_between_interactions)

    wd = webdriver_start()
    search_url = "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img"
    wd.get(search_url.format(q=query))
    thumbnails = []
    image_count = 0
    results_start = 0
    while image_count < max_links_to_fetch:
        scroll_to_end(wd)
        thumbnail_results = wd.find_elements_by_css_selector("img.Q4LuWd")
        number_results = len(thumbnail_results)
        print(f"Found: {number_results} search results. Extracting links from {results_start}:{number_results}")

        for img in thumbnail_results[results_start:number_results]:
            ## try to click every thumbnail such that we can get the real image behind it
            #try:
            #    img.click()
            #    time.sleep(sleep_between_interactions)
            #except Exception:
            #    continue

            ## extract image urls
            #actual_images = wd.find_elements_by_css_selector('img.n3VNCb')
            #for actual_image in actual_images:
            #    if actual_image.get_attribute('src') and 'http' in actual_image.get_attribute('src'):
            #        thumbnails.append(actual_image.get_attribute('src'))
            if img.get_attribute('src'):
                thumbnail = {}
                thumbnail['src'] = img.get_attribute('src')
                thumbnail['alt'] = img.get_attribute('alt')
                thumbnail['width'] = img.get_attribute('width')
                thumbnail['height'] = img.get_attribute('height')
                thumbnails.append(thumbnail)
            image_count = len(thumbnails)
            if len(thumbnails) >= max_links_to_fetch:
                print(f"Found: {len(thumbnails)} image links, done!")
                break
        else:
            print("Found:", len(thumbnails),
                  "image links, looking for more ...")
            time.sleep(30)
            return
            load_more_button = wd.find_element_by_css_selector(".mye4qd")
            if load_more_button:
                wd.execute_script("document.querySelector('.mye4qd').click();")

        # move the result startpoint further down
        results_start = len(thumbnail_results)
    webdriver_stop()
    return thumbnails


def persist_image(folder_path: str, url: str):
    try:
        image_content = requests.get(url).content

    except Exception as e:
        print(f"ERROR - Could not download {url} - {e}")

    try:
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file).convert('RGB')
        file_path = os.path.join(folder_path, hashlib.sha1(
            image_content).hexdigest()[:10] + '.jpg')
        with open(file_path, 'wb') as f:
            image.save(f, "JPEG", quality=85)
        print(f"SUCCESS - saved {url} - as {file_path}")
    except Exception as e:
        print(f"ERROR - Could not save {url} - {e}")

def scrape_init_field(field_type):
    field_value = ""
    if field_type == 'nested':
        field_value = []
    elif field_type == list:
        field_value = []
    elif field_type == dict:
        field_value = []
    elif field_type == int:
        field_value = 0
    elif field_type == datetime:
        field_value = datetime.now().strftime('%Y-%m-%d')
    else:
        field_value = ""
    return field_value

def scrape_find_elms_values(root_elm, field_name, field_parser):
    field_type = field_parser.get('type', 'nested')
    selectors = field_parser.get('selectors', [])
    child_elms = []
    child_value = scrape_init_field(field_type)
    if type(selectors) == str:
        return [root_elm], selectors
    if len(selectors) == 0:
        return [root_elm], child_value
    stack = [(root_elm, 0)]
    while len(stack):
        node = stack.pop()
        root_elm = node[0]
        selector = selectors[node[1]]
        if selector[0] == '=':
            if selector[1] == '.':
                child_value = eval('root_elm' + selector[1:])
            else:
                child_value = eval(selector[1:])
        else:
            elms = root_elm.find_elements_by_css_selector(selector)
            for elm in elms:
                if node[1] == len(selectors) - 1:
                    child_elms.append(elm)
                    if field_type == str:
                        child_value = child_value + elm.text
                    elif field_type == dict:
                        child_value.append({field_name : elm.get_attribute('textContent')})
                    elif field_type == datetime:
                        child_value = datetime.parse(elm.text).strftime('%Y-%m-%d')
                    else:
                        child_value.append(elm.get_attribute('textContent'))
                else:
                    stack.append((elm, node[1] + 1))
    return child_elms, child_value

def recipe_parse(root_elm, parser_recipe, path = ""):
    global wd

    dhk_wb = workbook.Workbook('dhk')
    recipe = {}
    for field_name, field_parser in parser_recipe.items():
        if field_parser is None:
            continue
        field_name_full = field_name if not path else path + '.' + field_name
        field_type_es = dhk_wb.get_field_type(field_name_full)
        field_type = field_parser.get('type', 'nested')
        field_value = scrape_init_field(field_type)
        if field_type_es == 'nested':
            elms, _ = scrape_find_elms_values(root_elm, field_name, field_parser)
            for elm in elms:
                elm_value = recipe_parse(elm, field_parser['properties'], field_name_full)
                if len(elm_value) > 0:
                    field_value.append(elm_value)
        else:
            elms, field_value = scrape_find_elms_values(root_elm, field_name, field_parser)
        if field_type == dict:
            recipe = field_value
        else:
            recipe[field_name] = field_value
    return recipe


def recipe_scrape(request):
    global wd

    id = request.GET['id']
    page = request.GET['page']
    logger.info(f"Scrape recipe for id '{id}' with page '{page}'")

    site = urllib.parse.urlparse(page).netloc.split(':')[0]
    if site not in parser_site_recipe:
        return None
    webdriver_start()
    dirname = os.path.join(BASE_DIR, 'data', 'dhk', 'scrape')
    filename = slugify(page) + '.html'
    filename_full = os.path.join(dirname, filename)
    if os.path.isfile(filename_full):
        #with open(filename_full, 'r', encoding='utf-8') as f:
        #    page_source = f.read()
        #    f.close()
        wd.get(filename_full)
        time.sleep(3)
        page_source = wd.page_source
    else:
        webdriver_get(page)
        page_source = wd.page_source
        with open(filename_full, 'w', encoding='utf-8') as f:
            f.write(page_source)
            f.close()
    root_elm = wd.find_element_by_tag_name('html')
    recipe_new = recipe_parse(root_elm, parser_site_recipe[site])
    recipe_new['id'] = page
    # leave the driver running
    # webdriver_stop()

    if id == '':
        id = slugify(page)
        recipe_obj = recipe.Recipe(id, recipe=recipe_new)
        recipe_obj.put()
    else:
        recipe_obj = recipe.Recipe(id)

    context = {
        'recipe'  : recipe_obj.recipe,
        }
    return HttpResponse(json.dumps(context), content_type='application/json')
