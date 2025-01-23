import re
import json
from datetime import datetime
import csv
import sys

# On stocke nos données décrivant quels fichiers sont smelly et lesquels ne le sont pas, et qui contiennent uniquement les smells qui nous itnéressent
with open("set_smelly.json") as json_data:
    data = json.load(json_data)
    json_data.close()

# Ouverture du fichier historique_fichiers.json
with open("historique_fichiers2.json") as json_data2:
    historique = json.load(json_data2)
    json_data2.close()

# On stocke les noms des 12 types de smells
type_smell = ['max-statements','max-depth','complexity','max-len','max-params','max-nested-callbacks','complex-switch-case','this-assign','complex-chaining','no-reassign','no-extra-bind','cond-assign']

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
# Filenames_to_link_without_duplicate réunit les noms d'un même fichier, et cela pour chaque fichier
filenames_to_link_without_duplicate = []
for element in filenames_to_link:
    if(element != [0,0]):
        filenames_to_link_without_duplicate.append(element)

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

# On stocke dans un dictionnaire les différents noms que peut avoir chaque fichier
dict_files_names = {}
for f in filenames_to_link_without_duplicate :
    for name in f:
        dict_files_names[name] = f
#print(dict_files_names)

# On regarde si chacun des fichiers est supprimé dans un des commits de data
# Si c'est le cas, on rajoute le commit qui le surpprime s'il n'est pas déjà présent dans l'historique
for file in historique.keys():
    for commit in data:
        if(len(commit["changes"])!=0):
            for change in commit["changes"]:
                if(change["f"] == file and change["type"]=="deleted"):
                    if(commit["commit"] not in historique[file]):
                        historique[file].append(commit["commit"])
print("Les informations sur les fichiers supprimés dans les commits ont été récupérées")
#print(file_deleted)

# On va ensuite reéanrranger les commits dans les historiques de fichiers, pour les ranger par ordre d'apparition
commit_by_epoque = {}
# On ouvre le fichier report.txt qui contient l'ordre d'apparition des différents commits
with open("report.txt") as file:
    data2 = file.readlines()
    file.close()
# On stocke les commits par époque à partir du fichier report.txt
for i in range(len(data2)):
    if(data2[i].split(' ')[0]=='COMMIT'):
        epoque = int(data2[i].split(' ')[1].split('\t')[1].split('\n')[0])
        commit = data2[i].split(' ')[1].split('\t')[0]
        commit_by_epoque[commit] = epoque
# On regarde dans l'historique de chaque fichier si les commits sont bien rangés dans l'ordre, auquel cas on permute les commits mal classés
for fichier in historique.keys():
    ancien = None
    while(ancien == None or historique[fichier] != ancien):
        ancien = historique[fichier][:]
        for i in range(len(historique[fichier])-1):
            if(commit_by_epoque[historique[fichier][i]] > commit_by_epoque[historique[fichier][i+1]]):
                #print('Commits à inverser :',historique[fichier][i],historique[fichier][i+1])
                z = historique[fichier][i]
                historique[fichier][i] = historique[fichier][i+1]
                historique[fichier][i+1] = z

# On récupère les smells pour chaque fichier, à chaque fois qu'il est modifié. Les smells correspondent aux 10% smells les plus importants car on a ouvert le fichier set_smelly.json
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
                        if(file in f):
                            for f2 in f:
                                if f2 in files_changed:
                                    fichier = f2
                for change in element["changes"]:
                    if(change["f"]==fichier):
                        fixes = [eval(fix) for fix in element["fix"]] if len(element["fix"]) > 0 else []
                        bugs = [[eval(bug.split(" @@ ")[0]),bug.split(" @@ ")[1]] for bug in element["buggy"]] if len(element["buggy"]) > 0 else []
                        smell_by_file[file][commit] = [change,fixes,bugs]

#print(smell_by_file)
print('Smells récupérés')

# On stocke une liste de liste qui va nous permettre de faire les analyses de survie, et d'étudier les risques de fautes dans les fichiers smelly et non-smelly
final_data = []
final_data.append(["time",'prevBugs','linesAdded','linesRemoved','totalChurn','loc','maxstatements','maxdepth','complexity','maxlen','maxparams','maxnestedcallbacks','complexswitchcase','thisassign','complexchaining','noreassign','noextrabind','condassign',"event","smelly"])

# Pour chaque fichier dans smell_by_file
for f in smell_by_file.keys():
    # Si le fichier se finit par .js (et est donc un fichier javascript) et ne finit pas par .min.js
    if(f.endswith('.js')==True and f.endswith('.min.js')==False):
        # On stocke les commits qui modifie le fichier
        commits = historique[f]
        # Pour compter le nombre de bug fix qu'a accumulé le fichier traité
        prevbugs = 0
        # Pour chacun de ces commits
        for i in range(len(commits)):
            # line va stocker les informations concernant le fichier et le commit étudiés
            line = {}
            # On stocke la date du commit actuel, en utilisant les données data
            for el in data : 
                if(commits[i] == el["commit"]):
                    date_commit_actual = datetime.strptime(el["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
                    break
            # Si on est au premier commit, on considère le commit actuel comme étant également le précédent (afin d'avoir time = 0 pour le premier commit du fichier)
            if(i == 0):
                date_commit_previous = datetime.strptime(el["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
            # Sinon, on stocke également la date du commit précédemment traité pour ce fichier
            else:
                for el2 in data:
                    if(commits[i-1] == el2["commit"]):
                        date_commit_previous = datetime.strptime(el2["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
                        break
            # time est égal au temps (en heures) qui s'est écoulé entre la révision actuelle du fichier et celle précédente (donc vaut 0 pour le premier commit du fichier)
            line["time"] = round((date_commit_actual-date_commit_previous).total_seconds()/3600)
            # Sanity check : on regarde qu'il n'y ait pas d'incohérence dans l'ordre de traitement des commits du fichier
            if(line["time"]<0):
                print("Erreur de temps")
                print(line["time"])
                print(commits[i])
                print(commits[i-1])
                print(f)
                print()

            # already va permettre de voir si les variables de smells ont été traitées dans cette boucle pour le fichier et le commit traités
            already = {}
            already["smelly"] = False
            for ts in type_smell:
                already[ts] = False

            # On met "event" à 0.
            # "event" vaut 1 si le commit actuel est un bug fix, et 0 sinon.
            line["event"] = 0
            # Si le commit actuel est un bug fix
            if(len(smell_by_file[f][commits[i]][1]) > 0):
                # On incrémente le nombre de bug fix 
                prevbugs += len(smell_by_file[f][commits[i]][1])
                # On met "event" à 1
                line["event"] = 1
                # Maintenant on veut voir s'il y a un lien entre le bug fix et les smells du fichier, en regardant si le fichier était à l'introduction du bug
                # Pour chaque fix dans le commit bug fix
                for fix in smell_by_file[f][commits[i]][1]:
                    # Pour chaque commit qui modifie le fichier traité
                    for j in range(len(commits)):
                        # Pour chaque bug dans le commit du fichier
                        for bug in smell_by_file[f][commits[j]][2]:
                            # Si le bug correspond au fix (id du bug/fix)
                            if (fix == bug[0]):
                                # Si le fichier buggé correspond au fichier actuellement traité, ou si le nom du fichier buggé est dans l'historique des noms du fichier actuellement traité
                                if(f == bug[1] or (f in dict_files_names.keys() and bug[1] in dict_files_names[f])):
                                    # Si de plus le fichier buggé n'est pas smelly
                                    if(smell_by_file[f][commits[j]][0]["smelly"] == 0):
                                        # On met "smelly" à 0 car il n'y a pas de lien entre les smells et le bug fix
                                        line["smelly"] = 0
                                        # On indique que "smelly" est traité
                                        already["smelly"] = True
                                    # Pour chaque type de smell
                                    for ts in type_smell:
                                        # Si le type de smell n'apparaît pas dans le fichier buggé
                                        if(ts not in smell_by_file[f][commits[j]][0]["smells"].keys()):
                                            # Alors on met ts à 0 car il n'y a pas de lien entre les smells de ce type et le bug fix
                                            line[ts] = 0
                                            # On indique que ce type de smell est traité
                                            already[ts] = True
                               #else:
                               #     print(f)
                               #     print(bug[1])
                               #     print()
            
            # Pour chaque type de smell
            for ts in type_smell:
                # Si ce type de smell n'a pas été déjà traité
                if(already[ts] == False):
                    # Si ce type de smell apparaît dans le commit et fichier traités
                    if(ts in smell_by_file[f][commits[i]][0]["smells"].keys()):
                        # On met à 1 line[ts]
                        line[ts] = 1
                    # Sinon, line[ts] vaut 0
                    else:
                        line[ts] = 0
            # Si "smelly" n'a pas déjà été traité
            if(already["smelly"] == False) :
                # Si somme_smell vaut 0, c'est qu'aucun des types de smell traités n'apparaît. On met donc "smelly" à 0
                if(smell_by_file[f][commits[i]][0]["smelly"]==0):
                    line["smelly"] = 0
                # Sinon, on met "smelly" à 1
                else:
                    line["smelly"] = 1
            
            # On stocke prevbugs, le nombre de lignes ajoutées, le nombre de lignes supprimées, le totalChurn, et le loc
            line["prevbugs"] = prevbugs
            line["linesAdded"] = smell_by_file[f][commits[i]][0]["churn"][0]
            line["linesRemoved"] = smell_by_file[f][commits[i]][0]["churn"][1]
            line["totalChurn"] = smell_by_file[f][commits[i]][0]["churn"][0] + smell_by_file[f][commits[i]][0]["churn"][1]
            line["loc"] = smell_by_file[f][commits[i]][0]["churn"][2]

            # On stocke les informations concernant le fichier et commit traités dans final_data
            final_data.append([line["time"],line["prevbugs"],line["linesAdded"],line["linesRemoved"],line["totalChurn"],line["loc"],line['max-statements'],line['max-depth'],line['complexity'],line['max-len'],line['max-params'],line['max-nested-callbacks'],line['complex-switch-case'],line['this-assign'],line['complex-chaining'],line['no-reassign'],line['no-extra-bind'],line['cond-assign'],line["event"],line["smelly"]])

# On enregistre nos informations dans un csv, sachant qu'on a traité ici les liens entre smells et bug fix à la granularité du fichier
with open('Grunt_bugs_smells_file-grain.csv',"w",newline='') as csv_file:
    writer = csv.writer(csv_file, delimiter=',')
    for line in final_data:
        writer.writerow(line)

print()
print("Fin traitement à la granularité du fichier")
print()

emplacements_bugs_all = []
with open("emplacements_bugs.txt") as file:
    data_bugs = file.readlines()
    file.close()

print("Début stockage emplacements bugs")
for i in range(len(data_bugs)):
    if(data_bugs[i].split(' ')[0]=='Fichier'):
        file = data_bugs[i].split(' ')[1].split('\n')[0]
        commit = data_bugs[i+1].split(' ')[1].split('\n')[0]
        bugs = eval(re.sub('\n','',re.sub('Emplacements_des_bugs ','',data_bugs[i+2])))
        found = False
        for f in smell_by_file.keys():
            if(file == f or (file in dict_files_names.keys() and f in dict_files_names[file])):
                for c in smell_by_file[f].keys():
                    if(commit == c):
                        smell_by_file[f][c].append(bugs)
print("Fin stockage emplacements bugs")
for file in smell_by_file.keys():
    for commit in smell_by_file[file].keys():
        if len(smell_by_file[file][commit]) == 3:
            smell_by_file[file][commit].append([])

# On stocke une liste de liste qui va nous permettre de faire les analyses de survie, et d'étudier les risques de fautes dans les fichiers smelly et non-smelly
final_data = []
final_data.append(["time",'prevBugs','linesAdded','linesRemoved','totalChurn','loc','maxstatements','maxdepth','complexity','maxlen','maxparams','maxnestedcallbacks','complexswitchcase','thisassign','complexchaining','noreassign','noextrabind','condassign',"event","smelly","eventmaxstatements","eventmaxdepth",'eventcomplexity','eventmaxlen','eventmaxparams','eventmaxnestedcallbacks','eventcomplexswitchcase','eventthisassign','eventcomplexchaining','eventnoreassign','eventnoextrabind','eventcondassign'])

# Pour chaque fichier dans smell_by_file
for f in smell_by_file.keys():
    # Si le fichier se finit par .js (et est donc un fichier javascript) et ne finit pas par .min.js
    if(f.endswith('.js')==True and f.endswith('.min.js')==False):
        # On stocke les commits qui modifie le fichier
        commits = historique[f]
        # Pour compter le nombre de bug fix qu'a accumulé le fichier traité
        prevbugs = 0
        # Pour chacun de ces commits
        for i in range(len(commits)):
            # line va stocker les informations concernant le fichier et le commit étudiés
            line = {}
            # On stocke la date du commit actuel, en utilisant les données data
            for el in data : 
                if(commits[i] == el["commit"]):
                    date_commit_actual = datetime.strptime(el["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
                    break
            # Si on est au premier commit, on considère le commit actuel comme étant également le précédent (afin d'avoir time = 0 pour le premier commit du fichier)
            if(i == 0):
                date_commit_previous = datetime.strptime(el["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
            # Sinon, on stocke également la date du commit précédemment traité pour ce fichier
            else:
                for el2 in data:
                    if(commits[i-1] == el2["commit"]):
                        date_commit_previous = datetime.strptime(el2["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
                        break
            # time est égal au temps (en heures) qui s'est écoulé entre la révision actuelle du fichier et celle précédente (donc vaut 0 pour le premier commit du fichier)
            line["time"] = round((date_commit_actual-date_commit_previous).total_seconds()/3600)
            # Sanity check : on regarde qu'il n'y ait pas d'incohérence dans l'ordre de traitement des commits du fichier
            if(line["time"]<0):
                print("Erreur de temps")
                print(line["time"])
                print(commits[i])
                print(commits[i-1])
                print(f)
                print()

            # already va permettre de voir si les variables de smells ont été traitées dans cette boucle pour le fichier et le commit traités
            already = {}
            already["smelly"] = False
            for ts in type_smell:
                already[ts] = False

            # On met "event" à 0.
            # "event" vaut 1 si le commit actuel est un bug fix, et 0 sinon.
            line["event"] = 0
            for ts in type_smell:
                line["event"+ts] = 0
            # Si le commit actuel est un bug fix
            if(len(smell_by_file[f][commits[i]][1]) > 0):
                # On incrémente le nombre de bug fix 
                prevbugs += len(smell_by_file[f][commits[i]][1])
                # On met "event" à 1
                line["event"] = 1
                for ts in type_smell:
                    line["event"+ts] = 1
                # Maintenant on veut voir s'il y a un lien entre le bug fix et les smells du fichier, en regardant si le fichier était à l'introduction du bug
                # Pour chaque fix dans le commit bug fix
                for fix in smell_by_file[f][commits[i]][1]:
                    # Pour chaque commit qui modifie le fichier traité
                    for j in range(len(commits)):
                        # Pour chaque bug dans le commit du fichier
                        for bug in smell_by_file[f][commits[j]][2]:
                            # Si le bug correspond au fix (id du bug/fix)
                            if (fix == bug[0]):
                                # Si le fichier buggé correspond au fichier actuellement traité, ou si le nom du fichier buggé est dans l'historique des noms du fichier actuellement traité
                                if(f == bug[1] or (f in dict_files_names.keys() and bug[1] in dict_files_names[f])):
                                    # Si de plus le fichier buggé n'est pas smelly
                                    if(smell_by_file[f][commits[j]][0]["smelly"] == 0):
                                        # On met "smelly" à 0 car il n'y a pas de lien entre les smells et le bug fix
                                        line["smelly"] = 0
                                        # On indique que "smelly" est traité
                                        already["smelly"] = True
                                    else:
                                        correlation = False
                                        emplacements_smells = [smell_by_file[f][commits[j]][0]["smells"][ts][l][1] for ts in type_smell if(ts in smell_by_file[f][commits[j]][0]["smells"].keys()) for l in range(len(smell_by_file[f][commits[j]][0]["smells"][ts]))]
                                        emplacements_bugs = smell_by_file[f][commits[j]][3]
                                        for s in emplacements_smells:
                                            for b in emplacements_bugs:
                                                if (b[1] < s[0] or b[0] > s[1]):
                                                    continue
                                                correlation = True
                                        if correlation == False:
                                            # On met "event" à 0 car il n'y a pas de lien entre les smells et le bug fix
                                            line["event"] = 0

                                    # Pour chaque type de smell
                                    for ts in type_smell:
                                        # Si le type de smell n'apparaît pas dans le fichier buggé
                                        if(ts not in smell_by_file[f][commits[j]][0]["smells"].keys()):
                                            # Alors on met ts à 0 car il n'y a pas de lien entre les smells de ce type et le bug fix
                                            line[ts] = 0
                                            # On indique que ce type de smell est traité
                                            already[ts] = True
                                        else:
                                            correlation = False
                                            emplacements_smells = [smell_by_file[f][commits[j]][0]["smells"][ts][l][1] for l in range(len(smell_by_file[f][commits[j]][0]["smells"][ts]))]
                                            emplacements_bugs = smell_by_file[f][commits[j]][3]
                                            for s in emplacements_smells:
                                                for b in emplacements_bugs:
                                                    if (b[1] < s[0] or b[0] > s[1]):
                                                        continue
                                                    correlation = True
                                            if correlation == False:
                                                line["event"+ts] = 0

                               #else:
                               #     print(f)
                               #     print(bug[1])
                               #     print()
            
            # Pour chaque type de smell
            for ts in type_smell:
                # Si ce type de smell n'a pas été déjà traité
                if(already[ts] == False):
                    # Si ce type de smell apparaît dans le commit et fichier traités
                    if(ts in smell_by_file[f][commits[i]][0]["smells"].keys()):
                        # On met à 1 line[ts]
                        line[ts] = 1
                    # Sinon, line[ts] vaut 0
                    else:
                        line[ts] = 0
            # Si "smelly" n'a pas déjà été traité
            if(already["smelly"] == False) :
                # Si somme_smell vaut 0, c'est qu'aucun des types de smell traités n'apparaît. On met donc "smelly" à 0
                if(smell_by_file[f][commits[i]][0]["smelly"]==0):
                    line["smelly"] = 0
                # Sinon, on met "smelly" à 1
                else:
                    line["smelly"] = 1
            
            # On stocke prevbugs, le nombre de lignes ajoutées, le nombre de lignes supprimées, le totalChurn, et le loc
            line["prevbugs"] = prevbugs
            line["linesAdded"] = smell_by_file[f][commits[i]][0]["churn"][0]
            line["linesRemoved"] = smell_by_file[f][commits[i]][0]["churn"][1]
            line["totalChurn"] = smell_by_file[f][commits[i]][0]["churn"][0] + smell_by_file[f][commits[i]][0]["churn"][1]
            line["loc"] = smell_by_file[f][commits[i]][0]["churn"][2]

            # On stocke les informations concernant le fichier et commit traités dans final_data
            final_data.append([line["time"],line["prevbugs"],line["linesAdded"],line["linesRemoved"],line["totalChurn"],line["loc"],line['max-statements'],line['max-depth'],line['complexity'],line['max-len'],line['max-params'],line['max-nested-callbacks'],line['complex-switch-case'],line['this-assign'],line['complex-chaining'],line['no-reassign'],line['no-extra-bind'],line['cond-assign'],line["event"],line["smelly"],line['eventmax-statements'],line['eventmax-depth'],line['eventcomplexity'],line['eventmax-len'],line['eventmax-params'],line['eventmax-nested-callbacks'],line['eventcomplex-switch-case'],line['eventthis-assign'],line['eventcomplex-chaining'],line['eventno-reassign'],line['eventno-extra-bind'],line['eventcond-assign']])

# On enregistre nos informations dans un csv, sachant qu'on a traité ici les liens entre smells et bug fix à la granularité du fichier
with open('Grunt_bugs_smells_line-grain.csv',"w",newline='') as csv_file:
    writer = csv.writer(csv_file, delimiter=',')
    for line in final_data:
        writer.writerow(line)

print()
print("Fin traitement à la granularité de la ligne")
print()

emplacements_bugs_all = []
with open("emplacements_bugs_large.txt") as file:
    data_bugs = file.readlines()
    file.close()

print("Début stockage emplacements bugs")
for i in range(len(data_bugs)):
    if(data_bugs[i].split(' ')[0]=='Fichier'):
        file = data_bugs[i].split(' ')[1].split('\n')[0]
        commit = data_bugs[i+1].split(' ')[1].split('\n')[0]
        bugs = eval(re.sub('\n','',re.sub('Emplacements_des_bugs ','',data_bugs[i+2])))
        found = False
        for f in smell_by_file.keys():
            if(file == f or (file in dict_files_names.keys() and f in dict_files_names[file])):
                for c in smell_by_file[f].keys():
                    if(commit == c):
                        smell_by_file[f][c].append(bugs)
print("Fin stockage emplacements bugs")
for file in smell_by_file.keys():
    for commit in smell_by_file[file].keys():
        if len(smell_by_file[file][commit]) == 4:
            smell_by_file[file][commit].append([])

# On stocke une liste de liste qui va nous permettre de faire les analyses de survie, et d'étudier les risques de fautes dans les fichiers smelly et non-smelly
final_data = []
final_data.append(["time",'prevBugs','linesAdded','linesRemoved','totalChurn','loc','maxstatements','maxdepth','complexity','maxlen','maxparams','maxnestedcallbacks','complexswitchcase','thisassign','complexchaining','noreassign','noextrabind','condassign',"event","smelly","eventmaxstatements","eventmaxdepth",'eventcomplexity','eventmaxlen','eventmaxparams','eventmaxnestedcallbacks','eventcomplexswitchcase','eventthisassign','eventcomplexchaining','eventnoreassign','eventnoextrabind','eventcondassign'])

# Pour chaque fichier dans smell_by_file
for f in smell_by_file.keys():
    # Si le fichier se finit par .js (et est donc un fichier javascript) et ne finit pas par .min.js
    if(f.endswith('.js')==True and f.endswith('.min.js')==False):
        # On stocke les commits qui modifie le fichier
        commits = historique[f]
        # Pour compter le nombre de bug fix qu'a accumulé le fichier traité
        prevbugs = 0
        # Pour chacun de ces commits
        for i in range(len(commits)):
            # line va stocker les informations concernant le fichier et le commit étudiés
            line = {}
            # On stocke la date du commit actuel, en utilisant les données data
            for el in data : 
                if(commits[i] == el["commit"]):
                    date_commit_actual = datetime.strptime(el["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
                    break
            # Si on est au premier commit, on considère le commit actuel comme étant également le précédent (afin d'avoir time = 0 pour le premier commit du fichier)
            if(i == 0):
                date_commit_previous = datetime.strptime(el["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
            # Sinon, on stocke également la date du commit précédemment traité pour ce fichier
            else:
                for el2 in data:
                    if(commits[i-1] == el2["commit"]):
                        date_commit_previous = datetime.strptime(el2["date"].split('.')[0],"%Y-%m-%dT%H:%M:%S")
                        break
            # time est égal au temps (en heures) qui s'est écoulé entre la révision actuelle du fichier et celle précédente (donc vaut 0 pour le premier commit du fichier)
            line["time"] = round((date_commit_actual-date_commit_previous).total_seconds()/3600)
            # Sanity check : on regarde qu'il n'y ait pas d'incohérence dans l'ordre de traitement des commits du fichier
            if(line["time"]<0):
                print("Erreur de temps")
                print(line["time"])
                print(commits[i])
                print(commits[i-1])
                print(f)
                print()

            # already va permettre de voir si les variables de smells ont été traitées dans cette boucle pour le fichier et le commit traités
            already = {}
            already["smelly"] = False
            for ts in type_smell:
                already[ts] = False

            # On met "event" à 0.
            # "event" vaut 1 si le commit actuel est un bug fix, et 0 sinon.
            line["event"] = 0
            for ts in type_smell:
                line["event"+ts] = 0
            # Si le commit actuel est un bug fix
            if(len(smell_by_file[f][commits[i]][1]) > 0):
                # On incrémente le nombre de bug fix 
                prevbugs += len(smell_by_file[f][commits[i]][1])
                # On met "event" à 1
                line["event"] = 1
                for ts in type_smell:
                    line["event"+ts] = 1
                # Maintenant on veut voir s'il y a un lien entre le bug fix et les smells du fichier, en regardant si le fichier était à l'introduction du bug
                # Pour chaque fix dans le commit bug fix
                for fix in smell_by_file[f][commits[i]][1]:
                    # Pour chaque commit qui modifie le fichier traité
                    for j in range(len(commits)):
                        # Pour chaque bug dans le commit du fichier
                        for bug in smell_by_file[f][commits[j]][2]:
                            # Si le bug correspond au fix (id du bug/fix)
                            if (fix == bug[0]):
                                # Si le fichier buggé correspond au fichier actuellement traité, ou si le nom du fichier buggé est dans l'historique des noms du fichier actuellement traité
                                if(f == bug[1] or (f in dict_files_names.keys() and bug[1] in dict_files_names[f])):
                                    # Si de plus le fichier buggé n'est pas smelly
                                    if(smell_by_file[f][commits[j]][0]["smelly"] == 0):
                                        # On met "smelly" à 0 car il n'y a pas de lien entre les smells et le bug fix
                                        line["smelly"] = 0
                                        # On indique que "smelly" est traité
                                        already["smelly"] = True
                                    else:
                                        correlation = False
                                        emplacements_smells = [smell_by_file[f][commits[j]][0]["smells"][ts][l][1] for ts in type_smell if(ts in smell_by_file[f][commits[j]][0]["smells"].keys()) for l in range(len(smell_by_file[f][commits[j]][0]["smells"][ts]))]
                                        emplacements_bugs = smell_by_file[f][commits[j]][4]
                                        for s in emplacements_smells:
                                            for b in emplacements_bugs:
                                                if (b[1] < s[0] or b[0] > s[1]):
                                                    continue
                                                correlation = True
                                        if correlation == False:
                                            # On met "event" à 0 car il n'y a pas de lien entre les smells et le bug fix
                                            line["event"] = 0

                                    # Pour chaque type de smell
                                    for ts in type_smell:
                                        # Si le type de smell n'apparaît pas dans le fichier buggé
                                        if(ts not in smell_by_file[f][commits[j]][0]["smells"].keys()):
                                            # Alors on met ts à 0 car il n'y a pas de lien entre les smells de ce type et le bug fix
                                            line[ts] = 0
                                            # On indique que ce type de smell est traité
                                            already[ts] = True
                                        else:
                                            correlation = False
                                            emplacements_smells = [smell_by_file[f][commits[j]][0]["smells"][ts][l][1] for l in range(len(smell_by_file[f][commits[j]][0]["smells"][ts]))]
                                            emplacements_bugs = smell_by_file[f][commits[j]][4]
                                            for s in emplacements_smells:
                                                for b in emplacements_bugs:
                                                    if (b[1] < s[0] or b[0] > s[1]):
                                                        continue
                                                    correlation = True
                                            if correlation == False:
                                                line["event"+ts] = 0

                               #else:
                               #     print(f)
                               #     print(bug[1])
                               #     print()
            
            # Pour chaque type de smell
            for ts in type_smell:
                # Si ce type de smell n'a pas été déjà traité
                if(already[ts] == False):
                    # Si ce type de smell apparaît dans le commit et fichier traités
                    if(ts in smell_by_file[f][commits[i]][0]["smells"].keys()):
                        # On met à 1 line[ts]
                        line[ts] = 1
                    # Sinon, line[ts] vaut 0
                    else:
                        line[ts] = 0
            # Si "smelly" n'a pas déjà été traité
            if(already["smelly"] == False) :
                # Si somme_smell vaut 0, c'est qu'aucun des types de smell traités n'apparaît. On met donc "smelly" à 0
                if(smell_by_file[f][commits[i]][0]["smelly"]==0):
                    line["smelly"] = 0
                # Sinon, on met "smelly" à 1
                else:
                    line["smelly"] = 1
            
            # On stocke prevbugs, le nombre de lignes ajoutées, le nombre de lignes supprimées, le totalChurn, et le loc
            line["prevbugs"] = prevbugs
            line["linesAdded"] = smell_by_file[f][commits[i]][0]["churn"][0]
            line["linesRemoved"] = smell_by_file[f][commits[i]][0]["churn"][1]
            line["totalChurn"] = smell_by_file[f][commits[i]][0]["churn"][0] + smell_by_file[f][commits[i]][0]["churn"][1]
            line["loc"] = smell_by_file[f][commits[i]][0]["churn"][2]

            # On stocke les informations concernant le fichier et commit traités dans final_data
            final_data.append([line["time"],line["prevbugs"],line["linesAdded"],line["linesRemoved"],line["totalChurn"],line["loc"],line['max-statements'],line['max-depth'],line['complexity'],line['max-len'],line['max-params'],line['max-nested-callbacks'],line['complex-switch-case'],line['this-assign'],line['complex-chaining'],line['no-reassign'],line['no-extra-bind'],line['cond-assign'],line["event"],line["smelly"],line['eventmax-statements'],line['eventmax-depth'],line['eventcomplexity'],line['eventmax-len'],line['eventmax-params'],line['eventmax-nested-callbacks'],line['eventcomplex-switch-case'],line['eventthis-assign'],line['eventcomplex-chaining'],line['eventno-reassign'],line['eventno-extra-bind'],line['eventcond-assign']])

# On enregistre nos informations dans un csv, sachant qu'on a traité ici les liens entre smells et bug fix à la granularité du fichier
with open('Grunt_bugs_smells_line-grain_large.csv',"w",newline='') as csv_file:
    writer = csv.writer(csv_file, delimiter=',')
    for line in final_data:
        writer.writerow(line)

print()
print("Fin traitement à la granularité de la ligne avec les dépendances")
print()
