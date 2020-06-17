# -*- coding: utf-8 -*-
import copy
import csv
import json
import random
import re

from requests import get

from data import *


def get_product_id(data):
    rs = re.findall('Mã sản phẩm: (\d+)', data.get('description', ''))
    if len(rs) > 0:
        return rs[0]
    return data.get('itemid', 0)


def get_category(data):
    for category in data.get('categories', []):
        if category['no_sub']:
            return category['catid']
    return 'ERROR'


def get_price(data):
    if PRICE_BEFORE_DISCOUNT:
        return data['price_before_discount']
    return data['price']


# Xử lý các hình ảnh phụ
def append_images(data_formated, raw_data):
    temp = 1
    mix_array = raw_data['images']
    random.shuffle(mix_array)

    for index in range(len(mix_array)):

        if mix_array[index] == raw_data['image']:
            continue

        data_formated[getattr(COLUMN_DEFAULT, f'hinh{temp}')] = link_shopee(mix_array[index])
        temp = temp + 1


def print_json(data):
    print(json.dumps(data, indent=4))


# Request into shopee get json data
def get_detail_from_shopee(item_id):
    url = f'https://shopee.vn/api/v2/item/get?itemid={item_id}&shopid={SHOP_ID}'
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
        'Accept': '*/*',
        'Accept-Language': 'vi-VN,vi;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': 'https://shopee.vn/product/12874043/1540002479',
        'X-Shopee-Language': 'vi',
        'X-Requested-With': 'XMLHttpRequest',
        'X-API-SOURCE': 'pc'
    }
    return get(url, headers=custom_headers).json()['item']


def random_item_id():
    n = ''.join([str(random.randrange(0, 9)) for i in range(10)])
    while n in UNIQUE_LIST:
        n = ''.join([str(random.randrange(0, 9)) for i in range(10)])

    UNIQUE_LIST.append(n)
    return n


# tach cac PHAN LOAI thanh nhieu documents
def split_by_variation(raw_data):
    variations = []
    for tier_variations in raw_data['tier_variations']:
        for option_name in tier_variations['options']:
            variation = {
                COLUMN_DEFAULT.ten_nhom_phan_loai_1: tier_variations['name'],
                COLUMN_DEFAULT.hinh_anh_phan_loai: tier_variations['images'],
                COLUMN_DEFAULT.ten_phan_loai_nhom_1: option_name
            }

            # lay ma phan loai cho tung phan loai
            for sku_short in raw_data['models']:
                if sku_short['name'] == option_name:
                    variation[COLUMN_DEFAULT.sku_phan_loai] = random_item_id()
                    variation[COLUMN_DEFAULT.gia] = get_price(sku_short) / 100000
                    variation[COLUMN_DEFAULT.kho] = sku_short['stock']
            variations.append(variation)
    return variations


def write_to_csv(data):
    # convert json to list row
    rows = []
    for item_in_list in data:
        row = []
        for key in item_in_list.keys():
            row.append(item_in_list[key])
        rows.append(row)

    with open(EXPORT_FILENAME, 'w', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter='~')
        for row in rows:
            writer.writerow(row)


def modify_name_product(name):
    return f"{MODIFY['PREFIX_NAME']} {name} {MODIFY['SUFFIX_NAME']}"


def modify_description(text):
    return f"""
    {MODIFY['PREFIX_DESCRIPTION']}
    {text}
    {MODIFY['SUFFIX_DESCRIPTION']}
    """


# @todo: change hash image
def upload_image(hash):
    return hash


def link_shopee(hash):
    return f'http://cf.shopee.vn/file/{hash}'


def crawling(item_id):
    raw_data = get_detail_from_shopee(item_id)

    # Phan du lieu chung cua 1 SAN PHAM
    data_formated = {
        COLUMN_DEFAULT.nganh_hang: get_category(raw_data),
        COLUMN_DEFAULT.ten_san_pham: modify_name_product(raw_data['name']),
        COLUMN_DEFAULT.mo_ta: modify_description(raw_data['description']),
        COLUMN_DEFAULT.sku_san_pham: raw_data['itemid'],
        COLUMN_DEFAULT.ma_san_pham: get_product_id(raw_data),
        COLUMN_DEFAULT.ten_nhom_phan_loai_1: '',
        COLUMN_DEFAULT.ten_phan_loai_nhom_1: '',
        COLUMN_DEFAULT.hinh_anh_phan_loai: '',
        COLUMN_DEFAULT.ten_nhom_phan_loai_2: ' ',
        COLUMN_DEFAULT.ten_phan_loai_nhom_2: ' ',
        COLUMN_DEFAULT.gia: 0,
        COLUMN_DEFAULT.kho: 0,
        COLUMN_DEFAULT.sku_phan_loai: '',
        COLUMN_DEFAULT.anh_bia: link_shopee(raw_data['image']),
        COLUMN_DEFAULT.hinh1: '',
        COLUMN_DEFAULT.hinh2: '',
        COLUMN_DEFAULT.hinh3: '',
        COLUMN_DEFAULT.hinh4: '',
        COLUMN_DEFAULT.hinh5: '',
        COLUMN_DEFAULT.hinh6: '',
        COLUMN_DEFAULT.hinh7: '',
        COLUMN_DEFAULT.hinh8: '',
        COLUMN_DEFAULT.can_nang: WEIGHT_DEFAULT,
        COLUMN_DEFAULT.dai: LENGTH_DEFAULT,
        COLUMN_DEFAULT.rong: WIDTH_DEFAULT,
        COLUMN_DEFAULT.cao: HEIGHT_DEFAULT,
        COLUMN_DEFAULT.ghn: DELIVERY_DEFAULT['ghn'],
        COLUMN_DEFAULT.jnt: DELIVERY_DEFAULT['jnt'],
        COLUMN_DEFAULT.ninja: DELIVERY_DEFAULT['ninja'],
        COLUMN_DEFAULT.bestexpress: DELIVERY_DEFAULT['bestexpress'],
        COLUMN_DEFAULT.viettelpost: DELIVERY_DEFAULT['viettelpost'],
        COLUMN_DEFAULT.ghtk: DELIVERY_DEFAULT['ghtk'],
        COLUMN_DEFAULT.vnpost: DELIVERY_DEFAULT['vnpost'],
        COLUMN_DEFAULT.ps_product_pre_order_dts: PRE_ORDER
    }

    ###
    # if int(data_formated[COLUMN_DEFAULT.ma_san_pham]) not in include:
    #     return ''
    ###

    # @todo: upload to another server | switch thứ tự
    append_images(data_formated, raw_data)

    # Tách row theo phân loại
    results = []
    variations = split_by_variation(raw_data)
    for variation in variations:
        temp = copy.deepcopy(data_formated) # clone variable
        for key in variation:
            temp[key] = variation[key]

        # sử dụng ảnh cover làm ảnh phân loại
        if not temp[COLUMN_DEFAULT.hinh_anh_phan_loai]:
            temp[COLUMN_DEFAULT.hinh_anh_phan_loai] = link_shopee(raw_data['image'])

        results.append(temp)

    return results


def get_item_onl():
    url = f'https://shopee.vn/api/v2/search_items/?by=pop&limit=100&match_id={SHOP_ID}&newest=0&order=desc&page_type=shop&version=2'
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
        'Accept': '*/*',
        'Accept-Language': 'vi-VN,vi;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': 'https://shopee.vn/tuhuucuong',
        'X-Shopee-Language': 'vi',
        'X-Requested-With': 'XMLHttpRequest',
        'X-API-SOURCE': 'pc'
    }
    items = get(url, headers=custom_headers).json()['items']

    data_to_export = []
    for item in items:
        temp = crawling(item['itemid'])
        if temp == '': continue
        data_to_export = data_to_export + temp

    write_to_csv(data_to_export)


if __name__ == '__main__':
    UNIQUE_LIST = []
    get_item_onl()
