# -*- coding: utf-8 -*-
"""POP-Melody-Transformer.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Rn6_FtKe8GSG17BcWSyF9w0vs9VaSb2_

# POP Melody Transformer (ver. 1.0)

***

Powered by tegridy-tools: https://github.com/asigalov61/tegridy-tools

***

WARNING: This complete implementation is a functioning model of the Artificial Intelligence. Please excercise great humility, care, and respect. https://www.nscai.gov/

***

#### Project Los Angeles

#### Tegridy Code 2023

***

# (SETUP ENVIRONMENT)
"""

#@title Install all dependencies (run only once per session)

!git clone --depth 1 https://github.com/asigalov61/POP-Melody-Transformer
!pip install einops
!pip install torch-summary
!pip install tqdm
!pip install matplotlib
!pip install gdown
!pip install huggingface_hub

# Commented out IPython magic to ensure Python compatibility.
#@title Import all needed modules

print('=' * 70)
print('Loading needed modules. Please wait...')

import os
import pickle

import secrets
import tqdm
import math

from joblib import Parallel, delayed, parallel_config

import torch

torch.set_float32_matmul_precision('high')
torch.backends.cuda.matmul.allow_tf32 = True # allow tf32 on matmul
torch.backends.cudnn.allow_tf32 = True # allow tf32 on cudnn

import matplotlib.pyplot as plt

from torchsummary import summary
from sklearn import metrics

from huggingface_hub import hf_hub_download

print('=' * 70)
print('Loading TMIDIX module...')

# %cd /content/POP-Melody-Transformer

import TMIDIX

print('=' * 70)
print('Loading X Transformer module...')

from x_transformer_1_23_2 import *
import random

# %cd /content/

print('=' * 70)
print('Creating I/O dirs...')

if not os.path.exists('/content/Dataset'):
    os.makedirs('/content/Dataset')

if not os.path.exists('/content/Output'):
    os.makedirs('/content/Output')

print('=' * 70)
print('Done!')
print('=' * 70)
print('PyTorch version:', torch.__version__)
print('=' * 70)
print('Enjoy! :)')
print('=' * 70)

"""# (LOAD PRE-TRAINED MODEL)"""

#@title Load POP Melody Transformer Small Model

#@markdown Very fast model, 8 layers, 2100 MIDIs training corpus

full_path_to_model_checkpoint = "/content/POP-Melody-Transformer/Model/Small/POP_Melody_Transformer_Small_Trained_Model_5395_steps_0.3491_loss_0.8924_acc.pth" #@param {type:"string"}

#@markdown Model precision option

model_precision = "bfloat16" # @param ["bfloat16", "float16"]

#@markdown bfloat16 == Half precision/faster speed (if supported, otherwise the model will default to float16)

#@markdown float16 == Full precision/fast speed

print('=' * 70)
print('Loading Giant Music Transformer Large Pre-Trained Model...')
print('Please wait...')
print('=' * 70)

if os.path.isfile(full_path_to_model_checkpoint):
  print('Model already exists...')

else:
  hf_hub_download(repo_id='asigalov61/POP-Melody-Transformer',
                  filename='POP_Melody_Transformer_Small_Trained_Model_5395_steps_0.3491_loss_0.8924_acc.pth',
                  local_dir='/content/POP-Melody-Transformer/Model/Small',
                  local_dir_use_symlinks=False)

print('=' * 70)
print('Instantiating model...')

torch.backends.cuda.matmul.allow_tf32 = True # allow tf32 on matmul
torch.backends.cudnn.allow_tf32 = True # allow tf32 on cudnn
device_type = 'cuda'

if model_precision == 'bfloat16' and torch.cuda.is_bf16_supported():
  dtype = 'bfloat16'
else:
  dtype = 'float16'

if model_precision == 'float16':
  dtype = 'float16'

ptdtype = {'float32': torch.float32, 'bfloat16': torch.bfloat16, 'float16': torch.float16}[dtype]
ctx = torch.amp.autocast(device_type=device_type, dtype=ptdtype)

SEQ_LEN = 8192

# instantiate the model

model = TransformerWrapper(
    num_tokens = 643,
    max_seq_len = SEQ_LEN,
    attn_layers = Decoder(dim = 1024, depth = 8, heads = 8, attn_flash = True)
)

model = AutoregressiveWrapper(model, ignore_index=642)

model.cuda()
print('=' * 70)

print('Loading model checkpoint...')

model.load_state_dict(torch.load(full_path_to_model_checkpoint))
print('=' * 70)

model.eval()

print('Done!')
print('=' * 70)

print('Model will use', dtype, 'precision...')
print('=' * 70)

# Model stats
print('Model summary...')
summary(model)
print('Done!')
print('=' * 70)

"""# (DOWNLOAD SAMPLE MIDI DATASET)"""

# Commented out IPython magic to ensure Python compatibility.
# @title Download and unzip POP1k7 Piano MIDI dataset

#@markdown Source GitHub repo https://github.com/YatingMusic/compound-word-transformer

# %cd /content/Dataset
!gdown '1qw_tVUntblIg4lW16vbpjLXVndkVtgDe'
!unzip dataset.zip
!rm dataset.zip
# %cd /content/

"""# (LOAD MIDI PROCESSOR)"""

#@title TMIDIX MIDI Processor

print('=' * 70)
print('Loading TMIDIX MIDI Processor...')
print('=' * 70)

def group_single_elements(lst):
  new_lst = []
  temp = []
  for sublist in lst:
      if len(sublist) == 1:
          temp.extend(sublist)
      else:
          if temp:
              new_lst.append(temp)
              temp = []
          new_lst.append(sublist)
  if temp:
      new_lst.append(temp)
  return new_lst

def TMIDIX_MIDI_Processor(midi_file):

    melody_chords = []

    try:

        fn = os.path.basename(midi_file)
        fn1 = fn.split('.mid')[0]

        # Filtering out GIANT4 MIDIs
        file_size = os.path.getsize(midi_file)

        if file_size <= 1000000:

          #=======================================================
          # START PROCESSING

          # Convering MIDI to ms score with MIDI.py module
          score = TMIDIX.midi2single_track_ms_score(open(midi_file, 'rb').read(), recalculate_channels=False)

          # INSTRUMENTS CONVERSION CYCLE
          events_matrix = []
          itrack = 1
          patches = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

          while itrack < len(score):
              for event in score[itrack]:
                  if event[0] == 'note' or event[0] == 'patch_change':
                      events_matrix.append(event)
              itrack += 1

          events_matrix.sort(key=lambda x: x[1])

          events_matrix1 = []

          for event in events_matrix:
                  if event[0] == 'patch_change':
                        patches[event[2]] = event[3]

                  if event[0] == 'note':
                        event.extend([patches[event[3]]])

                        if events_matrix1:
                            if (event[1] == events_matrix1[-1][1]):
                                if ([event[3], event[4]] != events_matrix1[-1][3:5]):
                                    events_matrix1.append(event)
                            else:
                                events_matrix1.append(event)

                        else:
                            events_matrix1.append(event)

        if len(events_matrix1) > 0:
            if min([e[1] for e in events_matrix1]) >= 0 and min([e[2] for e in events_matrix1]) >= 0:

                #=======================================================
                # PRE-PROCESSING

                # checking number of instruments in a composition
                instruments_list = list(set([y[3] for y in events_matrix1]))

                if len(events_matrix1) > 0:

                    #===================================
                    # ORIGINAL COMPOSITION
                    #===================================

                    # Adjusting timings

                    for e in events_matrix1:
                      e[1] = int(e[1] / 16)
                      e[2] = int(e[2] / 16)

                    # Sorting by patch, pitch, then by start-time

                    events_matrix1.sort(key=lambda x: x[6])
                    events_matrix1.sort(key=lambda x: x[4], reverse=True)
                    events_matrix1.sort(key=lambda x: x[1])

                    #=======================================================
                    # FINAL PROCESSING

                    #=======================================================
                    # MAIN PROCESSING CYCLE
                    #=======================================================

                    pe = events_matrix1[0]

                    notes = []

                    for e in events_matrix1:

                      time = max(0, min(255, (e[1] - pe[1])))
                      dur = max(0, min(255, e[2]))
                      cha = max(0, min(15, e[3]))
                      ptc = max(1, min(127, e[4]))
                      vel = max(1, min(127, e[5]))

                      if cha != 9:
                        notes.append([time, dur, 0, ptc, vel])

                      pe = e

                    return [notes, fn1]

    except:
      return None

print('Done!')
print('=' * 70)

"""# (FILES LIST)"""

#@title Save file list
###########

print('=' * 70)
print('Loading MIDI files...')
print('This may take a while on a large dataset in particular.')

dataset_addr = "/content/Dataset/dataset/midi_transcribed"

# os.chdir(dataset_addr)
filez = list()
for (dirpath, dirnames, filenames) in os.walk(dataset_addr):
    filez += [os.path.join(dirpath, file) for file in filenames]
print('=' * 70)

if not filez:
    print('Could not find any MIDI files. Please check Dataset dir...')
    print('=' * 70)

else:
  print('Randomizing file list...')
  random.shuffle(filez)
  print('Done!')
  print('=' * 70)
  print('Total files:', len(filez))
  print('=' * 70)

"""# (PROCESS)"""

#@title Process MIDIs with TMIDIX MIDI processor

print('=' * 70)
print('TMIDIX MIDI Processor')
print('=' * 70)
print('Starting up...')
print('=' * 70)

###########

melody_chords_f = []

print('Processing MIDI files. Please wait...')
print('=' * 70)

for i in tqdm.tqdm(range(0, len(filez), 16)):

  with parallel_config(backend='threading', n_jobs=4, verbose = 0):

    output = Parallel()(delayed(TMIDIX_MIDI_Processor)(f) for f in filez[i:i+16])

    for o in output:

        if o is not None:
            melody_chords_f.append(o)

print('Done!')
print('=' * 70)

"""# (SAVE/LOAD PROCESSED MIDIs)"""

#@title Save processed MIDIs
TMIDIX.Tegridy_Any_Pickle_File_Writer(melody_chords_f, '/content/Processed_MIDIs')

# @title Load processed MIDIs
melody_chords_f = TMIDIX.Tegridy_Any_Pickle_File_Reader('/content/Processed_MIDIs')
print('Done!')

"""# (EXTRACT MELODY)"""

#@title Melody arrangement/extraction

#@markdown You can stop the extraction at any time to render partial results

#@markdown Extraction settings

melody_MIDI_patch_number = 40 # @param {type:"slider", min:0, max:127, step:1}
accompaniment_MIDI_patch_number = 0 # @param {type:"slider", min:0, max:127, step:1}
add_base_line = True # @param {type:"boolean"}
base_line_threshold_pitch_number = 50 # @param {type:"slider", min:10, max:60, step:1}
base_line_MIDI_patch_number = 35 # @param {type:"slider", min:0, max:127, step:1}

#@markdown Generation settings

number_of_prime_notes = 4 # @param {type:"slider", min:1, max:256, step:1}
number_of_memory_tokens = 4096 # @param {type:"slider", min:3, max:8190, step:3}
number_of_samples_per_inpainted_note = 2 #@param {type:"slider", min:1, max:16, step:1}
temperature = 1 # @param {type:"slider", min:0.1, max:1, step:0.05}

#@markdown Other Settings

verbose = False # @param {type:"boolean"}

print('=' * 70)
print('POP Melody Transformer Model Generator')

for j in range(len(melody_chords_f)):

  try:

    melody_chords = melody_chords_f[j][0]
    fname = melody_chords_f[j][1]

    print('=' * 70)
    print('Processing MIDI file', j, 'out of', len(melody_chords_f))
    print('MIDI file name:', fname+'.mid')
    print('=' * 70)

    out2 = []
    out3 = []

    abs_time = 0

    for m in melody_chords[:number_of_prime_notes]:
        out2.extend([m[0], m[1]+256, m[3]+512, 640+0])
        out3.extend([m[0], m[1]+256, m[3]+512, 640+0, m[4]+642])
        abs_time += m[0]

    torch.cuda.empty_cache()

    pt = abs_time
    pd = m[1]

    for i in tqdm.tqdm(range(number_of_prime_notes, len(melody_chords))):

        m = melody_chords[i]

        out2.extend([m[0], m[1]+256, m[3]+512])
        out3.extend([m[0], m[1]+256, m[3]+512])
        abs_time += m[0]

        if abs_time >= pt+pd:

            samples = []

            for j in range(number_of_samples_per_inpainted_note):

                inp = torch.LongTensor(out2[-number_of_memory_tokens:]).cuda()

                with ctx:
                    out1 = model.generate(inp,
                                          1,
                                          temperature=temperature,
                                          return_prime=True,
                                          verbose=False)

                    with torch.no_grad():
                      test_loss, test_acc = model(out1)

                samples.append([[out1.tolist()[0][-1]], test_acc.tolist()])

            accs = [y[1] for y in samples]
            max_acc = max(accs)
            max_acc_sample = samples[accs.index(max_acc)][0]


            out2.extend(max_acc_sample)
            out3.extend(max_acc_sample + [m[4]+642])

            if max_acc_sample == [641]:
                pt = abs_time
                pd = m[1]

        else:
            out2.extend([640])
            out3.extend([640, m[4]+642])

    if verbose:
      print('Done!')
      print('=' * 70)

    torch.cuda.empty_cache()

    #==================================================

    train_data1 = out3 # y[0]

    #train_data1 = max(melody_chords_f, key = len)

    if verbose:
      print('Sample INTs', train_data1[:15])

    out = train_data1

    patches = [0] * 16

    patches[0] = accompaniment_MIDI_patch_number
    patches[2] = base_line_MIDI_patch_number
    patches[3] = melody_MIDI_patch_number

    #==================================================

    if len(out) != 0:

        song = out
        song_f = []

        time = 0
        dur = 0
        vel = 90
        pitch = 0
        channel = 0

        for ss in song:

            if 0 <= ss < 256:

                time += (ss * 16)

            if 256 <= ss < 512:

                dur = (ss-256) * 16

            if 512 <= ss < 640:

                pitch = ss-512

            if 640 <= ss < 642:

                channel = ss-640

                if channel == 1:
                    channel = 3

            if 642 <= ss < 770:
                vel = ss-642

                song_f.append(['note', time, dur, channel, pitch, vel ])

        #==================================================

        song_f_chords = []

        cho = []
        pe = song_f[0]
        for s in song_f:
            if s[1]-pe[1] == 0:
                cho.append(s)

            else:
                if len(cho) > 0:
                    song_f_chords.append(cho)
                cho = []
                cho.append(s)

            pe = s

        if len(cho) > 0:
            song_f_chords.append(cho)


        song_f_base = []

        for s in song_f_chords:
            if s[-1][4] <= base_line_threshold_pitch_number:
                s[-1][3] = 2

            for ss in s:
                song_f_base.append(ss)

        #==================================================

        if add_base_line:
          song_final = song_f_base
        else:
          song_final = song_f

        #==================================================

    detailed_stats = TMIDIX.Tegridy_ms_SONG_to_MIDI_Converter(song_final,
                                                              output_signature = 'POP Melody Transformer',
                                                              output_file_name = '/content/Output/'+fname,
                                                              track_name='Project Los Angeles',
                                                              list_of_MIDI_patches=patches,
                                                              verbose=verbose)

  except KeyboardInterrupt:
    print('Stopping extraction...')
    break

  except Exception as e:
    print('Error', e)
    continue

print('=' * 70)
print('Done!')
print('=' * 70)

"""# Congrats! You did it! :)"""