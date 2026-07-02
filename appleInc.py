import httpx
from bs4 import BeautifulSoup
import re
from pydantic import BaseModel, TypeAdapter, ValidationError
from typing import Literal
class AppStore(BaseModel):
    name: str
    description: str
    star: str
    view: str
    
class Input(BaseModel):
    keyword:str
    region: str
    platform: Literal['watch','tv','vision','mac','ipad','iphone']
    
def app_store(keyword:str, region:str, platform: str):
    try:
        Input(keyword=keyword,region=region,platform=platform)
    except ValidationError as e:
        print(f"error:{e}")
        return None
    raw = httpx.get(f"https://apps.apple.com/{region}/{platform}/search?term={keyword}")
    raw.encoding = 'utf-8'
    soup = BeautifulSoup(raw.text,"lxml")
        
    container = soup.find('ul',class_ = "grid")
    app = []
    li = container.find_all(name="h3",class_="svelte-ppcjjt")
    for i in li:
        print(i.string)
        app.append(i.string)

    description = []
    d = container.find_all(name='p',class_="svelte-ppcjjt")
    for i in d:
        print(i.string)
        description.append(i.string)

    views = []
    view = container.find_all(name="span",class_=re.compile(r"^rating-container"))
    for i in view:
        print(i.get_text())
        views.append(i.get_text(strip=True))

    ratings = []
    rate = container.find_all(name = 'ol', attrs={'aria-label':True})
    for i in rate:
        print(i.attrs['aria-label'])
        ratings.append(i.attrs['aria-label'])

    links = container.find_all('a',attrs={"href":True})
    for i in links:
        print(i.attrs['href'])

    search_results = [AppStore(name=a,description=b,star=c,view=d) for a,b,c,d in zip(app, description, ratings, views)]

    results_model = TypeAdapter(list[AppStore])

    result = results_model.dump_json(search_results)
    print(result.decode('utf-8'))
    print(repr(result.decode('utf-8')))
    print(type(result.decode('utf-8')))
    return result.decode('utf-8')

if __name__ == "__main__":
    app_store('apple', 'us', 'iphone')
