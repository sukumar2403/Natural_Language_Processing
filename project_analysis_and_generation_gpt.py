# -*- coding: utf-8 -*-
"""Project_Analysis_and_Generation_gpt.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1sZAowJG0P27IPNkQQ57clL9lFPsex4hi

# Generate beautiful lyrics for your next hit!

## Data cleaning and encoding
"""

# Commented out IPython magic to ensure Python compatibility.
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re

# %matplotlib inline

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable

from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.utils import to_categorical

from torch.utils.data import Dataset, DataLoader

pip install transformers

import time

# Loading positive dataset.
posdf = pd.read_csv('/content/positive.csv')

# Uncomment this line to reduce size of dataset for faster training - positive dataset.
posdf = posdf.head(100)

posdf.head()

#Loading negative dataset
negdf = pd.read_csv('/content/negative.csv')

# Uncomment this line to reduce size of dataset for faster training - negative dataset.
negdf = negdf.head(100)

negdf.head()



def replacenewline(dataframe):
    '''
    Cleans up lyrics by changing \n to 'newline' to help tokenizer and removes unnecessary junk terms.
    param dataframe: datadframe to remove from.
    '''
    dataframe['Lyrics'] = dataframe['Lyrics'].str.replace(r"\n", "newline", regex=True)
    dataframe['Lyrics'] = dataframe['Lyrics'].str.replace(r"urlembedcopy", "", regex=True)
    dataframe['Lyrics'] = dataframe['Lyrics'].str.replace(r"urlcopyembedcopy", "", regex=True)
    dataframe['Lyrics'] = dataframe['Lyrics'].str.replace(r"roamembedshare", "", regex=True)

replacenewline(posdf)
replacenewline(negdf)

# get combined lyrics in one list.
combined_lyrics_pos = posdf['Lyrics'].str.cat(sep = ' newline ')

combined_lyrics_neg = negdf['Lyrics'].str.cat(sep = ' newline ')

def getcleantoks(temp_tokens):
    '''
    Removes empty tokens from list.
    '''
    tokens = []
    for tok in temp_tokens:
        if len(tok) > 0:
            tokens.append(tok)
    return tokens

pos_tokens = getcleantoks(combined_lyrics_pos.split(" "))

neg_tokens = getcleantoks(combined_lyrics_neg.split(" "))

pos_tokens

neg_tokens

#pos_tokens = pos_tokens[0:20000]

#Number of positive tokens
len(pos_tokens)

# Number of negative tokens
len(neg_tokens)

#label_list --- last word of the training_list of tokens,
#it will be used to predict the next possible words once the model is trained on the training_list

def generateTrainingSet(tokens, n):
    '''
    converts the token list into dataset with x values bwing wi to wk-1 and y being wk.
    param tokens: list og tokens
    param n: the size of n gram representation.
    '''
    training_list = []
    label_list = []
    for i in range(len(tokens)):
        if i + n > len(tokens) - 1:
            break
        training_list.append(tokens[i:i+n])
        label_list.append(tokens[i+n])

    #return pd.DataFrame(list(zip(training_list, label_list)), columns = ['Sequence', 'Label'])
    return np.asarray(training_list), np.asarray(label_list)





# Encode positive data.
tokenizer_positive = Tokenizer()
tokenizer_positive.fit_on_texts(pos_tokens)
encoded_pos = tokenizer_positive.texts_to_sequences(pos_tokens)

encoded_pos

tokenizer_positive.word_index["newline"]

tokenizer_positive.index_word[1]

# Encode negative data.
tokenizer_negative = Tokenizer()
tokenizer_negative.fit_on_texts(neg_tokens)
encoded_neg = tokenizer_negative.texts_to_sequences(neg_tokens)

posX, posY = generateTrainingSet(encoded_pos, 8)

negX, negY = generateTrainingSet(encoded_neg, 8)

posY.shape

posX.shape

len(posX)

posX = posX.reshape((len(posX),8))

posX

posY = posY.reshape((len(posY), ))

posY

posY.shape

negX = negX.reshape((len(negX),8))

negY = negY.reshape((len(negY), ))







"""# Creating models"""

class LSTMModel(nn.Module):
    '''
    LSTM model with embedding layer, lstm layer and fully connected layer.
    '''

    def __init__(self, vocab_size):
        super().__init__()
        self.embedding_size = 200
        self.embed = nn.Embedding(vocab_size, self.embedding_size)
        self.lstmlayer = nn.LSTM(input_size = self.embedding_size, hidden_size = 128, num_layers = 2, dropout = 0.1)
        self.ln1 = nn.Linear(128, vocab_size)
        #self.ln2 = nn.Linear(256, vocab_size)

    def forward(self, x):
        layer1 = self.embed(x.t())
        layer2, junk = self.lstmlayer(layer1)
        layer3 = self.ln1(layer2[-1])
        #layer4 = self.ln2(layer3[-1])
        return layer3

class RNNModel(nn.Module):
    '''
    RNN model with embedding layer, lstm layer and fully connected layer.
    '''

    def __init__(self, vocab_size):
        super().__init__()
        self.embedding_size = 200
        self.embed = nn.Embedding(vocab_size, self.embedding_size)
        self.lstmlayer = nn.RNN(input_size = self.embedding_size, hidden_size = 128, num_layers = 2, dropout = 0.1)
        self.ln1 = nn.Linear(128, vocab_size)
        #self.ln2 = nn.Linear(256, vocab_size)

    def forward(self, x):
        layer1 = self.embed(x.t())
        layer2, junk = self.lstmlayer(layer1)
        layer3 = self.ln1(layer2[-1])
        #layer4 = self.ln2(layer3[-1])
        return layer3

class GPTModel(nn.Module):
    '''
    Simplified GPT-like model with an embedding layer, transformer layers, and a fully connected layer.
    '''
    def __init__(self, vocab_size):
        super().__init__()
        self.embedding_size = 200
        self.embed = nn.Embedding(vocab_size, self.embedding_size)
        self.transformer_layer = nn.TransformerEncoderLayer(
            d_model=self.embedding_size, nhead=4, dim_feedforward=256, dropout=0.1
        )
        self.transformer = nn.TransformerEncoder(self.transformer_layer, num_layers=2)
        self.ln1 = nn.Linear(self.embedding_size, vocab_size)

    def forward(self, x):
        layer1 = self.embed(x.t())  # Transpose to match batch-first requirement
        layer2 = self.transformer(layer1)

        # Ensuring we use the last token's representation across the batch
        layer3 = self.ln1(layer2[-1, :, :])  # Use the last timestep (layer2[-1]) across the batch

        return layer3





posX_train = torch.tensor(posX, dtype=torch.long)
posY_train = torch.tensor(posY, dtype=torch.long)

posX_train.shape

negX_train = torch.tensor(negX, dtype=torch.long)
negY_train = torch.tensor(negY, dtype=torch.long)

len(set(pos_tokens))

pos_model = LSTMModel(len(set(pos_tokens)) + 1)
neg_model = LSTMModel(len(set(neg_tokens)) + 1)

pos_gpt_model = GPTModel(len(set(pos_tokens)) + 1)
neg_gpt_model = GPTModel(len(set(neg_tokens)) + 1)





def getdataloader(x, y):
    '''
    Dataloader from torch to feed data one by one.
    '''
    return torch.utils.data.DataLoader(torch.utils.data.TensorDataset(x, y,), batch_size = 128)

pos_train_dload = getdataloader(posX_train, posY_train)

neg_train_dload = getdataloader(negX_train, negY_train)

# Positive and Negative Data Loaders for GPT
pos_train_gpt_dload = getdataloader(posX_train, posY_train)

neg_train_gpt_dload = getdataloader(negX_train, negY_train)

# Optimizers and learning rate
learning_rate = 0.001
loss_fn = nn.CrossEntropyLoss()

optimpos_gpt = torch.optim.Adam(pos_gpt_model.parameters(), lr=learning_rate)
optimneg_gpt = torch.optim.Adam(neg_gpt_model.parameters(), lr=learning_rate)

# Optimizers and learning rate
learning_rate = 0.001
optimpos = torch.optim.Adam(pos_model.parameters(), lr = learning_rate)
optimneg = torch.optim.Adam(neg_model.parameters(), lr = learning_rate)

"""# Train the models"""

def train(model, max_epochs, dataloader, opt):
    '''
    Trains the torch network
    '''
    for epoch in range(max_epochs):
        start = time.time()
        print("epoch ", epoch,"/", max_epochs, end = " ")
        model.train()
        cel = 0
        crossentropyloss = torch.nn.CrossEntropyLoss()
        counter = 9
        temploss = 0.0
        for i, (x, y) in enumerate(dataloader):
            pred_y = model(x)
            L = crossentropyloss(pred_y, y)
            opt.zero_grad()
            counter = 0
            for k in range(5):
                counter += 1
            L.backward()
            counter -= 1
            opt.step()
            counter += 1
            temploss+= L.item()/len(dataloader)
        endtime = time.time() - start
        print('loss={:.5f}    time={:.1f}s'.format(temploss, endtime))

# training positive model with lstm
train(pos_model, 3, pos_train_dload, optimpos)

#training negative model with lstm
train(neg_model, 3, neg_train_dload, optimneg)

posX_train.shape

posY_train.shape



pos_rnn = RNNModel(len(set(pos_tokens)) + 1)

optimrnn = torch.optim.Adam(pos_rnn.parameters(), lr = learning_rate)

# training positive model with rnns
train(pos_rnn, 3, pos_train_dload, optimrnn)

# Train Positive GPT Model
train(pos_gpt_model, 3, pos_train_dload, optimpos_gpt)

# Train Negative GPT Model
train(neg_gpt_model, 3, neg_train_dload, optimneg_gpt)

"""## Generating songs"""

# Generate seeds for positive and negative datasets
def getseeds(dataset, num):
    '''
    Generate random seeds to generate songs with.
    param num - number of seeds to sample
    '''
    seeds = []
    for i in range(num):
        temp = []
        seed = getcleantoks(dataset['Lyrics'].sample().values[0].split(" "))[0:8]
        seeds.append(seed)
    return seeds

pos_seeds = getseeds(posdf, 10)
neg_seeds = getseeds(negdf, 10)

# Function to sample next token based on probabilities
def prob_sample(arr):
    '''
    Sample the predicted output to pick next sequence based on probability distribution and variance.
    '''
    var = 0.8
    probs = np.log(np.asarray(arr).astype('float64')) / var
    return np.argmax(np.random.multinomial(1, np.exp(probs) / np.sum(np.exp(probs)), 1))

# Generates songs using models
def generatesongs(seeds, token, model, maxiter, dims):
    '''
    Generates songs by encoding seeds, passing through model and generating maxiter amount of sequences.
    '''
    songs = []
    counter = 0
    for seed in seeds:
        sentences = []
        start = seed
        next_seed = seed
        counter += 1
        for i in range(maxiter):
            temp = np.zeros(dims)
            for index, gen in enumerate(next_seed):
                if gen == '\n':
                    gen = 'newline'
                temp[0, index] = token.word_index[gen]
            predictions = F.softmax(model(Variable(torch.LongTensor(temp))), dim=1)
            predictions = np.array(predictions.data[0].cpu())
            generated_string = token.index_word[prob_sample(predictions)]
            if generated_string == 'newline':
                generated_string = '\n'
            sentences += [generated_string]
            next_seed = next_seed[1:] + [generated_string]
        songs.append([" ".join(start + sentences)])
    return songs

# generating 10 positive songs
positive_songs1 = generatesongs(pos_seeds, tokenizer_positive, pos_rnn, 300, (1,8))

# example of generated positive lyrics with RNN model
for token in positive_songs1[2]:
    token = re.sub('newline', '\n', token)
    print(token, end = "")

# generating 10 songs with positive and negative LSTM models.
positive_songs = generatesongs(pos_seeds, tokenizer_positive, pos_model, 300, (1,8))

negative_songs = generatesongs(neg_seeds, tokenizer_negative, neg_model, 300, (1,8))

# example of positive song generated by LSTM model.
for token in positive_songs[6]:
    token = re.sub('newline', '\n', token)
    print(token, end = "")

# Example of negative song generated by LSTM model.
for token in negative_songs[9]:
    token = re.sub('newline', '\n', token)
    print(token, end = "")

# Generating songs using GPT model
positive_songs_gpt = generatesongs(pos_seeds, tokenizer_positive, pos_gpt_model, 300, (1, 8))
negative_songs_gpt = generatesongs(neg_seeds, tokenizer_negative, neg_gpt_model, 300, (1, 8))

# Example of positive song generated by GPT model
for token in positive_songs_gpt[2]:
    token = re.sub('newline', '\n', token)
    print(token, end="")

# Example of negative song generated by GPT model
for token in negative_songs_gpt[9]:
    token = re.sub('newline', '\n', token)
    print(token, end="")

"""## Analysis of results

### Dataset
"""

from transformers import GPT2LMHeadModel, GPT2Tokenizer
import spacy

# Load pre-trained model and tokenizer
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
model = GPT2LMHeadModel.from_pretrained("gpt2")

# Add pad token if not available (GPT-2 doesn't have padding token by default)
model.config.pad_token_id = model.config.eos_token_id  # Set pad_token_id to eos_token_id

# Load GPT2 model and tokenizer for GPT-based generation
tokenizer_gpt = GPT2Tokenizer.from_pretrained("gpt2")
model_gpt = GPT2LMHeadModel.from_pretrained("gpt2")
model_gpt.eval()  # Set the model to evaluation mode

def generate_gpt_song(seed_text, max_length=100):
    # Encode the seed text
    input_ids = tokenizer.encode(seed_text, return_tensors="pt")

    # Create attention mask (1 for real tokens, 0 for padding tokens)
    attention_mask = torch.ones(input_ids.shape, device=input_ids.device)  # All tokens are real

    # Generate text with GPT-2
    output = model.generate(input_ids=input_ids,
                            max_length=max_length,
                            attention_mask=attention_mask,
                            pad_token_id=model.config.pad_token_id,  # Use the pad token ID
                            num_return_sequences=1,
                            no_repeat_ngram_size=2,  # Avoid repetition
                            temperature=0.7,  # Control randomness of the generation
                            top_p=0.9,  # Use nucleus sampling
                            top_k=50)  # Use top-k sampling

    # Decode the generated text
    generated_song = tokenizer.decode(output[0], skip_special_tokens=True)
    return generated_song

def metrics(text):
    counter = Counter(text['Lyrics'])
    distinct_words = len(counter)

    len_toks = sum(text['Lyrics'].str.len())/len(text['Lyrics'])

    subset = text
    songs = list(subset[subset['Lyrics'].notnull()]['Lyrics'].str.split(pat = "\n")) #songs

    song_line_len = []
    for song in songs:
        line_lens = []
        for line in song:
            line_lens.append(len(line.split(" ")))
        avg_line_per_song = sum(line_lens)/len(song)
        song_line_len.append(avg_line_per_song)
    avg_line_len = sum(song_line_len)/len(songs)

    song_line_len = []
    for song in songs:
        line_lens = []
        for line in song:
            line_lens.append(len(line)/len(line.split(" ")))
        avg_line_per_song = sum(line_lens)/len(song)
        song_line_len.append(avg_line_per_song)
    avg_word_len = sum(song_line_len)/len(songs)

    return distinct_words, len_toks, avg_line_len, avg_word_len

from collections import Counter

distinct_words_neg, len_toks_neg, avg_line_len_neg, avg_word_len_neg = metrics(negdf)

distinct_words_pos, len_toks_pos, avg_line_len_pos, avg_word_len_pos = metrics(posdf)

# number of distinct words in alyric
# average number of tokens in a lyric
print("distinct_words : ", "average number of tokens : ", "avg_line_length : ", "avg_word_len" )
print(distinct_words_neg, len_toks_neg, avg_line_len_neg, avg_word_len_neg)
print(distinct_words_pos, len_toks_pos, avg_line_len_pos, avg_word_len_pos)

X = ['distinct_words', 'number of tokens', 'average line length', "avg word len"]
Y_neg = [distinct_words_neg, len_toks_neg,  avg_line_len_neg, avg_word_len_neg]
Z_pos = [distinct_words_pos, len_toks_pos, avg_line_len_pos, avg_word_len_pos]

X_axis = np.arange(len(X))

plt.bar(X_axis - 0.2, Y_neg, 0.4, label = 'Negative')
plt.bar(X_axis + 0.2, Z_pos, 0.4, label = 'Positive')

plt.xticks(X_axis, X)
plt.xlabel("Groups")
plt.ylabel("Measured value ")
plt.title("Song Lyrics dataset")
plt.xticks(rotation = 90)
plt.legend()
plt.show()

"""### Song generation and similarity scores"""

# data frame of generated positive and negative songs

gen_pos_df = pd.DataFrame(positive_songs, columns = ['Lyrics'])

gen_neg_df = pd.DataFrame(negative_songs, columns = ['Lyrics'])

def gen_metrics(text):
    counter = Counter(text['Lyrics'])
    distinct_words = len(counter)

    len_toks = sum(text['Lyrics'].str.len())/len(text['Lyrics'])

    subset = text
    songs = list(subset[subset['Lyrics'].notnull()]['Lyrics'].str.split(pat = "\n")) #songs

    song_line_len = []
    for song in songs:
        line_lens = []
        for line in song:
            line_lens.append(len(line.split(" ")))
        avg_line_per_song = sum(line_lens)/len(song)
        song_line_len.append(avg_line_per_song)
    avg_line_len = sum(song_line_len)/len(songs)

    song_line_len = []
    for song in songs:
        line_lens = []
        for line in song:
            line_lens.append(len(line)/len(line.split(" ")))
        avg_line_per_song = sum(line_lens)/len(song)
        song_line_len.append(avg_line_per_song)
    avg_word_len = sum(song_line_len)/len(songs)

    return distinct_words, len_toks, avg_line_len, avg_word_len

def get_random_songs(dataset, num):
    songs = []
    for i in range(num):
        song = dataset['Lyrics'].sample().values[0]
        songs.append(song)
    return songs

import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

distinct_words_neg, len_toks_neg, avg_line_len_neg,avg_word_len_neg  = gen_metrics(gen_neg_df)

distinct_words_pos, len_toks_pos, avg_line_len_pos, avg_word_len_pos = gen_metrics(gen_pos_df)

# number of distinct words in alyric
# average number of tokens in a lyric
print("distinct_words : ", "average number of tokens : ", "avg_word_length : ", " avg_word_length:")
print(distinct_words_neg, len_toks_neg, avg_line_len_neg, avg_word_len_neg)
print(distinct_words_pos, len_toks_pos, avg_line_len_pos, avg_word_len_pos)

X = ['distinct_words', 'number of tokens', 'average word length', "avg_word_length"]
Y_neg = [distinct_words_neg, len_toks_neg,  avg_line_len_neg, avg_word_len_neg]
Z_pos = [distinct_words_pos, len_toks_pos, avg_line_len_pos, avg_word_len_pos]

X_axis = np.arange(len(X))

plt.bar(X_axis - 0.2, Y_neg, 0.4, label = 'Negative')
plt.bar(X_axis + 0.2, Z_pos, 0.4, label = 'Positive')

plt.xticks(X_axis, X)
plt.xlabel("Groups")
plt.ylabel("Measured value")
plt.title("Generated song dataset")
plt.xticks(rotation = 90)
plt.legend()
plt.show()

## measuring SPacy similarity b/n ten random songs (from each positive and negative dataset)
## vs generated songs (pos and neg)

def get_random_songs(dataset, num):
    songs = []
    for i in range(num):

        # song = dataset['Lyrics'].sample(n=num)
        song = dataset['Lyrics'].sample().values[0]
        songs.append(song)

    return songs


# list of string of all songs
pos_songs_df = get_random_songs(posdf, 10)
neg_songs_df = get_random_songs(negdf, 10)

# instruction : sudo pip3 install spacy
# instruction : sudo python3 -m spacy download en


import spacy


nlp = spacy.load('en_core_web_sm')

# positive songs cosine similarity



pos_sim = 0
pos_songs_dataset = [x for [x] in positive_songs]

for ds, gen in zip(pos_songs_dataset, pos_songs_df):


    pos_sim = pos_sim + nlp(ds).similarity(nlp(gen))



avg_pos_cos_sim = pos_sim / 10
print("AVERAGE POSITIVE COSINE SIMILARITY : ",avg_pos_cos_sim)

# NEgative songs cosine similarity



neg_sim = 0
# flatten
neg_songs_dataset = [x for [x] in negative_songs]

for ds, gen in zip(neg_songs_dataset, neg_songs_df):


    neg_sim = neg_sim + nlp(ds).similarity(nlp(gen))



avg_neg_cos_sim = neg_sim / 10
print("AVERAGE NEGATIVE COSINE SIMILARITY : ",avg_neg_cos_sim)

"""## GRAPH COSINE SIMILARITY

"""

import matplotlib.pyplot as plt
fig = plt.figure()
ax = fig.add_axes([0,0,1,1])
dataset = ['NEGATIVE', 'POSITIVE']
sim_val = [avg_neg_cos_sim, avg_pos_cos_sim]
plt.xlabel("emotions of songs")
plt.ylabel("average cosine similarity")
plt.title("Cosine similarity of generated songs Vs songs in the dataset. FOR: positve and  negative datasets")
plt.xticks(rotation = 90)
ax.bar(dataset,sim_val)
plt.show()

# DataFrame for positive and negative generated songs
gen_pos_df = pd.DataFrame(positive_songs, columns = ['Lyrics'])
gen_neg_df = pd.DataFrame(negative_songs, columns = ['Lyrics'])

# Generate songs using GPT-2
gpt_pos_songs = [generate_gpt_song("positive seed") for _ in range(10)]
gpt_neg_songs = [generate_gpt_song("negative seed") for _ in range(10)]

# Add GPT songs to DataFrames
gpt_pos_df = pd.DataFrame(gpt_pos_songs, columns=['Lyrics'])
gpt_neg_df = pd.DataFrame(gpt_neg_songs, columns=['Lyrics'])

# Metrics for original and GPT generated songs
distinct_words_neg, len_toks_neg, avg_line_len_neg, avg_word_len_neg = metrics(negdf)
distinct_words_pos, len_toks_pos, avg_line_len_pos, avg_word_len_pos = metrics(posdf)

distinct_words_neg_gpt, len_toks_neg_gpt, avg_line_len_neg_gpt, avg_word_len_neg_gpt = gen_metrics(gpt_neg_df)
distinct_words_pos_gpt, len_toks_pos_gpt, avg_line_len_pos_gpt, avg_word_len_pos_gpt = gen_metrics(gpt_pos_df)

# Print metrics for original and GPT-generated songs
print("Metrics for Dataset Songs:")
print(distinct_words_neg, len_toks_neg, avg_line_len_neg, avg_word_len_neg)
print(distinct_words_pos, len_toks_pos, avg_line_len_pos, avg_word_len_pos)

print("Metrics for GPT Generated Songs:")
print(distinct_words_neg_gpt, len_toks_neg_gpt, avg_line_len_neg_gpt, avg_word_len_neg_gpt)
print(distinct_words_pos_gpt, len_toks_pos_gpt, avg_line_len_pos_gpt, avg_word_len_pos_gpt)

# Bar plot comparing the metrics for dataset and GPT-generated songs
X = ['distinct_words', 'number of tokens', 'average line length', 'avg word len']
Y_neg = [distinct_words_neg, len_toks_neg, avg_line_len_neg, avg_word_len_neg]
Z_neg = [distinct_words_neg_gpt, len_toks_neg_gpt, avg_line_len_neg_gpt, avg_word_len_neg_gpt]
Y_pos = [distinct_words_pos, len_toks_pos, avg_line_len_pos, avg_word_len_pos]
Z_pos = [distinct_words_pos_gpt, len_toks_pos_gpt, avg_line_len_pos_gpt, avg_word_len_pos_gpt]

X_axis = np.arange(len(X))

plt.bar(X_axis - 0.2, Y_neg, 0.4, label = 'Negative (Original)')
plt.bar(X_axis + 0.2, Z_neg, 0.4, label = 'Negative (GPT)')
plt.bar(X_axis - 0.2, Y_pos, 0.4, label = 'Positive (Original)', bottom=Y_neg)
plt.bar(X_axis + 0.2, Z_pos, 0.4, label = 'Positive (GPT)', bottom=Z_neg)

plt.xticks(X_axis, X)
plt.xlabel("Groups")
plt.ylabel("Measured value")
plt.title("Song Lyrics Dataset vs GPT Generated Songs")
plt.xticks(rotation=90)
plt.legend()
plt.show()

# Load the SpaCy model
nlp = spacy.load('en_core_web_sm')

# Flatten the positive_songs list if it's a list of lists
positive_songs_flat = [item for sublist in positive_songs for item in sublist]

# Ensure you're using a subset of 10 songs for cosine similarity comparison
pos_songs_subset = positive_songs_flat[:10]  # Adjust based on your data

# Create a DataFrame from the generated positive songs if not already done
gen_pos_df = pd.DataFrame(gpt_pos_songs, columns=['Lyrics'])

# Ensure we are working with a DataFrame
print(gen_pos_df.head())  # Check if the DataFrame is structured correctly

# Initialize a variable for the total cosine similarity
pos_sim = 0

# Ensure we are accessing the 'Lyrics' column correctly from the DataFrame
for ds, gen in zip(pos_songs_subset, gen_pos_df['Lyrics'].values[:10]):  # Using only 10 samples
    pos_sim += nlp(ds).similarity(nlp(gen))

# Calculate the average cosine similarity
avg_pos_cos_sim = pos_sim / 10

# Print the result
print("AVERAGE POSITIVE COSINE SIMILARITY : ", avg_pos_cos_sim)

# Cosine similarity for GPT-generated positive songs
gpt_pos_sim = 0
for ds, gen in zip(pos_songs_dataset, gpt_pos_df['Lyrics']):
    gpt_pos_sim += nlp(ds).similarity(nlp(gen))

avg_gpt_pos_cos_sim = gpt_pos_sim / 10
print("AVERAGE GPT POSITIVE COSINE SIMILARITY : ", avg_gpt_pos_cos_sim)

# Cosine similarity for GPT-generated negative songs
gpt_neg_sim = 0
for ds, gen in zip(neg_songs_dataset, gpt_neg_df['Lyrics']):
    gpt_neg_sim += nlp(ds).similarity(nlp(gen))

avg_gpt_neg_cos_sim = gpt_neg_sim / 10
print("AVERAGE GPT NEGATIVE COSINE SIMILARITY : ", avg_gpt_neg_cos_sim)

# Plot the cosine similarity results for real and GPT-generated songs
fig = plt.figure()
ax = fig.add_axes([0, 0, 1, 1])
dataset = ['Negative Dataset', 'Positive Dataset', 'Negative GPT', 'Positive GPT']
sim_val = [avg_neg_cos_sim, avg_pos_cos_sim, avg_gpt_neg_cos_sim, avg_gpt_pos_cos_sim]

plt.xlabel("Emotions of Songs")
plt.ylabel("Average Cosine Similarity")
plt.title("Cosine Similarity of Real vs GPT-Generated Songs")
plt.xticks(rotation=90)
ax.bar(dataset, sim_val)
plt.show()