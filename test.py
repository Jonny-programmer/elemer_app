import json

import requests


def smth(**kwargs):
    res = requests.get(url="https://yandex.ru", params=params).text
    print(res)
    res = json.loads(res)
    return res


params = {"address": ["-4242413", "message", "Sorry, some mistake happened"]}
print(smth(**params))