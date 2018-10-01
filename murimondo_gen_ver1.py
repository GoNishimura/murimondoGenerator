
# coding: utf-8

# In[1]:


import re
import bs4
import sys
import MeCab
import urllib.request
from pprint import pprint
import json
from urllib.parse import urlparse
import time
#from gensim.models.word2vec import Word2Vec
from gensim.models import KeyedVectors
import time
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
# download chromedriver for using Google Search
import pandas as pd
import numpy as np
from sklearn.externals import joblib


# In[2]:


# are there 1015474 words inside? check len(model.similar_by_word('戦車', topn=False)). Maybe it doesn't care about itself
model = KeyedVectors.load_word2vec_format('/Users/Go/Documents/myapps/py/entity_vector/entity_vector.model.bin', binary=True)


# In[60]:


def mecab_parser(word, use_neologd=False):
    if use_neologd == False: m = MeCab.Tagger()
    else: m = MeCab.Tagger("-d /usr/local/lib/mecab/dic/mecab-ipadic-neologd")
    parsed = [[chunk.split('\t')[0], tuple(chunk.split('\t')[1].split(','))] for chunk in m.parse(word).splitlines()[:-1]] 
    return parsed # [ ['一', ('名詞', '数', '*', '*', '*', '*', '一', 'イチ', 'イチ')], ... ]


# In[61]:


# encode req. words (in Japanese) into utf8
def utf8_encode(list_words):
    word_utf8 = [] # return: list of words in utf8 form
    
    for word in list_words:
        transfer_utf8 = str(word.encode('utf-8')) # encode into utf8 form and make it into string: b'\xe3\x82...\xaf'
        transfer_stripped = transfer_utf8[2:-1] # erase b and ': \xe3\x82...\xaf
        word_to_req = transfer_stripped.replace('\\x', '%').upper() # make it into request form: %E3%82...%AF
        word_utf8.append(word_to_req)
    
    return word_utf8


# In[62]:


# transfer input word into katakana
def katakanize(word_2_transfer):
    input_katakana = '' # to return
    if len(word_2_transfer) == len(re.findall('[ァ-ンー―]', word_2_transfer)): return word_2_transfer
    
    word_2_transfer = re.split('_', word_2_transfer)[0] # 片瀬_(藤沢市) -> 片瀬
    parsed = mecab_parser(word_2_transfer, use_neologd=True)
    for token in parsed:
        for data in token[1]: 
            if len(re.findall('[ァ-ンー―]', data)) == len(data): 
                input_katakana += data # ゴビサバク
                break # want to take only how to read, not with how to pronounce
    if len(re.findall('[ァ-ン]', input_katakana)) == 0: # if no katakana was found
        parsed = mecab_parser(word_2_transfer, use_neologd=False)
        for token in parsed:
            for data in token[1]:
                if len(re.findall('[ァ-ンー―]', data)) == len(data): 
                    input_katakana += data
                    break
    
    return input_katakana


# In[63]:


# make input word into hiragana
def hiraganize(word_2_transfer): # for example: 'ゴビサバク'
    input_katakana = katakanize(word_2_transfer)
    to_req = utf8_encode([input_katakana]) # encode req. words (in Japanese) into utf8

    # send url to the Google transliterate and get result
    url = 'http://www.google.com/transliterate?langpair=ja-Hira|ja&text=' + to_req[0] + '%2C' # '%2C' is a utf8 code for ' , '
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        body = json.load(res) # [['ゴビサバク', ['ゴビサバク', 'ごびさばく', 'ｺﾞﾋﾞｻﾊﾞｸ']]]
    hiragana = body[0][1][1]
    return hiragana # ごびさばく'


# In[64]:


# divide hiragana into parts
def partDivider(hiragana): # ex. ごびさばく
    list_parts = [hiragana] # final return: ['ごびさばく', 'ごびさば', 'びさばく', ... 'ばく']
    list_char = list(hiragana) # ['ご', 'び', 'さ', 'ば', 'く']
    
    for length_of_part in range(len(hiragana)-1, 1, -1): #... 3, 2: this frame move on the list_char to make a part.
        start_point = 0
        while start_point + length_of_part <= len(hiragana): # while frame is not out from the list_char
            part = ''
            for charID in range(start_point, start_point + length_of_part): # for each char in the frame
                part += list_char[charID] # concatenate into part
            if part not in list_parts: list_parts.append(part)
            start_point += 1
    return list_parts # ['ごびさばく', 'ごびさば', 'びさばく', ... 'ばく']


# In[65]:


# make hiragana into kanji and other transliteration
def kanjize_slow(list_2_transfer): # for example:  ['ごびさばく', 'ごびさば', 'びさばく', ... 'ばく']
    req_utf8 = [] # utf8 of request word
    to_req = [] # list of end of urls, list of concatenates of String in req_utf8
    list_kanji = [] # to return
    
    req_utf8 = utf8_encode(list_2_transfer) # encode req. words (in Japanese) into utf8
        
    # concatenate Strings in req_utf8 to send as url. Make sure Google transliterate don't take too big size of req.
    for idx, word_utf8 in enumerate(req_utf8):
        to_req.append(word_utf8 + '%2C') # '%2C' is a utf8 code for ' , '
    
    # send url to the Google transliterate and get result
    timer = 0 # timer for access
    for sub_req in to_req: # send small sized urls
        timer = time.perf_counter()
        url = 'http://www.google.com/transliterate?langpair=ja-Hira|ja&text=' + sub_req
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as res:
            list_kanji += json.load(res)
        if time.perf_counter() - timer < 1: time.sleep(1 - (time.perf_counter() - timer)) # wait for 1 sec before next access
    return list_kanji # [['ごびさばく', ['ゴビ砂漠', ...]], ['ごびさば', ['語尾サバ', '...]], ..., ['ばく', ['バク', 'ばく', ...]]]


# In[66]:


# faster, but there are some miss inside search
# make hiragana into kanji and other transliteration
def kanjize_fast(list_2_transfer): # for example:  ['ごびさばく', 'ごびさば', 'びさばく', ... 'ばく']
    req_utf8 = [] # utf8 of request word
    to_req = [] # list of end of urls, list of concatenates of String in req_utf8
    list_kanji = [] # to return
    
    req_utf8 = utf8_encode(list_2_transfer) # encode req. words (in Japanese) into utf8
        
    # concatenate Strings in req_utf8 to send as url. Make sure Google transliterate can't take too big size of req.
    sub_rq = '' # sub part of to_req
    sub_rq_length = 0 # cnt for the length of words inside sub_rq
    for idx, word_utf8 in enumerate(req_utf8):
        if sub_rq_length + len(word_utf8) <= 504: # if still long enough, append it to the sub_rq
            sub_rq += word_utf8 + '%2C' # '%2C' is a utf8 code for ' , '
            sub_rq_length += len(word_utf8) + 3
        else: # if not, put sub_rq into to_req, restart, and then put the word into the new sub_rq
            to_req.append(sub_rq)
            sub_rq = ''
            sub_rq_length = 0
            # same as above
            sub_rq += word_utf8 + '%2C' # '%2C' is a utf8 code for ' , '
            sub_rq_length += len(word_utf8) + 3
    to_req.append(sub_rq) # send last made sub_rq to the to_req
    
    # send url to the Google transliterate and get result
    timer = 0 # timer for access
    for sub_req in to_req: # send small sized urls
        timer = time.perf_counter()
        url = 'http://www.google.com/transliterate?langpair=ja-Hira|ja&text=' + sub_req
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as res:
            list_kanji += json.load(res)
        if time.perf_counter() - timer < 1: time.sleep(1 - (time.perf_counter() - timer)) # wait for 1 sec before next access
    return list_kanji # [['ごびさばく', ['ゴビ砂漠', ...]], ['ごびさば', ['語尾サバ', '...]], ..., ['ばく', ['バク', 'ばく', ...]]]


# In[67]:


# pick up words which make sense 
def chooseRealWords(list_translite):
    realWords = [] # to return
    
    for hiraganaID in range(len(list_translite)): # for each hiragana-sorted list of words
        for word in list_translite[hiraganaID][1]:
            parsed = mecab_parser(word, use_neologd=True)
            # [['ゴビ砂漠', ('名詞', '固有名詞', '一般', '*', '*', '*', 'ゴビ砂漠', 'ゴビサバク', 'ゴビサバク')]] if input_word: 'ゴビ砂漠'
            if (len(parsed) == 1 and # it is a one word
                word == parsed[0][1][6] and # there is no better expression
                len(parsed[0][1]) == 9 and # data is fully set
                len(word) != len(re.findall('[ぁ-んー―]', word)) and # not completely hiragana
                len(word) != len(re.findall('[a-z]', word.lower())) and # not completely english
                (len(word) != len(re.findall('[ぁ-んァ-ンー―]', word)) or len(word) > 2) # not completely hira/katakana, or longer than 2
               ): 
                try: model[word] # check if the word is in dic of w2v
                except KeyError: continue
                realWords.append(word)
    return realWords # ['ゴビ砂漠', '砂漠', ...]


# In[68]:


def get_syare(word, fast=False):
    global dajare_dic# dictionary of hiragana:kanji or word:dajare
    to_kanjize = [] # hiragana part which we met for the first time
    list_syare = [] # list of syare
                
    if word in dajare_dic: return dajare_dic[word] # if word was doubled, reuse it
    
    input_hiragana = hiraganize(word) # ごびさばく
    hinput_parts = partDivider(input_hiragana) # ['ごびさばく', 'ごびさば', 'びさばく', 'ごびさ', 'びさば', 'さばく', 'ごび', 'びさ', 'さば', 'ばく']
    
    for part in hinput_parts: # 'ごびさばく'
        if part not in dajare_dic: to_kanjize.append(part) # first contact
        else: list_syare.extend(dajare_dic[part]) # met before
        
    if to_kanjize != []: # there are words we met for the first time
        parts_translite = [] # [ ['ごびさばく', ['ゴビ砂漠', ...]], ['ごびさば', ['語尾サバ', '...]], ..., ['ばく', ['バク', 'ばく', ...] ]
        if fast: 
            parts_translite = kanjize_fast(to_kanjize) # gather in fast mode
            list_syare.extend(chooseRealWords(parts_translite)) # ['ゴビ砂漠',  '砂漠', ...]
        else: 
            parts_translite = kanjize_slow(to_kanjize) # gather in slow mode
            list_syare.extend(chooseRealWords(parts_translite)) # ['ゴビ砂漠',  '砂漠', ...]
            dajare_dic[word] = list_syare # record word:dajare
            for part in parts_translite: dajare_dic[part[0]] = chooseRealWords([part]) # record hiragana:kanji

    return list_syare


# In[69]:


def get_similar_word(word, num_sim_words):
    # if str
    to_return = []
    if type(word) == str: 
        try: list_sim = model.most_similar(word, [], num_sim_words)
        except KeyError:
            # make new word by adding known words into one vector
            vec_new_word = np.zeros_like(model['。'])
            parsed = mecab_parser(word, use_neologd=False)
            for part in parsed: # ['一', ('名詞', '数', '*', '*', '*', '*', '一', 'イチ', 'イチ')]
                try: model[part[0]]
                except KeyError: continue
                vec_new_word += model[part[0]]
            list_sim = model.most_similar([vec_new_word], [], num_sim_words)
        
        # if word_sim was part of word or was one hira/kata character, remove it
        for word_sim in list_sim: # ('[畝_(単位)]', 0.5915420055389404)
            # take it as teiritu if
            if (word.find(re.sub('[\[\]]', '', word_sim[0])) == -1 and # if no word_sim found inside given[0]
                len(word_sim[0]) > 1 or len(re.findall('[ぁ-んァ-ン]', word_sim[0])) != len(word_sim[0]) # is not a one hira/kata character
               ): 
                to_return.append(word_sim)
   
    # if vec
    else: 
        list_sim = model.most_similar([word], [], num_sim_words)
        for word_sim in list_sim:
            if len(word_sim[0]) > 1 or len(re.findall('[ぁ-んァ-ン]', word_sim[0])) != len(word_sim[0]): # is not a one hira/kata character
                to_return.append(word_sim)
            
    return to_return


# In[70]:


# calulate cosine similarity
def cos_sim(word_or_vec1, word_or_vec2):
    if type(word_or_vec1) == str: v1 = model[word_or_vec1]
    else: v1 = word_or_vec1
    if type(word_or_vec2) == str: v2 = model[word_or_vec2]
    else: v2 = word_or_vec2
    
    return (np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


# In[111]:


# reference: https://qiita.com/orangain/items/6a166a65f5546df72a9d
# execute search on Google and return num of hits
# when using bs4, access wii be forbidden (403)
def search_hits(list_words, close_driver=True):
    global driver
    try: driver.get('https://www.google.co.jp/') # if driver is still open, reuse it
    except:
        #options = ChromeOptions()
        #options.add_argument('--headless') # enable headless mode
        #driver = Chrome('/Users/Go/chromedriver', options=options) # on the first argument, set path to the chromedriver
        driver = Chrome('/Users/Go/chromedriver')
        driver.get('https://www.google.co.jp/')

    to_req = ''
    for idx, word in enumerate(list_words): # concatenate list_words into a String
        to_req += word
        if idx != len(list_words)-1: to_req += ' '
    input_element = driver.find_element_by_name('q') # input the words and search
    input_element.send_keys(to_req)
    input_element.send_keys(Keys.RETURN)    
    result = driver.find_elements_by_css_selector('div#resultStats')[0].text # 約 16,700,000 件 （0.21 秒）
    no_contain = driver.find_elements_by_css_selector('div.TXwUJf') # 含まれない：りんご
    if len(no_contain) > 0: result = -1
    if close_driver: driver.quit()  # terminate browser
    
    try: num_hits = int( result[2:].split(' ')[0].replace(',', '') ) # '約 16,700,000 件 （0.21 秒） ' -> '16700000'
    except: num_hits = 0

    return num_hits


# In[112]:


def search_page(search_word):
    global driver
    kata_search = katakanize(search_word)
    list_josuusi = []
    
    # search suusi
    boxes = driver.find_elements_by_css_selector('td[width="150"], td[width="430"]')
    for idx, b in enumerate(boxes):
        if idx%3 == 0:
            sounds = b.text.split('・') # there are words combined into one box
            for sound in sounds:
                if kata_search == katakanize(sound): # same sound
                    erase_idx = boxes[idx+1].text.find('[') # start of explanation
                    if erase_idx != -1 and boxes[idx+1].text[:erase_idx].find(search_word) != -1: # contains search word itself
                        ei = boxes[idx+2].text.find('　【知識】')
                        if ei != -1: list_josuusi.extend(boxes[idx+2].text[:ei].split('、')) # erase 【知識】and later
                        else: list_josuusi.extend(boxes[idx+2].text.split('、'))
                        break
                    elif erase_idx == -1 and boxes[idx+1].text.find(search_word) != -1: # contains search word itself
                        ei = boxes[idx+2].text.find('　【知識】')
                        if ei != -1: list_josuusi.extend(boxes[idx+2].text[:ei].split('、')) # erase 【知識】and later
                        else: list_josuusi.extend(boxes[idx+2].text.split('、'))
                        break
        if len(list_josuusi) > 0: break
    
    # if found josuusi, purify it and return
    if len(list_josuusi) > 0: 
        to_return = []
        
        for josuusi in list_josuusi:
            # if told to, redirect
            if josuusi.find('⇒') != -1: 
                key_box = driver.find_element_by_name("key") # input search word
                key_box.send_keys(josuusi[2:])
                search_button = driver.find_element_by_name("submit") # hit search
                search_button.click()
                search_page(josuusi[2:])
            else:
                word = josuusi.replace('一', '')
                word = word.replace(' など。', '') # sometimes in the last josuusi
                ei = word.find('（') # pronunciation
                if ei != -1: word = word[:ei]
                ei = word.find(' [') # explanation of usage
                if ei != -1: word = word[:ei]
                josuusis = word.split('・') # kanji with same meaning in a block: 匹・疋
                for j in josuusis:
                    to_return.append(j)
        
        for josuusi in to_return[:]: # word[exexex、exexex] -> [ 'word', 'exexex]' ] erase the one with ']'
            if josuusi.find(']') != -1: to_return.remove(josuusi)
        return to_return
    
    # if not found, go to the next page and execute this function again
    else:
        try: 
            next_button = driver.find_element_by_name("next")
            next_button.click()
            search_page(search_word, driver)
        except:
            print("We've Found NOTHING!!!")
            return driver


# In[118]:


def get_suusi(search_word, close_driver=True):
    global driver
    try: driver.get("https://www.benricho.org/kazu/")
    except: 
        #options = ChromeOptions()
        #options.add_argument('--headless') # enable headless mode
        #driver = Chrome('/Users/Go/chromedriver', options=options) # on the first argument, set path to the chromedriver
        driver = Chrome('/Users/Go/chromedriver')
        driver.get("https://www.benricho.org/kazu/")
        
    key_box = driver.find_element_by_name("key") # input search word
    key_box.send_keys(search_word)
    selecter = driver.find_element_by_name("print") # set num of results in a page
    selectInstance = Select(selecter)
    selectInstance.select_by_index(5)
    search_button = driver.find_element_by_name("submit") # hit search
    search_button.click()

    result = driver.find_elements_by_css_selector('div > table > tbody > tr > td[valign="middle"]')[0]
    numbers = re.findall('[0-9]', result.text) # ■ヒット数 ： 0 件    -> ['0'], ■ヒット数 ： 120 件   -> ['1', '2', '0']
    #if close_driver: driver.quit()

    if numbers == ['0']: # hit = 0
        print('Josuusi not found')
        driver.quit()
        return []
    else: # hits!
        returned = search_page(search_word)
        if type(returned) == list: # if search was successful
            if close_driver: driver.quit()
            return returned
        else: # if search was not good
            returned.quit()
            try: driver.quit()
            except: 
                print("you can't quit this raw driver!")
                pass
            return []


# In[115]:


def upper_half(input_word):
    kata_num = ['ゼロ', 'レイ', 'イチ', 'ニ', 'サン', 'ヨン', 'ゴ', 'ロク', 'ナナ', 'ハチ', 'キュウ', 'ジュウ', 'ヒャク', 'セン', 'マン', 'オク', 'チョウ']
    kanji_num = '零一二三四五六七八九十百千万億兆'
    suusi = ''
    syare = ''
    teiritu = ''

    try: 
        model['[' + input_word + ']']
        input_word = '[' + input_word + ']'
    except: 
        try: model[input_word]
        except:
            print("we can't handle this word!")
            return []

    # get suusi and syare based on how to read the word
    kata_word = katakanize(input_word)
    for num in kata_num:
        if num in kata_word:
            if num == 'イチ':
                suusi = kanji_num[2]
                syare = kanji_num[1]
            else:
                suusi = kanji_num[1]
                if num == 'ニ': syare = kanji_num[2]
                if num == 'ゴ': syare = kanji_num[5]
                if num == 'サン': syare = kanji_num[3]
                if num == 'ヨン': syare = kanji_num[4]
                if num == 'ロク': syare = kanji_num[6]
                if num == 'ナナ': syare = kanji_num[7]
                if num == 'ハチ': syare = kanji_num[8]
                if num == 'セン': syare = kanji_num[12]
                if num == 'マン': syare = kanji_num[13]
                if num == 'オク': syare = kanji_num[14]
                if num == 'キュウ': syare = kanji_num[9]
                if num == 'ジュウ': syare = kanji_num[10]
                if num == 'ヒャク': syare = kanji_num[11]
                if num == 'チョウ': syare = kanji_num[15]
                if num == 'ゼロ' or num == 'レイ': syare = kanji_num[0]

    if syare == '':
        print("we can't find any syare in this word!")
        return []

    # get teiritu online
    list_teiritu = get_suusi(re.sub('[\[\]]', '', input_word), False) # delete '[' and ']'
    teiritu = list_teiritu[0]
    
    print('{}なのに{}({})とはこれ如何に'.format(suusi+teiritu, re.sub('[\[\]]', '', input_word),  syare,))
    return [suusi+teiritu, syare, re.sub('[\[\]]', '', input_word)]


# In[126]:


def lower_half(original_given, fast_mode=False):
    if original_given == []: return None
    given = original_given[:]
    given_vec = [np.zeros_like(model['。']) for i in range(3)]
    suusi = ''
    start_timer = 0 # timer of execution
    start_timer = time.perf_counter()


    # if 数詞, erase number ex: '一枚'
    word = original_given[0]
    if len(word) >= 2:
        pattern = '[一二三四五六七八九十百千1234567890１２３４５６７８９０]'
        res = re.search(pattern, word)
        if res != None:
            suusi = word[0] # 一
            given[0] = word[1] # 枚

    # if 数詞, set given word into word in correct context if exists
    if suusi != '':
        list_sim = model.most_similar([model[given[0]]+model[given[1]]], [], 10)
        for block in list_sim: # ('[畝_(単位)]', 0.5915420055389404)
            res = re.search(given[0], block[0])
            if res != None and res.start() == 1 and block[0][-2] == ')':
                given[0] = block[0] # 畝_(単位)
                break

    # if there are article in Wikipedia, use it.
    for idx, word in enumerate(given):
        try: given_vec[idx] += model[ '['+word+']' ]
        except: pass 
        try: given_vec[idx] += model[ word ] # if the word is not in dic, return error
        except KeyError: 
            print(word, "can't be used!")
            return None

    #print(given)
    time_ready = time.perf_counter()
    print()

    print('-----------MODE: TEIRITU FIRST----------------------')
    print()


    # get teiritu
    list_teiritu = get_similar_word(given_vec[0], 100) # [ ('一機', 0.5296095013618469), ... ]
    true_teiritu = [] #[ ['given[0]', []], ... ] since getting similar word in vec, it must contain itself

    for teiritu in list_teiritu: # ('一機', 0.5296095013618469)
        # if given[0] was suusi...
        if (suusi != '' and # given[0] is suusi
            len(re.split( '_', re.sub('[\[\]]', '', teiritu[0]) )[0]) == 1 and #'[畝_(単位)]' -> 畝
            teiritu[1] > 0.4 and # sim score between given_vec[0]
            [ teiritu[0], [] ] not in true_teiritu
           ): 
            true_teiritu.append( [ teiritu[0], [] ] )
        # elif not suusi && similarity was over 0.6 && teiritu[0] not in given
        elif suusi == '' and teiritu[1] > 0.6 and [ teiritu[0], [] ] not in true_teiritu: 
            true_teiritu.append( [ teiritu[0], [] ] )
        else: continue

    #print('true_teiritu:', true_teiritu) # [['輛', []], ['隻', []], ['挺', []], ['両', []], ['艘', []], ['個', []], ['ｔ', []], ['台', []], ['㎜', []], ['機', []]]


    # get list of hanteiritu
    for idx, teiritu in enumerate(true_teiritu): # ['機', []]
        list_hanteiritu =  model.most_similar(positive=[given[2], teiritu[0]], negative=[given[0]], topn=30) # 戦車+機-輌
        for tup in list_hanteiritu: # ('装甲車', 0.7579861283302307)
            # if len(hanteiritu) <= 8, it's hanteiritu. avoid heavy and long words
            to_check = re.split( '_', re.sub('[\[\]]', '', tup[0]) )[0]
            if len(to_check) <= 8: true_teiritu[idx][1].append(tup)

    #fast_mode = False
    true_answers = [] # list of [teiritu, syare, hanteiritu]
    ans_score = [] # list of scores of hanteiriu given 戦車+機-輌

    for idx, duo in enumerate(true_teiritu): # ['機', [('戦闘機', 0.757), ...]]: duo of teiritu and list of hanteiritu
        print('Progress:', round(100*idx/len(true_teiritu)), '%')
        for tup in duo[1]: # [ ('戦闘機', 0.757), ... ]
            try: hiraganize(re.sub('[\[\]]', '', tup[0]))
            except: continue
            #print('working on:', duo[0], hanteiritu.replace('[', '').replace(']', ''))
            list_syare = get_syare(re.split( '_', re.sub('[\[\]]', '', tup[0]) )[0], fast_mode) # get list of syare
            #print(list_syare)
            for syare in list_syare:
                to_go = [re.sub('[\[\]]', '', duo[0]), re.sub('[\[\]]', '', syare), re.sub('[\[\]]', '', tup[0])] # teiritu, syare, hanteiritu
                if (cos_sim(syare, given_vec[1]) > 0.5 and # two syare is somewhat sim
                    to_go not in true_answers and
                    re.sub('[\[\]]', '', (to_go[1]+to_go[2])) != re.sub('[\[\]]', '', (given[1]+given[2])) # avoid same (syare, hanteiritu)
                   ):
                    print('{}なのに{}({})と言うが如し\t\tscore: {}'.format(suusi+to_go[0], to_go[2], to_go[1], tup[1]))
                    true_answers.append(to_go)
                    ans_score.append(tup[1]) # score of hanteiriu given 戦車+機-輌

    time_teiritu = time.perf_counter()
    time_took = time_teiritu - start_timer
    print('time took in teiritu version: {:.0f}min {}sec:'.format(round(time_took/60), round(time_took%60)))
    print(len(true_answers), 'answers found')
    print()


    print('-----------MODE: HANTEIRITU FIRST----------------------')
    print()


    # get hanteiritu
    list_hanteiritu = get_similar_word(given_vec[2], 100) # [ ('戦闘機', 0.5296095013618469), ... ] 
    true_hanteiritu = []
    #fast_mode = False

    for idx, tup in enumerate(list_hanteiritu): # ('戦闘機', 0.5296095013618469)
        print('Searching 洒落. Progress:', round(100*idx/len(list_hanteiritu)), '%')
        try: hiraganize(re.sub('[\[\]]', '', tup[0]))
        except: continue
        list_syare = get_syare(re.split( '_', re.sub('[\[\]]', '', tup[0]) )[0], fast_mode) # get list of syare
        for syare in list_syare:
            if cos_sim(syare, given_vec[1]) > 0.5: true_hanteiritu.append([syare, tup[0]])

    #print('true_hanteiritu:', true_hanteiritu) # [ [syare, hanteiritu], ... ]


    # get teiritu
    for idx, _list in enumerate(true_hanteiritu): # [ ['千', '戦闘機'], ... ]
        print('Searching 定立. Progress:', round(100*idx/len(true_hanteiritu)), '%')
        list_teiritu =  model.most_similar(positive=[given[0], _list[1]], negative=[given[2]], topn=30) # 輌+戦闘機-戦車
        for tup in list_teiritu: # ('機', 0.7579861283302307)
            to_go = [re.sub('[\[\]]', '', tup[0]), re.sub('[\[\]]', '', _list[0]), re.sub('[\[\]]', '', _list[1])]
            if (
                (len(tup[0]) > 1 or len(re.findall('[ぁ-んァ-ン]', tup[0])) != len(tup[0])) and # is not a one hira/kata character
                (
                    (suusi[0] != '' and len(re.split( '_', re.sub('[\[\]]', '', tup[0]) )[0]) == 1 and tup[1] > 0.4) or # is suusi
                    (suusi[0] == '' and (res != None or tup[1] > 0.6)) # not suusi
                ) and
                to_go not in true_answers and
                re.sub('[\[\]]', '', (to_go[1]+to_go[2])) != re.sub('[\[\]]', '', (given[1]+given[2])) # don't use same (syare, hanteiritu)
               ):
                print('{}なのに{}({})と言うが如し\t\tscore: {}'.format(suusi+to_go[0], to_go[2], to_go[1], tup[1]))
                true_answers.append(to_go)
                ans_score.append(tup[1]) # score for teiritu given 輌+戦闘機-戦車

    time_hanteiritu = time.perf_counter()
    time_elpsd = time_hanteiritu - start_timer # <- at the top of this function
    time_between = time_teiritu - time_ready # <- before MODE: TEIRITU FIRST
    time_res = time_elpsd - time_between
    print('time took in hanteiritu version: {:.0f}min {}sec:'.format(round(time_res/60), round(time_res%60)))
    print(len(true_answers), 'answers found')
    print()
    

    # get current results
    current_answers = []
    for idx, ans in enumerate(true_answers):
        quartet = ans
        quartet.append(ans_score[idx])
        current_answers.append(quartet)

    current_answers.sort(key=lambda ans: ans[3], reverse=True) # sort by score
    print('{}なのに{}({})とはこれ如何に'.format(original_given[0], original_given[2], original_given[1]))
    print()
    for ans in current_answers:
            print('{}なのに{}({})と言うが如し\t\tscore: {}'.format(suusi+ans[0], ans[2], ans[1], ans[3]))
    print()


    # search good answers
    print('Wait for about', 1.3*len(true_answers), 'sec')
    tm = time.perf_counter()
    final_answers = []

    # for answers with same (syare and )hanteiritu, choose the best teiritu with the best score
    current_answers.sort(key=lambda quartet: quartet[1]) # sort by syare
    current_answers.sort(key=lambda quartet: quartet[2]) # sort by hanteiritu
    list_sh_checking = [current_answers[0][1], current_answers[0][2]] # [syare, hanteiritu] from the first answer
    list_ts_checking = [] # [teiritu, syare]
    cnt = 0 # counter for accessing Google
    for idx, quartet in enumerate(current_answers): # ['隻', '千', '戦艦', 0.702]
        print('Progress:', round(100*idx/len(current_answers)), '%')
        if [quartet[1], quartet[2]] == list_sh_checking: # if hanteiritu was what we are woking on right now
            list_ts_checking.append( (quartet[0], quartet[3]) ) # (teiritu, score)
        if [quartet[1], quartet[2]] != list_sh_checking or idx == len(current_answers)-1: # if not, or at last ans
            best_score = -1
            best_score_id = 0
            vec_score = 0
            for i, tup in enumerate(list_ts_checking): # ('隻', 0.987)
                small_timer = time.perf_counter()
                word1 = re.split('_', tup[0])[0]
                if suusi != '': word1 = '1'+word1 # if suusi, put '1' in front of the josuusi
                word2 = re.split('_', list_sh_checking[1])[0]
                # vec_score is two times important than num_hits. if last ans && last ts, close driver
                at_last_or_50 = ((idx == len(current_answers)-1) and (i == len(list_ts_checking)-1)) or (cnt != 0 and cnt%50==0)
                score = search_hits([word1, word2], at_last_or_50) * (tup[1]**2) 
                cnt += 1
                if tup[0] == 'ｔ': score /= 10 # ambiguous word
                print('{}\t{}\t{}\t{}'.format(tup[0], round(score), (tup[1]**2), score/(tup[1]**2)))
                if best_score < score:  # if 0 < 0, the word with higher vec_score will be chosen automatically by sorting at above
                    best_score = score
                    best_score_id = i
                    vec_score = tup[1]
                time_ep = time.perf_counter() - small_timer
                if time_ep < 1: time.sleep(1 - time_ep) # wait for 1 sec before next access
            # final answer will be chosen by score, but as for comparing with other answers, just use vec score
            final_answers.append([list_ts_checking[best_score_id][0], list_sh_checking[0], list_sh_checking[1], vec_score])
            print(list_ts_checking[best_score_id][0], list_sh_checking[0], list_sh_checking[1], vec_score)
            list_ts_checking = [ [quartet[0], quartet[3]] ] # go on to the answer we are working on
            list_sh_checking = [quartet[1], quartet[2]]

    if final_answers != []:
        final_answers.sort(key=lambda ans: ans[3], reverse=True) # ans: ['隻', '千', '戦艦', 0.775]

        print()
        print()
        print('{}なのに{}({})とはこれ如何に'.format(original_given[0], original_given[2], original_given[1]))
        print()
        for ans in final_answers:
            print('{}なのに{}({})と言うが如し\t\tscore: {}'.format(suusi+ans[0], ans[2], ans[1], ans[3]))

    else: print('Couldn\'t find answer...')
    print('Time took in selecting answers in sec:', time.perf_counter()-tm)
    print('per answer', (time.perf_counter()-tm)/len(true_answers))
    print('Total time:', round((time.perf_counter()-start_timer)/60), 'min', round((time.perf_counter()-start_timer)%60), 'sec')


# In[90]:


driver = Chrome('/Users/Go/chromedriver')
fast_mode = False
dajare_dic = joblib.load('dajare_dic.dic') # dictionary of hiragana:kanji or word:dajare
list_uh = upper_half('秋刀魚')
lower_half(list_uh, fast_mode)
if fast_mode == False: joblib.dump(dajare_dic, 'dajare_dic.dic', compress=True) # update dic only in slow version


# In[91]:


driver = Chrome('/Users/Go/chromedriver')
fast_mode = False
dajare_dic = joblib.load('dajare_dic.dic') # dictionary of hiragana:kanji or word:dajare
list_uh = upper_half('煎餅')
lower_half(list_uh, fast_mode)
if fast_mode == False: joblib.dump(dajare_dic, 'dajare_dic.dic', compress=True) # update dic only in slow version


# In[125]:


driver = Chrome('/Users/Go/chromedriver')
fast_mode = False
dajare_dic = joblib.load('dajare_dic.dic') # dictionary of hiragana:kanji or word:dajare
list_uh = upper_half('戦車')
lower_half(list_uh, fast_mode)
if fast_mode == False: joblib.dump(dajare_dic, 'dajare_dic.dic', compress=True) # update dic only in slow version


# In[122]:


# check activity monitor to see if there are any chromedrivers or Google Chrome remain opened
#if fast_mode == False: joblib.dump(dajare_dic, 'dajare_dic.dic', compress=True)
#driver.quit()

