import json
from pprint import pprint
import re
from collections import Counter
import heapq
import math

# Apertura del file data.json
with open("data_clean.json") as json_data:
    data = json.load(json_data)
    json_data.close()

# Definiamo i nomi dei tipi di smell
smells = ['max-statements','max-depth','complexity','max-len','max-params','max-nested-callbacks','complex-switch-case','complex-chaining']
smells_boolean = ['no-reassign','no-extra-bind','cond-assign','this-assign']
smells_values = {}
smells_seuil = {}
smells_count = {}

# Per ogni tipo di smell, contiamo quante volte appare in media per commit
for smell in smells:
    smells_count[smell] = 0
for smell in smells_boolean:
    smells_count[smell] = 0
Nb_Commit = 0
for commit in data:
    Nb_Commit += 1
    for change in commit['changes']:
        smell = change['smells']
        for s in smell.keys():
            if(s in smells_count):
                smells_count[s] = smells_count[s] + len(change['smells'][s])
for type_smell in smells_count:
    print('Numero di smells del tipo', type_smell, ':', smells_count[type_smell])

# Per ogni tipo di smell, salviamo i valori (pesi) per ciascun file in data.json
for smell in smells:
    smells_values[smell] = []

# Per ogni tipo di smell (eccetto quelli booleani)
for type_smell in smells:
    # Per ogni commit
    for commit in data:
        # Per ogni cambiamento effettuato
        for change in commit['changes']:
            smell = change['smells']
            # Se il tipo di smell è presente nel file cambiato
            if(type_smell in smell.keys()):
                # Aggiungiamo il peso massimo, se ci sono più di un tipo di smell dello stesso tipo (il più grande caratterizza il file)
                smells_values[type_smell].append(max([e[0] for e in smell[type_smell]]))

# Per ogni tipo di smell, definiamo una soglia basata sui valori ottenuti precedentemente. Superato questo limite, lo smell sarà considerato reale. Al di sotto, non verrà preso in considerazione.
# La soglia scelta qui è del 10% (quindi i 10% smell più "grandi" sono considerati reali)
for smell in smells_values.keys():
    #if(math.floor(0.25*len(smells_values[smell])) == 0):
    if(math.floor(0.1*len(smells_values[smell])) == 0):
        smells_seuil[smell] = max(smells_values[smell]) if len(smells_values[smell]) > 0 else 0
    else:
        #smells_seuil[smell] = round((min(heapq.nlargest(round(0.25*len(smells_values[smell])),smells_values[smell]))+10*max(smells_values[smell]))/11)
        smells_seuil[smell] = min(heapq.nlargest(math.floor(0.1*len(smells_values[smell])),smells_values[smell]))
for smell in smells_boolean:
    smells_seuil[smell] = 1

# Per ogni tipo di smell
for type_smell in smells:
    # Per ogni commit
    for i in range(len(data)):
        # Per ogni cambiamento
        for j in range(len(data[i]['changes'])):
            # Se il tipo di smell è nel file modificato
            if(type_smell in data[i]['changes'][j]['smells'].keys()): 
                # Se uno degli smells ha un peso superiore alla soglia stabilita precedentemente
                if(max([e[0] for e in data[i]['changes'][j]['smells'][type_smell]]) >= smells_seuil[type_smell]):
                    # Manteniamo solo gli smells con il peso massimo (gli smells più caratteristici)
                    data[i]['changes'][j]['smells'][type_smell] = [e for e in data[i]['changes'][j]['smells'][type_smell] if e[0] == max([e[0] for e in data[i]['changes'][j]['smells'][type_smell]])]
                else:
                    # Altrimenti, eliminiamo questo tipo di smell dai dati del file modificato
                    del data[i]['changes'][j]['smells'][type_smell]

# Per ogni commit
for i in range(len(data)):
    # Per ogni cambiamento (quindi per ogni file modificato)
    for j in range(len(data[i]['changes'])):
        # Se questo cambiamento include degli smells
        if(len(data[i]['changes'][j]['smells']) > 0): 
            # Allora marchiamo questo file come smelly
            data[i]['changes'][j]['smelly'] = 1
        else:
            # Altrimenti il file è marcato come non smelly
            data[i]['changes'][j]['smelly'] = 0

#print(smells_seuil)
#print(smells_values)
#print(data[10])

# Salviamo i nuovi dati, che stabiliscono se i file sono smelly o meno
with open('set_smelly.json','w') as outfile:
    json.dump(data,outfile)

with open('seuil_poids_smells.json','w') as outfile2:
    json.dump(smells_seuil,outfile2)

with open('smells_values.json', 'w') as outfile3:
    json.dump(smells_values, outfile3)
