'''
@author: v-lianji
'''
import random 
import numpy as np
#from numpy import mask_indices
import config
import codecs


def load_documents(infile):
    r'''
    infile format: id \t category \t title
    returns:
         doc2title,  doc2category
    '''
    doc2title, doc2category = {}, {} 
    with codecs.open(infile, 'r', 'utf-8') as rd:
        while True:
            line = rd.readline() 
            if not line:
                break 
            words = line.strip().split('\t')
            if len(words)!=3:
                continue
            doc_id, category, title = words[0], words[1], words[2]
            if not doc_id in doc2title:
                doc2title[doc_id] = title 
                doc2category[doc_id] = category
    return doc2title, doc2category


def load_article_content(infile):
    # infile format: id \t 0:0.2 3:0.6 ...
    res = {} 
    with open(infile, 'r') as rd:
        while True:
            line = rd.readline() 
            if not line:
                break 
            words = line.strip().split('\t')
            if len(words)!=2:
                continue 
            res[words[0]] = words[1]
    return res

def load_CDAE_data(infile, batch_size = 64, noise_ratio = 0.2, sample_negative = False):
    """
    infile format:  0:0.2 3:0.6...\t...\t...
                which indicates that x0 x1 belong to the same category, while x2 does not.
    returns a tuple:
        sp_indices: a matrix of [batch_size, 2] 
        sp_noised_values: a list of values (corrupted)
        sp_original_values: a list of values (original)
        sp_masked_indices
        sp_indices1: a matrix of [batch_size, 2] 
        sp_noised_values1: a list of values (corrupted)
        sp_original_values1: a list of values (original)
        sp_masked_indices1
        sp_indices2: a matrix of [batch_size, 2] 
        sp_noised_values2: a list of values (corrupted)
        sp_original_values2: a list of values (original)
        sp_masked_indices2
        num: number of rows. equals to len(sp_noised_values)
    """ 
    with open(infile, 'r') as rd:
        batch_data = [] 
        counter = 0 
        while True:
            line = rd.readline() 
            if not line:
                break 
            batch_data.append(line.strip())
            counter+=1 
            if counter>= batch_size:
                yield (*wrapper_CDAE_data(batch_data, noise_ratio, sample_negative), counter)
                batch_data = [] 
                counter = 0
        if counter>0:
            yield (*wrapper_CDAE_data(batch_data, noise_ratio, sample_negative), counter)
        counter = 0
        
def wrapper_CDAE_data(data, noise_ratio , sample_negative ):
    data00, data01, data02 = [],[],[] 
    for line in data:
        tokens = line.split('\t')
        data00.append(tokens[0])
        data01.append(tokens[1])
        data02.append(tokens[2])
    return (*wrapper_autoencoder_data(data00, noise_ratio, sample_negative), *wrapper_autoencoder_data(data01, noise_ratio, sample_negative), *wrapper_autoencoder_data(data02, noise_ratio, sample_negative))
           

def load_autoencoder_data(infile, batch_size = 64, noise_ratio = 0.2, sample_negative = False):
    """
    returns a tuple:
        sp_indices: a matrix of [*, 2]   * is determined by batch_size and number of words per line
        sp_noised_values: a list of values (corrupted)
        sp_original_values: a list of values (original)
        sp_mask_indices: like sp_indices, may contain more rows due to sampling negative words
        num: number of rows. equals to min(batch_size, rows)
    """
    with open(infile, 'r') as rd:
        batch_data = [] 
        counter = 0 
        while True:
            line = rd.readline() 
            if not line:
                break 
            batch_data.append(line.strip())
            counter+=1 
            if counter>= batch_size:
                yield (*wrapper_autoencoder_data(batch_data, noise_ratio, sample_negative), counter)
                batch_data = [] 
                counter = 0
        if counter>0:
            yield (*wrapper_autoencoder_data(batch_data, noise_ratio, sample_negative), counter)
        counter = 0

def wrap_ae_data(one_tfidf, noise_ratio = 0.2 , sample_negative = False):
    indices = [] 
    noised_values = [] 
    original_values = [] 
    mask_indices = []
    
    line_num = 0 

    pairs = [(p[0],p[1]) for p in one_tfidf]
    for p in pairs:
        indices.append([line_num, p[0]])
        noised_values.append(p[1] * (1 - noise_ratio))
        original_values.append(p[1]) 

    if sample_negative:
        cur_set = set([p[0] for p in pairs])
        sam_cnt = len(cur_set)
        for _ in range(sam_cnt):
            cur_sam =   sample_one_neg_word() 
            if cur_sam not in cur_set:
                cur_set.add(cur_sam)
        cur_list = list(cur_set)
        cur_list.sort() 
        
        for p in cur_list:
            mask_indices.append([line_num, p])
    else:
        mask_indices = indices
                
    return (np.asarray(indices, dtype=np.int64), np.asarray(noised_values, dtype=np.float32), np.asarray(original_values, np.float32), np.asarray(mask_indices, dtype=np.int64))    

            
def wrapper_autoencoder_data(data, noise_ratio, sample_negative):
    indices = [] 
    noised_values = [] 
    original_values = [] 
    
    mask_indices = []
    
    line_num = 0 
    for line in data:
        pairs = [(lambda a,b: (int(a),float(b)))(*word.split(':'),) for word in line.split(' ')]
        for p in pairs:
            indices.append([line_num, p[0]])
            noised_values.append(0 if random.random() < noise_ratio else p[1])
            original_values.append(p[1])            

        if sample_negative:
            cur_set = set([p[0] for p in pairs])
            sam_cnt = len(cur_set)
            for _ in range(sam_cnt):
                cur_sam =   sample_one_neg_word() 
                if cur_sam not in cur_set:
                    cur_set.add(cur_sam)
            cur_list = list(cur_set)
            cur_list.sort() 
            
            for p in cur_list:
                mask_indices.append([line_num, p])
            
        line_num += 1 
        
    if not sample_negative:
        mask_indices = indices
    
    return (np.asarray(indices, dtype=np.int64), np.asarray(noised_values, dtype=np.float32), np.asarray(original_values, np.float32), np.asarray(mask_indices, dtype=np.int64))    

def sample_one_neg_word():
    return random.randint(0, config.VOC_SIZE-1)

def load_article_embeddings(infile):
    res = {} 
    with open(infile,'r') as rd:
        while True:
            line = rd.readline() 
            if not line:
                break 
            words = line.strip().split('\t')
            res[words[0]] = np.array([float(token) for token in words[1].split(' ')], dtype=np.float32)
            dim = res[words[0]].shape[0]
    return res,dim

     
def load_rnnRS_data(trainfile, articlefile, batch_size = 64):
    '''
    returns a tuple:
      user_history: a tensor of [batch_size, time_steps, dim] 
      target_items: a matrix of [batch_size, dim] 
      labels:  [batch_size, 1] 
      user_history_lens: [batch_size] 
      max_len:  max(user_history_lens),
      batch_size
    '''  
    article_embeddings , dim = load_article_embeddings(articlefile)
    with open(trainfile,'r') as rd :
        counter = 0 
        user_history =  [] 
        target_items = []
        labels = []
        user_history_lens = []
        while True:
            line = rd.readline() 
            if not line:
                break    
            
            words = line.strip().split('\t')
            
            one_history = [article_embeddings[k] if k in article_embeddings else np.zeros(dim, dtype=np.float32) for k in words[0].split(' ')]
            article = article_embeddings[words[1]] if words[1] in article_embeddings else np.zeros(dim,dtype=np.float32)
            
            labels.append(float(words[2]))
            target_items.append(article)
            user_history_lens.append(len(one_history))
            user_history.append(one_history)
             
            counter+=1 
            if counter>=batch_size:
                max_len = max(user_history_lens)
                zero_padding(user_history, max_len, dim)
                yield ( np.asarray(user_history, dtype=np.float32), np.asarray(target_items, dtype=np.float32), np.reshape(np.asarray(labels, dtype=np.float32),(-1,1)),
                        np.asarray(user_history_lens, dtype=np.int64), max_len, counter)
                user_history = [] 
                target_items = [] 
                labels= [] 
                user_history_lens = []
                counter=0

        if counter>0:
            max_len = max(user_history_lens)
            zero_padding(user_history, max_len, dim)
            yield ( np.asarray(user_history, dtype=np.float32), np.asarray(target_items, dtype=np.float32), np.reshape(np.asarray(labels, dtype=np.float32),(-1,1)),
                        np.asarray(user_history_lens, dtype=np.int64), max_len, counter)
            user_history = [] 
            target_items = [] 
            labels= [] 
            user_history_lens = []
            counter=0

def zero_padding(user_history, max_len, dim):
    for history in user_history:
        while len(history)<max_len:            
            history.append(np.zeros(dim, dtype=np.float32))
    
      
def load_avgRS_data(trainfile, articlefile, batch_size = 64):
    '''
    returns :
    batch_X: a matrix of [batch_size, dim]
    batch_Y: [batch_size, 1]
    '''  
    article_embeddings , dim = load_article_embeddings(articlefile)
    with open(trainfile,'r') as rd :
        counter = 0 
        batch_X =  [] 
        batch_Y = []
        while True:
            line = rd.readline() 
            if not line:
                break    
            
            words = line.strip().split('\t')
            history = np.mean([article_embeddings[k] if k in article_embeddings else np.zeros(dim, dtype=np.float32) for k in words[0].split(' ')], axis = 0) 
            article = article_embeddings[words[1]] if words[1] in article_embeddings else np.zeros(dim,dtype=np.float32)
            batch_Y.append(float(words[2]))
            batch_X.append(history*article)
            
            counter+=1 
            if counter>=batch_size:
                yield (np.asarray(batch_X, dtype=np.float32), np.reshape(np.asarray(batch_Y, dtype=np.float32),(-1,1)), counter)
                batch_X = [] 
                batch_Y = [] 
                counter= 0 

        if counter>0:
            yield (np.asarray(batch_X, dtype=np.float32), np.reshape(np.asarray(batch_Y, dtype=np.float32),(-1,1)), counter)
