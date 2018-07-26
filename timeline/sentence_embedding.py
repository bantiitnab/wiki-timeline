import numpy as np

EMBED_SIZE = 50

def get_coefs(word,*arr): 
    return word, np.asarray(arr, dtype='float32')

def get_token_probs(sentences):    
    token_counts = {}
    token_probs = {}
    total_tokens = 0
    for sentence in sentences:
        tokens = sentence.split()
        total_tokens += len(tokens)
        for token in tokens:
            token_count = token_counts.get(token, 0)
            token_counts[token] = token_count + 1
       

    # print('token_counts ', token_counts, total_tokens)
    for key, item in token_counts.items():
        token_probs[key] = item / total_tokens
    # print('token_probs ', token_probs)
    return token_counts, token_probs, total_tokens

def sentences_embedding(sentences, glove_file_path='./glove.6B/glove.6B.50d.txt', sentence=None):
    """
        sentence_embeddings formula used from 
        'A Simple but Tough-to-Beat Baseline for Sentence Embeddings'
        https://openreview.net/forum?id=SyK00v5xx
        word_embeddings used: Glove
        returns:
            numpy array of all sentence embeddings
    """    
    if len(sentences) == 0:
        return np.zeros([len(sentences), EMBED_SIZE])

    glove_file_path = 'static/glove.6B/glove.6B.50d.txt'
    embeddings_index = dict(get_coefs(*o.strip().split()) for o in open(glove_file_path))

    # get mean and std of embeddings
    all_embs = np.stack(embeddings_index.values())
    emb_mean, emb_std = all_embs.mean(), all_embs.std()

    # get probability of each token
    token_counts, token_probs, total_tokens = get_token_probs(sentences)
    
    # build sentence embedding
    # sentence embedding is a linear weighted sum of word embeddings
    sen_embs = np.zeros([len(sentences), EMBED_SIZE])
    alpha = 1.0
    for i, sentence in enumerate(sentences):        
        tokens = sentence.split()        
        sentence_embedding = np.zeros(EMBED_SIZE)
        for j, token in enumerate(tokens):
            token_coef = alpha / (alpha + token_probs[token])
            embedding_vector = embeddings_index.get(token, np.random.normal(emb_mean, emb_std, (EMBED_SIZE)))
            sentence_embedding += token_coef * embedding_vector                              
        sentence_embedding /= len(tokens)
        sen_embs[i, :] = sentence_embedding
    # print('sentence embedding 1 ', sen_embs)

    # to make sentence embedding more better
    # we use SVD to get first singular vector of 
    # sen_emb.T = [sen_emb1, sen_emb2, ..,sen_embn]
    # and then do sen_embn -= uu.T.sen_embn for each 
    # sentence embedding
    sen_embs = sen_embs.T    
    U,S,V = np.linalg.svd(sen_embs)
    u = U[:, 0]    
    uut = np.matmul(np.expand_dims(u, axis=-1), u.reshape([1, u.shape[0]]))    
    sen_embs = sen_embs - np.matmul(uut, sen_embs)

    # print('sentence embedding 2 ', sen_embs)
    return sen_embs.T
    

def timeline_sentences_embeddings(timeline, glove_file_path):
    """
        return timeline as list of [line, dates, embedding]
    """
    # get sentences
    sentences = []
    for line, dates in timeline:
        sentences.append(line)

    # get their embeddings
    sentences_embeddings = sentences_embedding(sentences, glove_file_path)
    
    # add sentence embedding into timeline
    timeline_clone = []
    for i, event in enumerate(timeline):
        event.append(sentences_embeddings[i])
        timeline_clone.append(event)
    return timeline_clone


if __name__ == '__main__':
    sentences = [
        'John is a good person and great husband',
        'ALice loves apples and oranges',
        'They hate bad breath, but dont do anything about it',
        'We are sitting at airport',
        'Boys are girls were playing cricker',
        'Football is the best sports in some parts and cricket in some part',
        'John is a good person and great husband',
        'ALice loves apples and oranges',
        'They go bad breath, but dont do anything about it',
        'We are sitting at airport',
        'Boys are girls were playing cricker',
        'Football is the best life in some parts and cricket in some part',
        'John is a good person and great husband',
        'ALice loves apples and oranges',
        'They love bad air, but dont do anything about it',
        'We are sitting at airport',
        'Boys are girls were playing cricker',
        'Football is the worst sports in some parts and cricket in all part',
        'John is a good person and great husband',
        'ALice loves apples and oranges',
        'They hate bad breath, but dont do anything about it',
        'We are sitting at airport',
        'Boys are girls were lunching cricket',
        'Football is the best sports in some parts and cricket in some part'
    ]

    senteces_embeddings1 = sentences_embedding(sentences)
    print(senteces_embeddings)

    