import json
import logging
import requests

import pathlib


def _load_ogc_apis():
    file_path = pathlib.Path(__file__).parent / 'ogc_apis.json'
    with open(file_path, 'r') as f:
        return json.load(f)


ogc_apis = _load_ogc_apis()


def fetch_ogc_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_ogc_collections(apiurl, itemType="feature"):
    try:
        url = apiurl.rstrip('/') + "/collections?f=json"
        print(url)
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(e)
        return None
    return response.json()


def process_ogc(url):
    try:
        ogc_data = fetch_ogc_data(url)

        selected_apis = []
        for api in ogc_data['apis']:
            root_link = next(
                (link['href'] for link in api['links']
                 if link and link['rel'] == 'root'),
                None)

            if root_link:
                collection_data = fetch_ogc_collections(root_link)
                if collection_data:
                    for collection in collection_data['collections']:
                        if ('itemType' in collection and
                                collection['itemType'] == 'feature'):
                            collection_link = next(
                                (link['href'] for link in collection['links']
                                 if link['rel'] == 'items'), None)
                            if collection_link:
                                collection_url = (root_link.rstrip('/') +
                                                  '/collections/' +
                                                  collection['id'] + '/items')
                                selected_apis.append({
                                    "displaytitle": api['title'] +
                                    ' - ' + collection['title'],
                                    "title": collection['title'],
                                    "url": collection_url,
                                    "description": collection.get(
                                        'description',
                                        'No description available')
                                })
    except Exception as e:
        logging.exception(e)

        return None

    return selected_apis
