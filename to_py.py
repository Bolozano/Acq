# -*- coding: utf-8 -*-
"""template based Acquire detection.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1hzMF5gjsdkAVMmuh2NU7p7hd3B_hQ4ae

# MaMa Algorithme  -LM to KG
"""

#!pip install -U spacy
#!pip install langid
#!pip install --upgrade py2neo

# #you can simply call this patterned-based methode from github
# !git clone https://github.com/Bolozano/Acq.git
# %cd Acq                         
# !python to_py.py c9cuW!izMoCUcyDdp-qwbhc 2021-05-01 2021-05-10  #password start_time end_time

import string
from tqdm.notebook import tqdm
import pickle
import gc
import re
import json
import time
import numpy as np
import copy
import sys
import langid

# tokenizer = BertTokenizer.from_pretrained('bert-base-cased')  #there are multilingue model
# model = BertModel.from_pretrained('bert-base-cased',output_attentions=True).cuda()

import spacy.cli
spacy.cli.download("en_core_web_sm")

import spacy
nlp=spacy.load('en_core_web_sm')

# from google.colab import drive
# drive.mount('/content/drive')

"""# Data Processing"""

#@title Neo4J Credentials
neo4jUser = "intern2021" #@param {type:"string"}
from getpass import getpass

neo4jPassword = sys.argv[1]
print (f"neo4jUser: {neo4jUser}")
# print (f"neo4jPassword: {neo4jPassword}")

from py2neo import Graph
graph = Graph("bolt+s://db-3ib8ouj9xqqcy081668k.graphenedb.com:24786",
              auth=(neo4jUser, neo4jPassword))

#if a token contain interesting verb, it will not be transformed to token.pos_
#For example, [I, love, to, acquire, companies,.]==>['NOUN_CHUNK', 'VERB', 'TO', 'ACQUIRE', 'NOUN_CHUNK', 'PUNCT']
#acquire is kept as ACQUIRE not VERB
interesting_verbs=['acqui','denies','denied','refuse','not']

def delete_paranthese(text):
  """delete all the (xxxxx) in text
  """
  i=0
  k=0
  while len(text)>i:
    if text[i] != '(':
      if text[i]==')':
        text=text[:i]+text[(i+1):]
        continue
      i=i+1
      continue
    else:
      k=i
      for j in range(i,len(text)):
        if text[j]==')':
          k=j
          break
      text=text[:i]+text[(k+1):]
  return text

def find_suitable_pattern(patterns,text):
  """find the best pattern for text

  Args:
    patterns: list of patterns defined afterwards
    text: text to analyse
  
  Return:
    the pattern found most suitable
  
  """
  score=0
  length=0
  doc=nlp(text)
  if len(doc)<3:
    return 0,[],{}
  #patternize the text = adpat the text in to ['NOUN_CHUNK', 'VERB', 'TO', 'ACQUIRE', 'NOUN_CHUNK', 'PUNCT']
  text_pat,text_words=get_pattern(doc)
  #y=the position of 'Acquire' in text
  for w in range(len(text_pat)):
    if'ACQUI' in text_pat[w]:
      y=w

  suitable_pattern=[]
  return_info={}
  consecutive_seq2=[]
  
  for pattern in patterns:
    pat=pattern[0]              #the pattern as a list ['NOUN_CHUNK', 'VERB', 'TO', 'ACQUIRE', 'NOUN_CHUNK', 'PUNCT']
    for w in range(len(pat)):
      if'ACQUI' in pat[w]:
        x=w                   #x=the position of 'Acquire' in pattern
    info_structure=pattern[1]  #knowledge in the pattern like {'Acquire_COM':[0],'Acquired_COM':[2]}
    temp_return_info= copy.deepcopy(info_structure)

    c,flag,seq1,seq2=lcs(pat,text_pat,x,y)
    temp_score=1
    consecutive_seq2=[seq2[i+1]-seq2[i] for i in range(len(seq2)-1)]
 
    if len(consecutive_seq2)>0:
      if max(consecutive_seq2)>2:
        # print('not consecutive')
        continue
    important_pos=[]

    for val in info_structure.values():
      important_pos=important_pos+val

    contain_structure=[False for c in important_pos if c not in seq1]

    if len(contain_structure)==0:
      if max(max(c))/len(pat)>0.8:
        if len(pat)>len(suitable_pattern):

          score=max(max(c))/len(pat)
          suitable_pattern=pat
          length=len(pat)
          for key in info_structure.keys():
            
            for word_pos in range(len(info_structure[key])):
              temp_return_info[key][word_pos]=text_words[seq2[seq1.index(info_structure[key][word_pos])]]
          
          return_info=temp_return_info
  
  return score,suitable_pattern,return_info

def contain_entity(special_pos,noun_chunk):
  """To see if 

  Args: 
  special_pos: position of interesting_verbs like ['acqui','denies','denied','refuse','not'] or ['CCONJ','ADP','PART']
  noun_chunk: noun_chunk or entity that risk of covering special_pos

  Return True or False
  """
  start=noun_chunk.start
  end=noun_chunk.end
  if [i for i in special_pos if i in range(noun_chunk.start,noun_chunk.end)]==[]:
    return False
  return True

def get_pattern(doc):
  """convert a list of tokens to pattern

  Args:
    doc: doc=nlp(text)

  Return:
    new_pattern: like this ['NOUN_CHUNK', 'VERB', 'TO', 'ACQUIRE', 'NOUN_CHUNK', 'PUNCT']
    new_words: like this ['I', 'love', 'to', 'acquire', 'companies', '.']

  """
  pattern=[j.pos_ for j in doc]
  words=[j.text for j in doc]

  #special_pos: position of interesting_verbs like ['acqui','denies','denied','refuse','not'] or ['CCONJ','ADP','PART']
  #because we want these special token continue to exist in the text_pattern to compare with pattern, so they should'nt be covered by entity or noun_chunk
  special_pos=[]
  for i in range(len(doc)):
    for word in interesting_verbs:
      if word in doc[i].text.lower():
        pattern[i]=doc[i].text.upper()
        special_pos.append(i)
        break
    if pattern[i] in ['CCONJ','ADP','PART']:
      pattern[i]=doc[i].text.upper()
      special_pos.append(i)

  #if a noun_chunk or entity. doesn't cover  special position we replace it by "NOUN_CHUNK" or "ENTITY" to patternize the text
  noun_chunks_and_entities=[]
  for ent in doc.ents:
    if contain_entity(special_pos,ent)==False:
      noun_chunks_and_entities.append(ent)

  for noun_chunk in doc.noun_chunks:
    if contain_entity(special_pos,noun_chunk)==False:
      noun_chunks_and_entities.append(noun_chunk)

  if len(noun_chunks_and_entities)<2:
    return pattern,words

  noun_chunks_and_entities.sort(key=lambda x: (x.start))

  new_pattern=pattern[:noun_chunks_and_entities[0].start]
  new_words=words[:noun_chunks_and_entities[0].start]
  for j in range(len(noun_chunks_and_entities)-1):
    #for noun_chunk, append NOUN_CHUNK
    if noun_chunks_and_entities[j].label_=='NP':
      new_pattern.append('NOUN_CHUNK')
      new_words.append(noun_chunks_and_entities[j].text)
    #for entities, append label_
    else:
      new_pattern.append(noun_chunks_and_entities[j].label_)
      new_words.append(noun_chunks_and_entities[j].text)

    start=noun_chunks_and_entities[j].end
    end=noun_chunks_and_entities[j+1].start
    new_pattern=new_pattern+pattern[start:end]
    new_words=new_words+words[start:end]
  #for noun_chunk, append NOUN_CHUNK
  if noun_chunks_and_entities[-1].label_=='NP':
      new_pattern.append('NOUN_CHUNK')
      new_words.append(noun_chunks_and_entities[-1].text)
  #for entities, append label_
  else:
    new_pattern.append(noun_chunks_and_entities[-1].label_)
    new_words.append(noun_chunks_and_entities[-1].text)
  
  new_pattern=new_pattern+pattern[noun_chunks_and_entities[-1].end:]
  new_words=new_words+words[noun_chunks_and_entities[-1].end:]
  return new_pattern,new_words

def lcs(a,b,x,y):
  """find the longest-commun-sequence of a and b

  Args:
    a: the first sequence to treat
    b: second sequence to treat
    x: the indice of 'ACQ' in list a
    y: the indice of 'ACQ' in list b

  Return:
    c: matrix 
    flag: matrix
    sub_seqa: lcs with indices in a
    sub_seqb: lcs with indices in b

  """
  lena=len(a)
  length_b=len(b)

  #. we only care about the part of pattern which are close to 'Acquire'
  b=b[max(0,int(y-0.5-1.3*x)):min(length_b,int(y+0.5+1.3*(lena-x)))]
  length_add=max(0,int(y-1-1.3*x))
  lenb=len(b)

  #c-flag are matix for the lcs apogorithm which we will use to store and look for lcs.
  c=[[0 for i in range(lenb+1)] for j in range(lena+1)]
  flag=[[0 for i in range(lenb+1)] for j in range(lena+1)]
  for i in range(lena):
    for j in range(lenb):
      if a[i]==b[j]:
        c[i+1][j+1]=c[i][j]+1
        flag[i+1][j+1]='ok'
        
      elif c[i+1][j]>=c[i][j+1]:
        c[i+1][j+1]=c[i+1][j]
        flag[i+1][j+1]='left'
      else:
        c[i+1][j+1]=c[i][j+1]
        flag[i+1][j+1]='up'
  
  sub_seqa=[]
  sub_seqb=[]
  m=lena
  n=lenb
  while c[m][n]!=0:
    temp_flag=flag[m][n]
    if temp_flag=='up':
      m=m-1
    elif temp_flag=='left':
      n=n-1
    else:
      sub_seqa.append(m-1)
      sub_seqb.append(n-1)
      n=n-1
      m=m-1
  for i in range(len(sub_seqb)):

    sub_seqb[i]=sub_seqb[i]+length_add
  sub_seqa.sort()
  sub_seqb.sort()
  
  return c,flag,sub_seqa,sub_seqb


def printLcs(flag,a,i,j):
  """print the lcs sequence by Recursive fonction"""
  if i==0 or j==0:
    return
  if flag[i][j]=='ok':
    printLcs(flag,a,i-1,j-1)
    print(a[i-1],end=' ')
  elif flag[i][j]=='left':
    printLcs(flag,a,i,j-1)
  else:
    printLcs(flag,a,i-1,j)

def get_lcs(flag,a,i,j):
  """get the lcs sequence by Recursive fonction"""
  if i==0 or j==0:
    return
  if flag[i][j]=='ok':
    get_lcs(flag,a,i-1,j-1)
    temp_lcs.append(a[i-1])
  elif flag[i][j]=='left':
    get_lcs(flag,a,i,j-1)
  else:
    get_lcs(flag,a,i-1,j)

# """This cell can show very clearly the fonctionality of find_suitable_pattern for a sentence """
# text='InfoWest acquires AWI, merges networks - The Independent ...'
# find_suitable_pattern(patterns,text)

"""This cell can show very clearly the fonctionality of get_pattern for a sentence """

# text1='I love to acquire companies.'
# text2='Magal Completes the Acquisition of E.S.C. BAZ, Manufacturer of Security Video Observation & Surveillance Systems'
# doc1=nlp(text1)
# print(len(doc1))
# print(get_pattern(doc1))

# doc2=nlp(text2)
# print(get_pattern(doc2))
# c,flag,seq1,seq2=lcs(get_pattern(doc1)[0],get_pattern(doc2)[0],2,4)
# printLcs(flag,get_pattern(doc1),len(get_pattern(doc1)),len(get_pattern(doc2)))
# print(max(max(c)))
# temp_lcs=[]
# get_lcs(flag,get_pattern(doc1),len(get_pattern(doc1)),len(get_pattern(doc2)))
# print(seq1)
# print(seq2)
# for i in flag:
#   print(i)
# print([get_pattern(doc1)[0][i] for i in seq1]) 
# print([get_pattern(doc2)[0][i] for i in seq2])

# patterns with format [[pattern structure],{pattern_knowledge}]
patterns=[[['NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[2]}],
          [['NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK','FOR','MONEY'],{'Acquire_COM':[0],'Acquired_COM':[2],'Transaction_Amount':[4]}],
          [['PROPN', 'PROPN', 'ACQUIRES', 'PROPN', 'PROPN'],{'Acquire_COM':[0,1],'Acquired_COM':[3,4]}],
          [['PROPN', 'PROPN', 'PROPN', 'ACQUIRES', 'PROPN', 'PROPN', 'PROPN'],{'Acquire_COM':[0,1,2],'Acquired_COM':[4,5,6]}],
          [['ORG', 'NOUN_CHUNK', 'ACQUIRES', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[3]}],
          [['ORG', 'NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[3]}],
          [['NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[2]}],
          [['NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK', 'FROM', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[2],'From':[4]}],
          [[ 'ORG', 'TO', 'ACQUIRE', 'PERCENT', 'NOUN_CHUNK', 'OF', 'PERSON', "'S", 'ORG', 'FOR', 'MONEY'],{'Acquire_COM':[1],'Acquired_COM':[2],'From':[4]}],

          [['NOUN_CHUNK', 'PROPN', 'ACQUISITION', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [['ORG', 'NOUN_CHUNK', 'VERB', 'ACQUISITION', 'OF', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
          [[ 'NOUN_CHUNK', 'VERB', 'ACQUISITION', 'OF', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [[ 'NOUN_CHUNK', 'VERB','MONEY', 'ACQUISITION', 'OF', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5],'Transaction_Amount':[2]}],
          [['NOUN_CHUNK', 'VERB', 'ACQUISITION', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [['ORG', 'NOUN_CHUNK', '’S', 'ACQUISITION', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
          [['ADJ', 'PUNCT', 'PERSON', 'NOUN_CHUNK', 'AUX', 'VERB', 'VERB', 'ACQUISITION', 'OF', 'NOUN_CHUNK', 'PUNCT', 'PROPN'],{'Acquire_COM':[3],'Acquired_COM':[9]}],
          [['NOUN_CHUNK', 'VERB', 'DET', 'ACQUISITION', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5]}],

          [['ORG', 'NOUN_CHUNK', 'TO', 'ACQUIRE', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [['ORG', 'NOUN_CHUNK', 'TO', 'ACQUIRE', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [['NOUN_CHUNK', 'TO', 'ACQUIRE', 'NOUN_CHUNK'] ,{'Acquire_COM':[0],'Acquired_COM':[3]}],
          [['NOUN_CHUNK', 'VERB', 'NOUN_CHUNK', 'TO', 'ACQUIRE', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
          

          [['NOUN_CHUNK', 'ACQUIRED', 'BY', 'NOUN_CHUNK'],{'Acquire_COM':[3],'Acquired_COM':[0]}],

          [['NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK', 'IN', 'GPE', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[2],'Acquired_COM_GPE':[4]}],
          [['NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK', 'IN', 'GPE', 'NOUN_CHUNK','FOR','MONEY'],{'Acquire_COM':[0],'Acquired_COM':[2],'Acquired_COM_GPE':[4],'Transaction_Amount':[7]}],
          [['NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK', 'AND', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM1':[2],'Acquired_COM2':[4]}],
          [['NOUN_CHUNK', 'TO', 'ACQUIRE', 'NOUN_CHUNK', 'FOR', 'MONEY'],{'Acquire_COM':[0],'Acquired_COM':[3],'Transaction_Amount':[5]}],
          # [['NOUN_CHUNK', 'VERB', 'NOUN_CHUNK', 'WITH', 'PROPN', 'ACQUISITION'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [['NOUN_CHUNK', 'VERB', 'ACQUISITION', 'OF', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [['NOUN_CHUNK', 'ACQUIRES', 'PERCENT', 'NOUN_CHUNK', 'IN', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5],'Percentage':[2]}],
          [['ORG', 'NOUN_CHUNK', 'ACQUIRES', 'ORG', 'NOUN_CHUNK', 'FOR', 'MONEY'],{'Acquire_COM':[0],'Acquired_COM':[3],'Transaction_Amount':[6]}],
          [['PROPN', 'PROPN', "'", 'ACQUISITION', 'OF', 'NOUN_CHUNK', 'PUNCT', 'NOUN_CHUNK', 'PUNCT'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
          [['PROPN', 'PROPN', 'ACQUIRES', 'PROPN', 'PROPN', 'PROPN', 'IN', 'GPE', 'NOUN_CHUNK'],{'Acquire_COM':[0,1],'Acquired_COM':[3,4,5],'Acquired_COM_GPE':[7]}],

          [['PROPN', 'PROPN', "'", 'ACQUISITION', 'OF', 'NOUN_CHUNK', 'PUNCT', 'NOUN_CHUNK', 'PUNCT'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
          [['ORG', 'NOUN_CHUNK', 'TO', 'ACQUIRE', 'NOUN_CHUNK', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[6]}],
          [['NOUN', 'VERB', 'TO', 'ACQUIRE', 'PROPN'],{'Acquire_COM':[0],'Acquired_COM':[6]}],
          [['ORG', 'PROPN', 'ACQUIRES', 'NOUN_CHUNK', 'OF', 'ORG'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
          [['DET', 'PROPN', 'PROPN', 'PROPN', 'ACQUIRES', 'NOUN_CHUNK', 'IN', 'MONEY', 'NOUN_CHUNK'],{'Acquire_COM':[1,2,3],'Acquired_COM':[5],'Transaction_Amount':[7]}],
          [['ORG','ACQUIRES', 'NOUN_CHUNK', 'IN', 'MONEY', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[2],'Transaction_Amount':[4]}],
          [['NOUN_CHUNK', 'ACQUIRES', 'PROPN', 'PROPN', 'PROPN', 'IN', 'GPE', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[2,3,4],'Transaction_Amount':[6]}],
          [[ 'PROPN', 'PROPN', "'S", 'ACQUISITION', 'OF', 'NOUN_CHUNK', 'IN', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0,1],'Acquired_COM':[7]}],
          [['ADV', 'ORG', 'NOUN_CHUNK', '’S', 'ACQUISITION', 'AUX', 'ADJ', 'FOR', 'PERSON', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[2],'Transaction_Amount':[4]}],
          [['NOUN_CHUNK', 'TO', 'ACQUIRE', 'NOUN_CHUNK', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
          [['PROPN', 'ACQUIRES', 'PROPN', 'PROPN', 'PROPN'],{'Acquire_COM':[0],'Acquired_COM':[2,3,4]}],
          [['PROPN', 'PROPN', 'ACQUISITION', 'OF', 'PROPN'],{'Acquire_COM':[0,1],'Acquired_COM':[4]}],
          [['NOUN_CHUNK', 'PUNCT', 'NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK', 'PERCENT', 'NOUN', 'IN', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[8],'Percentage':[5]}],
          [['ORG', 'NOUN_CHUNK', 'VERB', 'ACQUISITION', 'OF', 'PERCENT', 'NOUN_CHUNK', 'IN', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[8],'Percentage':[5]}],
          [['ORG', 'NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK', 'IN', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
          [['ORG', 'AND', 'ORG', 'TO', 'ACQUIRE', 'ORG', 'NOUN_CHUNK', 'PUNCT', 'NOUN_CHUNK'],{'Acquire_COM1':[0],'Acquire_COM2':[2],'Acquired_COM':[5]}],
          [['NOUN_CHUNK', 'VERB', 'ACQUISITION', 'ON', 'ORG', 'NOUN_CHUNK', 'FROM', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4],'From':[7]}],
          [[ 'NOUN_CHUNK', 'TO', 'ACQUIRE', 'NOUN_CHUNK', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[3],'From':[5]}],
          [['PERSON', 'PROPN', 'ACQUISITION', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [['VERB', 'ACQUIRES', 'ORG', 'NOUN_CHUNK', 'TO'],{'Acquire_COM':[0],'Acquired_COM':[2]}],
          [['ORG', 'NOUN_CHUNK', 'ACQUIRES', 'NORP', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4],'Acquired_COM_GPE':[3]}],
          [['GPE', 'NOUN_CHUNK', 'ACQUIRED', 'BY', 'GPE', 'NOUN_CHUNK'],{'Acquire_COM':[5],'Acquired_COM':[2],'Acquired_COM_GPE':[0]}],
          [['ORG', 'NOUN_CHUNK', 'ACQUIRES', 'NOUN', 'PROPN', 'PROPN', 'AND', 'PROPN', 'PROPN', 'PROPN'],{'Acquire_COM':[3,4,5],'Acquired_COM':[7,8]}],
          [['ORG', 'NOUN_CHUNK', 'VERB', 'NOUN_CHUNK', 'WITH', 'ACQUISITION', 'OF', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[7]}],
          [[ 'PROPN', 'PROPN', "'S", 'ACQUISITION', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
          [['NOUN_CHUNK', '’S', 'ACQUISITION', 'OF', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [['GPE', '’S', 'PROPN', 'ACQUIRES', 'GPE', 'NOUN_CHUNK', 'PRODUCT', 'FOR', 'SYM', 'MONEY', 'NUM'],{'Acquire_COM':[2],'Acquired_COM':[5],'Acquire_COM_GPE':[0],'Acquired_COM_GPE':[4],'Transaction_Amount':[9]}],
          [['PROPN', 'ACQUIRES', 'PROPN'],{'Acquire_COM':[0],'Acquired_COM':[2]}],
          [['ORG', 'TO', 'ACQUIRE', 'NOUN_CHUNK', 'ORG', 'NOUN', 'NOUN', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[4]}],
          [['ORG', 'ACQUISITION', 'OF', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[3]}],        
]

news2 = graph.query("""
    MATCH (n:News) 
    WHERE 
        n.publicationDate >= $before
    AND n.publicationDate < $after
    AND size(n.title) > 10
  RETURN n.title as title        
  """, {"before": sys.argv[2], "after": sys.argv[3]})
sentences=[i['title'] for i in news2 if 'acqui' in i['title'].lower()]
for i in news2:
  if langid.classify(i['title'])[0]!='en':
    continue
  if 'acqui' in i['title'].lower():
    sentences.append(delete_paranthese( i['title'].replace('– TechCrunch','')))
print(len(sentences))

acq=[]
for sent in sentences:
  if langid.classify(sent)[0]!='en':
    continue
  
  score,suitable_pattern,return_info=find_suitable_pattern(patterns,sent)
  if score>0.8:
    print(sent)
    print(get_pattern(nlp(sent)))
    print(suitable_pattern)
    print(return_info)
    print()
    acq.append([sent,return_info])
  # else:
    # print(sent)
    # print(get_pattern(nlp(sent)))
    # print(find_suitable_pattern)
    # print()
print(len(acq))
h = open("acquire.json.txt", 'w+')
new_json=json.dumps(acq,indent=1)
h.write(new_json)
h.close()
