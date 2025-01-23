import json
from difflib import SequenceMatcher
from datetime import datetime
from statistics import median
import csv
import sys

# Degré de similitude entre 2 smells
Degre_similitude = float(sys.argv[1])

# Ouverture du fichier data.json
with open("data.json") as json_data:
    data = json.load(json_data)
    json_data.close()

# Ouverture du fichier historique_fichiers.json
with open("historique_fichiers2.json") as json_data2:
    historique = json.load(json_data2)
    json_data2.close()

# Ouverture du fichier contenant le seuil des poids des smells de chaque type
with open("seuil_poids_smells.json") as json_data3:
    seuil = json.load(json_data3)
    json_data3.close()

# On met en lien chaque fichier renommé, à la période où le fichier a été renommé
filenames_to_link = []
for commit in data:
    if(len(commit['changes']) != 0):
        for change in commit['changes']:
            if('old' in change.keys()):
                # On met dans une liste chaque couple de fichiers identiques mais de noms différents
                filenames_to_link.append([change["f"],change["old"]])

# On met en lien les noms pour un même fichier
for i in range(len(filenames_to_link)-1):
    for j in range(i,len(filenames_to_link)-1):
        if filenames_to_link[i][0]==filenames_to_link[j][1]:
            for k in filenames_to_link[i][1:]:
                filenames_to_link[j].append(k)
            filenames_to_link[i] = [0,0]

# On élimine les valeurs "vides"
filenames_to_link_without_duplicate = []
for element in filenames_to_link:
    if(element != [0,0]):
        filenames_to_link_without_duplicate.append(element)
            
# Filenames_to_link_without_duplicate réunit les noms d'un même fichier, et cela pour chaque fichier
#print('Voici les noms des fichiers liés : ',filenames_to_link_without_duplicate)
print('Les mêmes noms pour un fichier donné ont été récupérés, et cela pour tous les fichiers modifiés')

# On vérifie bien que chaque fichier apparaît bien dans les commits de son historique (avec le nom actuel ou sous d'autres noms)
for file in historique.keys():
    hist = historique[file]
    for commit in hist:
        for element in data:
            if(element["commit"]==commit):
                files_changed = [e["f"] for e in element["changes"]]
                if(file not in files_changed):
                    find = False
                    for f in filenames_to_link_without_duplicate:
                        if(file == f[0]):
                            for f2 in f[1:]:
                                if f2 in files_changed:
                                    find = True
                    if(find == False):
                        print('Erreur avec le fichier : ',file)
                        print("Commit de l'historique : ",commit)
                        print()

# On regarde si chacun des fichiers est supprimé dans un des commits de data
for file in historique.keys():
    for commit in data:
        if(len(commit["changes"])!=0):
            for change in commit["changes"]:
                if(change["f"] == file and change["type"]=="deleted"):
                    historique[file].append(commit["commit"])
print("Les informations sur les fichiers supprimés dans les commits ont été récupérées")
#print(file_deleted)

# On récupère les smells pour chaque fichier, à chaque fois qu'il est modifié
smell_by_file = {}
nb_iter = 0
for file in historique.keys():
    smell_by_file[file] = {}
    hist = historique[file]
    for commit in hist:
        fichier = file
        nb_iter+=1
        for element in data:
            if(element["commit"]==commit):
                files_changed = [e["f"] for e in element["changes"]]
                if(file not in files_changed):
                    for f in filenames_to_link_without_duplicate:
                        if(file == f[0]):
                            for f2 in f[1:]:
                                if f2 in files_changed:
                                    fichier = f2
                for change in element["changes"]:
                    if(change["f"]==fichier):
                        if(len(change["smells"])!=0):
                            smell_by_file[file][commit] = change["smells"]
                        else:
                            smell_by_file[file][commit] = {}

#print(smell_by_file)
print('Smells récupérés')

# On stocke les différents types de smell
type_smell = ['max-statements','max-depth','complexity','max-len','max-params','max-nested-callbacks','complex-switch-case','this-assign','complex-chaining','no-reassign','no-extra-bind','cond-assign']
#type_smell = ['this-assign']

# Pour stocker le nombre de smells corrigés tout au long du projet
nb_smell_corrige = {}
# Pour stocker le nombre de smells créés tout au long du projet
nb_smell_cree = {}
# Pour stocker le nombre de smells créés à la création du projet
nb_smell_cree_debut = {}
# Pour stocker le temps de survie des smells
smell_time = {}
# Pour stocker la date d'un commit
date = None

# On initialise nos variables
for ts in type_smell:
    nb_smell_corrige[ts] = 0
    nb_smell_cree[ts] = 0
    nb_smell_cree_debut[ts] = 0
    smell_time[ts] = {}
    for f in smell_by_file.keys():
        smell_time[ts][f] = {}

# Structure pour la survie des smells
survie_smells = {}
for ts in type_smell:
    survie_smells[ts] = [["Time","Event"]]
#survie_smells.append(["Time","Event","Type_Smell"])
#survie_smells.append(["Time","Event"])

# On stocke la date du dernier commit
date_dernier_commit = datetime.strptime(data[-1]["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
date_premier_commit = datetime.strptime(data[0]["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
date_ancien_commit = 0
iter = 0

fichier_traite = []

# Pour chaque fichier
for f in smell_by_file.keys():
    print('Fichier traité : ',f)
    # Si le fichier est modifié dans des commits
    if(len(smell_by_file[f])!=0 and f not in fichier_traite and f.endswith('.min.js')==False):
        fichier_traite.append(f)
        # Pour savoir si on est à la création du fichier
        premier_commit = True
        # Pour stocker les smells du fichier au commit précédent
        smell_precedent = {}
        # Pour stocker les smell du fichier au commit actuellement traité
        smell_actuel = {}
        # On initialise à 0 (liste vide) nos variables (aucun smell enregistré)
        for ts in type_smell:
            smell_precedent[ts] = []
            smell_actuel[ts] = []
        # Pour chaque commit (qui modifie le fichier)
        commits = [key for key in smell_by_file[f].keys()]
        for c in commits:
            iter+=1
            print('     Commit traité : ',c)
            print('     Itération',iter,'sur',nb_iter)
            for el in data : 
                if(c == el["commit"]):
                    date = datetime.strptime(el["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
            # Pour chaque type de smell
            for typeSmell in type_smell:
                # Si le type de smell apparaît dans le commit, on stocke les lignes liés à ce smell
                if(typeSmell in smell_by_file[f][c].keys()):
                    ma_liste = [[smell[1][0],smell[2]] for smell in smell_by_file[f][c][typeSmell] if smell[0] >= seuil[typeSmell]]
                    mes_tuples = [tuple(t) for t in ma_liste]
                    mon_set = set(mes_tuples)
                    ma_nouvelle_liste = [list(t) for t in mon_set]
                    smell_actuel[typeSmell] = [e[1] for e in ma_nouvelle_liste]
                    #print("             Smells :",smell_actuel[typeSmell])
                # Sinon, on ne stocke rien (liste vide)
                else : 
                    smell_actuel[typeSmell] = []
                # Si on est au premier commit du fichier (création du fichier)
                if(premier_commit == True):
                    # On compte combien de smell du type actuel apparaît
                    nb_smell_cree_debut[typeSmell]+=len(smell_actuel[typeSmell])

                # Si nous avons des smells du type recherché au commit précédent, et qu'il n'y en a pas au commit actuel
                if(len(smell_actuel[typeSmell])==0 and len(smell_precedent[typeSmell])!=0):
                    # On incrémente le nombre de smells corrigés du type traité
                    nb_smell_corrige[typeSmell]+=len(smell_precedent[typeSmell])
                    for s in smell_time[typeSmell][f].keys():
                        while('blank' in smell_time[typeSmell][f][s]):
                            smell_time[typeSmell][f][s].insert(smell_time[typeSmell][f][s].index('blank'),date)
                            smell_time[typeSmell][f][s].remove('blank')

                # Si nous avons des smells du type recherché au commit actuel, et qu'il n'y en avait pas précédemment (au commit précédent)
                if(len(smell_actuel[typeSmell])!=0 and len(smell_precedent[typeSmell])==0):
                    # On incrémente le nombre de smells créés du type traité
                    nb_smell_cree[typeSmell]+=len(smell_actuel[typeSmell])
                    for s in smell_actuel[typeSmell]:
                        best_match_value = max([SequenceMatcher(None,s,s1).ratio() for s1 in smell_time[typeSmell][f].keys()]) if(len(smell_time[typeSmell][f].keys()))!=0 else 0
                        if(best_match_value > Degre_similitude) :
                            found = False
                            candidats_similaires = [e for e in smell_time[typeSmell][f].keys() if SequenceMatcher(None,s,e).ratio() > Degre_similitude]
                            candidat_similaire_meilleur = [e for e in smell_time[typeSmell][f].keys() if SequenceMatcher(None,s,e).ratio() == best_match_value][0]
                            while found == False : 
                                measure = max([SequenceMatcher(None, s, s2).ratio() for s2 in candidats_similaires])
                                s3_candidats = [s5 for s5 in candidats_similaires if(SequenceMatcher(None, s, s5).ratio()==measure)]
                                for candidat in s3_candidats:
                                    for i in range(len(smell_time[typeSmell][f][candidat])):
                                        if(i%2 == 1 and smell_time[typeSmell][f][candidat][i] != 'blank' and date > smell_time[typeSmell][f][candidat][i]):
                                            smell_time[typeSmell][f][candidat][i] = 'blank'

                                            if(s != candidat):
                                                smell_time[typeSmell][f][s] = smell_time[typeSmell][f][candidat]
                                                del smell_time[typeSmell][f][candidat]

                                            found = True
                                            nb_smell_cree[typeSmell]-=1
                                            nb_smell_corrige[typeSmell]-=1
                                            break
                                    if found == True:
                                        break
                                for element in s3_candidats:
                                    candidats_similaires.remove(element)
                                if(len(candidats_similaires) == 0 and found == False):
                                    smell_time[typeSmell][f][candidat_similaire_meilleur].append(date)
                                    smell_time[typeSmell][f][candidat_similaire_meilleur].append('blank')

                                    if(s!=candidat_similaire_meilleur):
                                        smell_time[typeSmell][f][s] = smell_time[typeSmell][f][candidat_similaire_meilleur]
                                        del smell_time[typeSmell][f][candidat_similaire_meilleur]

                                    found = True

                        else:
                            smell_time[typeSmell][f][s] = [date,'blank']

                # Si on a des smells du type recherché pour le commit actuel et le commit précédent
                if(len(smell_actuel[typeSmell])!=0 and len(smell_precedent[typeSmell])!=0):
                    # On fait une sauvegarde des smells précédents et actuels
                    sa = smell_actuel[typeSmell][0:]
                    sp = smell_precedent[typeSmell][0:]
                    # On cherche la meilleure valeur de similitude entre un smell précédent et un smell actuel
                    best_match_value = max([SequenceMatcher(None,s1,s2).ratio() for s1 in sa for s2 in sp]) if(len(sa)!=0 and len(sp)!=0) else 0
                    # Tant que la meilleure valeur de similitude est supérieure au degré établi
                    while(best_match_value > Degre_similitude):
                        #print('Meilleur valeur de similitude entre smells :',best_match_value)
                        #print('Longueur de sa : ',len(sa))
                        #print('longueur de sp : ',len(sp))

                        # On cherche les couples de smells (précédent et actuel) dont le degré de similitude est maximal
                        best_match_smells = [[s1,s2] for s1 in sa for s2 in sp if SequenceMatcher(None,s1,s2).ratio()==best_match_value]
                        # Pour chaque couple
                        for element in best_match_smells:
                            # On veut que les deux smells du couple soit encore présent dans les smells précédents et actuels (pour ne pas associer 2 smells à un même smell par exemple)
                            if (element[0] in sa and element[1] in sp) :
                                # On enlève le smell actuel de la liste des smells actuels
                                sa.remove(element[0])
                                # # On enlève le smell précédent de la liste des smells précédents
                                sp.remove(element[1])

                        # On met à jour la meilleure valeur de similtude entre smells actuels et smells précédents
                        best_match_value = max([SequenceMatcher(None,s1,s2).ratio() for s1 in sa for s2 in sp]) if(len(sa)!=0 and len(sp)!=0) else 0
                    # Pour chaque smell actuel restant, on sait qu'il a été créé
                    for s in sa:
                        # On incrémente de 1 le nombre de smells créés
                        nb_smell_cree[typeSmell]+=1
                        best_match_value = max([SequenceMatcher(None,s,s1).ratio() for s1 in smell_time[typeSmell][f].keys()]) if(len(smell_time[typeSmell][f].keys()))!=0 else 0
                        if(best_match_value > Degre_similitude) :
                            found = False
                            candidats_similaires = [e for e in smell_time[typeSmell][f].keys() if SequenceMatcher(None,s,e).ratio() > Degre_similitude]
                            candidat_similaire_meilleur = [e for e in smell_time[typeSmell][f].keys() if SequenceMatcher(None,s,e).ratio() == best_match_value][0]
                            while found == False : 
                                measure = max([SequenceMatcher(None, s, s2).ratio() for s2 in candidats_similaires])
                                s3_candidats = [s5 for s5 in candidats_similaires if(SequenceMatcher(None, s, s5).ratio()==measure)]
                                for candidat in s3_candidats:
                                    for i in range(len(smell_time[typeSmell][f][candidat])):
                                        if(i%2 == 1 and smell_time[typeSmell][f][candidat][i] != 'blank' and date > smell_time[typeSmell][f][candidat][i]):
                                            smell_time[typeSmell][f][candidat][i] = 'blank'

                                            if(s != candidat):
                                                smell_time[typeSmell][f][s] = smell_time[typeSmell][f][candidat]
                                                del smell_time[typeSmell][f][candidat]

                                            found = True
                                            nb_smell_cree[typeSmell]-=1
                                            nb_smell_corrige[typeSmell]-=1
                                            break
                                    if found == True:
                                        break
                                for element in s3_candidats:
                                    candidats_similaires.remove(element)
                                if(len(candidats_similaires) == 0 and found == False):
                                    smell_time[typeSmell][f][candidat_similaire_meilleur].append(date)
                                    smell_time[typeSmell][f][candidat_similaire_meilleur].append('blank')

                                    if(s!=candidat_similaire_meilleur):
                                        smell_time[typeSmell][f][s] = smell_time[typeSmell][f][candidat_similaire_meilleur]
                                        del smell_time[typeSmell][f][candidat_similaire_meilleur]
                                    found = True

                        else:
                            smell_time[typeSmell][f][s] = [date,'blank']

                    # Pour chaque smell précédent restant, on sait qu'il a été corrigé
                    for s2 in sp:
                        # On incrémente de 1 le nombre de smells corrigés
                        nb_smell_corrige[typeSmell]+=1
                        # On stocke sa date de correction dans notre dictionnaire
                        found = False
                        candidats_similaires = [e for e in smell_time[typeSmell][f].keys()]
                        while(found == False and len(candidats_similaires)!=0):
                            measure = max([SequenceMatcher(None, s2, s3).ratio() for s3 in candidats_similaires])
                            s4_candidats = [s5 for s5 in candidats_similaires if(SequenceMatcher(None, s2, s5).ratio()==measure)]
                            for candidat in s4_candidats:
                                if('blank' in smell_time[typeSmell][f][candidat]):
                                    s4 = candidat
                                    found = True
                                    break
                            for element in s4_candidats:
                                candidats_similaires.remove(element)
                        if found == True:
                            smell_time[typeSmell][f][s4].insert(smell_time[typeSmell][f][s4].index('blank'),date)
                            smell_time[typeSmell][f][s4].remove('blank')


                # Si on est au dernier commit du fichier
                if(commits.index(c)==len(commits)-1):
                    # Pour tous les smells qui n'ont pas été corrigés (donc qui n'ont pas de date de correction)
                    for s in smell_time[typeSmell][f].keys():
                        while('blank' in smell_time[typeSmell][f][s]):
                            smell_time[typeSmell][f][s].insert(smell_time[typeSmell][f][s].index('blank'),date_dernier_commit)
                            smell_time[typeSmell][f][s].remove('blank')


                # Les smells actuels deviennent les précédents
                smell_precedent[typeSmell] = smell_actuel[typeSmell][0:]
                #print(smell_time)
                date_ancien_commit = date
            # Après le premier commit (création du fichier), on marque à faux le fait qu'on traite le premier commit
            premier_commit = False

del historique
del smell_by_file
del data

# Pour stocker nos données statistiques, que l'on va écrire dans un csv
data = []
data.append(["Type Smell","Number created","Number killed","Number killed (%)","Number survived","Number survived (%)","Number created at the birth of file","Number created at the birth of file (%)","Average days of survival","Median days of survival"])

# Stockage des résultats
print('Stockage des résultats')

smell_time2 = {}
for ts in type_smell:
    smell_time2[ts] = []

max_period_smell = {}
for ts in smell_time.keys():
    max_period = 0
    for f in smell_time[ts].keys():
        for s in smell_time[ts][f].keys():
            intervalle = [[smell_time[ts][f][s][i],smell_time[ts][f][s][i+1]] for i in range(len(smell_time[ts][f][s])) if i%2==0]
            for inter in intervalle:
                presence_time = round((inter[1]-inter[0]).total_seconds()/86400)
                if presence_time > max_period :
                    max_period = presence_time
    max_period_smell[ts] = max_period


for ts in smell_time.keys():
    for f in smell_time[ts].keys():
        for s in smell_time[ts][f].keys():
            intervalle = [[smell_time[ts][f][s][i],smell_time[ts][f][s][i+1]] for i in range(len(smell_time[ts][f][s])) if i%2==0]
            for inter in intervalle:
                #smell_time2[ts].append((max(smell_time[ts][f][s])-min(smell_time[ts][f][s])).days)
                presence_time = round((inter[1]-inter[0]).total_seconds()/86400)
                smell_time2[ts].append(presence_time)
                if presence_time <0 :
                    print("fichier :",f)
                    print("Temps début :",inter[0],"    Temps fin :",inter[1])
                    print("Temps de présence du smell :",ts," est:",presence_time)
                    print('Smell :',s)
                    print()
                for time in range(presence_time+1):
                    survie_smells[ts].append([time,1])
                    #survie_smells.append([time,1])
                if inter[1] != date_dernier_commit :
                #    for time in range(presence_time+1,max_period_smell[ts]+1):
                #        survie_smells.append([time,1,ts])
                #        #survie_smells.append([time,1])
                #else:
                    for time in range(presence_time+1,max_period_smell[ts]+1):
                        survie_smells[ts].append([time,0])
                        #survie_smells.append([time,0])

del smell_time

smell_time_average = {}
for ts in smell_time2.keys():
    if(len(smell_time2[ts])!=0):
        smell_time_average[ts] = [round(sum(smell_time2[ts])/len(smell_time2[ts])),median(smell_time2[ts])]
    else:
        smell_time_average[ts] = [0,0]

for ts in type_smell:
    if nb_smell_cree[ts] != 0 :
        data.append([ts,nb_smell_cree[ts],nb_smell_corrige[ts],(nb_smell_corrige[ts]/nb_smell_cree[ts])*100,nb_smell_cree[ts]-nb_smell_corrige[ts],((nb_smell_cree[ts]-nb_smell_corrige[ts])/nb_smell_cree[ts])*100,nb_smell_cree_debut[ts],(nb_smell_cree_debut[ts]/nb_smell_cree[ts])*100,smell_time_average[ts][0],smell_time_average[ts][1]])
    else : 
        data.append([ts,0,0,0,0,0,0,0,0,0])
    print()
    print('Nombre de smells',ts,'créés :',nb_smell_cree[ts])
    print('Nombre de smells',ts,'corrigés :',nb_smell_corrige[ts])
    print('Nombre de smells',ts,'restant :',nb_smell_cree[ts]-nb_smell_corrige[ts])
    print('Nombre de smells',ts,'créés à la création du fichier :',nb_smell_cree_debut[ts])
    print('Nombre moyen de jours de survie des smells de type',ts,':',smell_time_average[ts][0])
    print('Nombre médian de jours de survie des smells de type',ts,':',smell_time_average[ts][1])
print()

total_cree = sum([nb_smell_cree[ts] for ts in type_smell])
total_corrige = sum([nb_smell_corrige[ts] for ts in type_smell])
total_cree_debut = sum([nb_smell_cree_debut[ts] for ts in type_smell])
data.append(["Total",total_cree,total_corrige,(total_corrige/total_cree)*100,(total_cree-total_corrige),((total_cree-total_corrige)/total_cree)*100,total_cree_debut,(total_cree_debut/total_cree)*100])

# Création des csv
with open('Grunt_%s.csv' %Degre_similitude,"w",newline='') as csv_file:
    writer = csv.writer(csv_file, delimiter=',')
    for line in data:
        writer.writerow(line)

for ts in type_smell:
    if len(survie_smells[ts]) > 1 :
        with open('Grunt_%s.csv' %ts,"w",newline='') as csv_file2:
            writer = csv.writer(csv_file2, delimiter=',')
            for line in survie_smells[ts]:
                writer.writerow(line)
