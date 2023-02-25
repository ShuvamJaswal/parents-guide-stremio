
from flask import Flask, jsonify, abort
from re import sub
import requests
from bs4 import BeautifulSoup
def getEpId(seriesID):
    season=seriesID.split('_')[-2]
    episode=seriesID.split('_')[-1]
    series=seriesID.split('_')[0]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'sec-uh-a':'"Not A;Brand";v="99", "Chromium";v="109", "Google Chrome";v="109"',
        'accept-encoding':'gzip, deflate, br',
        'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'scheme':'https',
        'authority':'www.imdb.com'}
    req=requests.get(f"https://m.imdb.com/title/{series}/episodes/?season={season}",headers=headers)
    soup = BeautifulSoup(req.content, 'html5lib')
    lis=[element['href'] for element in soup.find('div',{'id':'eplist'}).find_all('a')]
    return lis[int(episode)-1].split('/')[2].split('?')[0]
def display_section(title, category):
    temp=""
    if category:
        temp+=f'\n[{title.upper()}]'
        temp+=f'\n{category}\n'
    return temp
def cleanup_comments(comments):
    clean_comments = []
    if comments:
        for comment in comments:
            cleaned_up = sub(r'\n\n {8}\n {8}\n {12}\n {16}\n {16}\n {12}\nEdit', '', comment)
            clean_comments.append('* '+cleaned_up)
    return "\n".join(clean_comments)
def parse_section(soup):
    if not soup:
        return ""
    section_comment_tags = soup.find_all('li', {'class': 'ipl-zebra-list__item'})
    section_comment_list = [comment.text.strip() for comment in section_comment_tags]
    comments = cleanup_comments(section_comment_list)
    return comments

app = Flask(__name__)
def scrape_movie(id):
    try:
        soup = get_soup(id)
        if soup:
            soup_sections = soup.find('section', {'class': 'article listo content-advisories-index'})
            soup_nudity = soup_sections.find('section', {'id': 'advisory-nudity'})
            soup_profanity = soup_sections.find('section', {'id': 'advisory-profanity'})
            soup_violence=soup_sections.find('section', {'id': 'advisory-violence'})
            soup_spoilers = soup_sections.find('section', {'id': 'advisory-spoilers'})
            soup_frightening = soup_sections.find('section', {'id': 'advisory-frightening'})
            soup_alcohol = soup_sections.find('section', {'id': 'advisory-alcohol'})
            
            nudity = parse_section(soup_nudity)
            profanity = parse_section(soup_profanity)
            violence= parse_section(soup_violence)
            spoilers=parse_section(soup_spoilers)
            frightening=parse_section(soup_frightening)
            alcohol=parse_section(soup_alcohol)
            
            temp=""
            temp+=display_section('nudity', nudity)
            temp+=display_section('profanity', profanity)
            temp+=display_section('violence', violence)
            temp+=display_section('frightening', frightening)
            temp+=display_section('alcohol', alcohol)
            temp+=display_section('spoilers', spoilers)
            title=soup.find('meta', {'property': 'og:title'})['content'][:-7]
            return [str(temp),title]
    except Exception as e:
            return [str(e),""]

def get_soup(id):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'sec-uh-a':'"Not A;Brand";v="99", "Chromium";v="109", "Google Chrome";v="109"',
        'accept-encoding':'gzip, deflate, br',
        'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'scheme':'https',
        'authority':'www.imdb.com'
        }
        page = requests.get(f'https://www.imdb.com/title/{id}/parentalguide',headers=headers)
        soup = BeautifulSoup(page.content, 'html5lib')
        return soup
    except :
        return None


@app.route('/')
def root():
	return respond_with('working')
MANIFEST = {
    'id': 'com.beast.getparentsguide',
    'version': '1.0.0',
    'name': 'Get parents Guide',
    'description': 'Fetch parents guide',
    'catalogs':[],
    'types': ['movie', 'series'],
    'resources': [
        {'name': "meta", 'types': ["series","movie"], 'idPrefixes': ["gpg"]},
        {'name': 'stream', 'types': ['movie', 'series'],
        "idPrefixes": ["tt","gpg"]}
        ]
}


def respond_with(data):
    resp = jsonify(data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    resp.headers['Cache-Control']='public, max-age=40000'
    return resp

@app.route('/manifest.json')
def addon_manifest():
    return respond_with(MANIFEST)

@app.route('/meta/<type>/<id>.json')
def addon_meta(type, id):
    try:
        data=scrape_movie(f"{id.split('-')[-1]}")
        meta=dict()
        ref= len(data[0])<5
        meta['id']=id
        meta['type']=type
        meta['name']=(f"""{data[1].split('"')[1]} S0{id.split('_')[-2]}E0{id.split('_')[-1].split('-')[0]}""" or "test") if type=='series' else (data[1] or "test")
        data[0]=f"Name: {data[1]}\n{data[0]}"
        meta['description']=f"""{data[0] or "test"}"""
        if type=='series' and ref:
            print('try 2')
            data=scrape_movie(f"{id.split('-')[-2].split('_')[0]}")
            data[0]=f"Name: {data[1]}\n{data[0]}"
            meta['description']=f"""Parent's Guide for series:- \n{data[0] or "test"}"""
        mmmm={'meta':meta}
        print(mmmm)
    except Exception as e:
        mmmm={}
        print(e)
    return respond_with(mmmm)

@app.route('/stream/<type>/<id>.json')
def addon_stream(type, id):
    id=id.replace('%3A','_')
    if 'gpg' in id:abort(404)
    try:
        if type=='series':id=f"{id}-{getEpId(id)}"
        strm={
    "streams": [
        {
            "name": "Parents Guide",
            "externalUrl": f"stremio:///detail/{type}/gpg-{id}"
        },
                ]
                }
        return respond_with(strm)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    app.run()
