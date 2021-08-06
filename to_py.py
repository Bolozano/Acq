# -*- coding: utf-8 -*-
"""template based.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1hzMF5gjsdkAVMmuh2NU7p7hd3B_hQ4ae

# MaMa Algorithme  -LM to KG
"""

# !pip install -U spacy
# !pip install langid
# !pip install --upgrade py2neo

# !pip install -q transformers

# !pip install torch

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

# tokenizer = BertTokenizer.from_pretrained('bert-base-cased')  #there are multilingue model
# model = BertModel.from_pretrained('bert-base-cased',output_attentions=True).cuda()

import spacy.cli
spacy.cli.download("en_core_web_sm")

import spacy
nlp=spacy.load('en_core_web_sm')

# from google.colab import drive
# drive.mount('/content/drive')

#@title
# !pip install --upgrade py2neo

# %cd /
# !pwd
# !git clone https://github.com/Bolozano/relation_extraction.git
# %cd relation_extraction
# !python to_py.py c9cuW!izMoCUcyDdp-qwbhc 2021-07-01 2021-07-02

"""# Data Processing"""

#@title Neo4J Credentials
neo4jUser = "intern2021" #@param {type:"string"}
from getpass import getpass

neo4jPassword = sys.argv[1]
print (f"neo4jUser: {neo4jUser}")
# print (f"neo4jPassword: {neo4jPassword}")

# neo4jUser = "intern2021" #@param {type:"string"}
# from getpass import getpass

# neo4jPassword = 'c9cuW!izMoCUcyDdp-qwbhc'
# print (f"neo4jUser: {neo4jUser}")

from py2neo import Graph

graph = Graph("bolt+s://db-3ib8ouj9xqqcy081668k.graphenedb.com:24786",
              auth=(neo4jUser, neo4jPassword))

# !pip install langid
import langid

# interesting_verbs=['inves','acqui','join','buy','rais','reach','receiv','parter','Inves','Acqui','Join','Buy','Rais','Reach','Receiv','Parter']
interesting_verbs=['acqui','denies','denied','refuse','not']

# text1='Doosan Bobcat Completes Acquisition of BOB-CAT Mowers, Steiner and Ryan Brands'
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

def delete_paranthese(text):
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
  score=0
  length=0
  doc=nlp(text)
  if len(doc)<3:
    return 0,[],{}
  text_pat,text_words=get_pattern(doc)
  for w in range(len(text_pat)):
    if'ACQUI' in text_pat[w]:
      y=w

  suitable_pattern=[]
  return_info={}
  consecutive_seq2=[]

  for pattern in patterns:
    pat=pattern[0]
    for w in range(len(pat)):
      if'ACQUI' in pat[w]:
        x=w
    info_structure=pattern[1]
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
    

    # if max(max(c))/len(pat)>score:
    #   score=max(max(c))/len(pat)
    #   suitable_pattern=pat
    #   length=len(pat)
    # elif max(max(c))/len(pat)==score:
    #   if len(pat)>len(suitable_pattern):
    #     score=max(max(c))/len(pat)
    #     suitable_pattern=pat
    #     length=len(pat)
  # print(consecutive_seq2)
  return score,suitable_pattern,return_info

def contain_entity(special_pos,noun_chunk):
  start=noun_chunk.start
  end=noun_chunk.end
  if [i for i in special_pos if i in range(noun_chunk.start,noun_chunk.end)]==[]:
    return False
  return True

def get_pattern(doc):
  
  pattern=[j.pos_ for j in doc]
  words=[j.text for j in doc]

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
    if noun_chunks_and_entities[j].label_=='NP':
      
      new_pattern.append('NOUN_CHUNK')
      new_words.append(noun_chunks_and_entities[j].text)
    
    else:
      new_pattern.append(noun_chunks_and_entities[j].label_)
      new_words.append(noun_chunks_and_entities[j].text)

    start=noun_chunks_and_entities[j].end
    end=noun_chunks_and_entities[j+1].start
    new_pattern=new_pattern+pattern[start:end]
    new_words=new_words+words[start:end]

  if noun_chunks_and_entities[-1].label_=='NP':

      new_pattern.append('NOUN_CHUNK')
      new_words.append(noun_chunks_and_entities[-1].text)
    
  else:
    new_pattern.append(noun_chunks_and_entities[-1].label_)
    new_words.append(noun_chunks_and_entities[-1].text)
  
  new_pattern=new_pattern+pattern[noun_chunks_and_entities[-1].end:]
  new_words=new_words+words[noun_chunks_and_entities[-1].end:]
  return new_pattern,new_words

p=[1,2,3,4]
print(p[0:3])

def lcs(a,b,x,y):
  lena=len(a)
  length_b=len(b)

  b=b[max(0,int(y-0.5-1.3*x)):min(length_b,int(y+0.5+1.3*(lena-x)))]
  length_add=max(0,int(y-1-1.3*x))
  lenb=len(b)

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



  # sub_seqa.append(x)
  # sub_seqb.append(y)

  # m=x
  # n=y
  # jump=0
  # while c[m][n]!=0:
  #   temp_flag=flag[m][n]
  #   if temp_flag=='up':
  #     m=m-1
  #   elif temp_flag=='left':
  #     n=n-1
  #     jump=jump+1
  #   else:
  #     jump=0
  #     sub_seqa.append(m-1)
  #     sub_seqb.append(n-1)
  #     n=n-1
  #     m=m-1
  #   if jump>2:
  #     break

  # m=x
  # n=y
  # jump=0
  # while m<lena and n<lenb:
    
  #   if flag[m+1][n]=='up':
  #     m=m+1
  #   elif flag[m][n+1]=='left':
  #     n=n+1
  #     jump=jump+1
  #   elif flag[m+1][n+1]=='ok':
  #     jump=0
  #     sub_seqa.append(m+1)
  #     sub_seqb.append(n+1)
  #     n=n+1
  #     m=m+1
  #   if jump>2:
  #     break
  # sub_seqa.sort()
  # sub_seqb.sort()
  
  return c,flag,sub_seqa,sub_seqb


# def find_consecutive_sequence(m,n,c,flag)
#   sub_seqa=[]
#   sub_seqb=[]
#   consecutive_sub_seqsb=[]
#   jump=0
#   while c[m][n]!=0:
#     temp_flag=flag[m][n]
#     if temp_flag=='up':
#       m=m-1
#     elif temp_flag=='left':
#       n=n-1
#       jump=jump+1
#     else:
#       jump=0
#       sub_seqa.append(m-1)
#       sub_seqb.append(n-1)
#       n=n-1
#       m=m-1
#     if jump>=2:
#       consecutive_sub_seqsb.append(sub_seqb)
#       consecutive_sub_seqsb=consecutive_sub_seqs+find_consecutive_sequence(lena,n,c,flag)
#       break
    
#   return consecutive_sub_seqs=[]



def printLcs(flag,a,i,j):
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
	if i==0 or j==0:
		return
	if flag[i][j]=='ok':
		get_lcs(flag,a,i-1,j-1)
		temp_lcs.append(a[i-1])
	elif flag[i][j]=='left':
		get_lcs(flag,a,i,j-1)
	else:
		get_lcs(flag,a,i-1,j)

# for i in news:
#   if 'acqui' in i['title']:
#     print(i['title'])
#     print(get_pattern(nlp(i['title'])))
#     # print([j.pos_ for j in nlp(i['title'])])
#     # print([[j,j.label_] for j in nlp(i['title']).ents])
#     # print([j for j in nlp(i['title']).noun_chunks])
#     print()

# print(len(pattern_list))
# poss={}
# # for i in pattern_list:
# #   for word in i[0]:
# #     if word in poss.keys():
# #       poss[word]=poss[word]+1
# #     else:
# #       poss[word]=1

# for i in pattern_list:
#   if 10>i[1]>0:
#     print(i[0],i[1],i[2][0])

# text='Tencent-led Consortium to Acquire 10% of Vivendi\'s Universal Music for $3.4 Billion'
# doc=nlp(text)
# for i in doc.noun_chunks:
#   print([i])
# print()
# for i in doc.ents:
#   print([i,i.label_])
# print(get_pattern(doc))

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
#           [['ORG', 'NOUN_CHUNK', 'ACQUIRES', 'NOUN_CHUNK', 'IN', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[5]}],
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
	  [['NOUN_CHUNK', 'TO', 'ACQUIRE', 'PERCENT', 'NOUN_CHUNK', 'OF', 'ORG', 'NOUN_CHUNK'],{'Acquire_COM':[0],'Acquired_COM':[6]}],
		

	


 




        
          
          
          
          
]

# news1 = graph.query("""
#     MATCH (n:News) 
#     WHERE 
#         n.publicationDate >= $before
#     AND n.publicationDate < $after
#     AND size(n.title) > 10
#   RETURN n.title as title        
#   """, {"before": "2021-03-01", "after": "2021-07-30"})

# examples=[]
# for i in news1:
#   if 'acqui' in i['title'].lower():
#     if langid.classify(i['title'])[0]!='en':
#       continue
#     examples.append(delete_paranthese (i['title']))
# templates=[[get_pattern(nlp(i))[0],i] for i in examples]
# pattern_list=[]
# for temp in templates:
#   pat=temp[0]
#   add=1
#   for i in pattern_list:
#     if pat==i[0]:
#       i[1]=i[1]+1
#       i[2].append(temp[1])
#       add=0
#   if add==1:
#     pattern_list.append([pat,0,[]])
  
# print(len(examples))

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

# text='InfoWest acquires AWI, merges networks - The Independent ...'
# find_suitable_pattern(patterns,text)

