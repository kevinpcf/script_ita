import json

# Apertura del file historique_fichiers.json
with open("historique_fichiers.json") as json_data:
    historique = json.load(json_data)
    json_data.close()

commit_by_epoque = {}

with open("report.txt") as file:
    data = file.readlines()
    file.close()

for i in range(len(data)):
    if(data[i].split(' ')[0]=='COMMIT'):
        epoque = int(data[i].split(' ')[1].split('\t')[1].split('\n')[0])
        commit = data[i].split(' ')[1].split('\t')[0]
        commit_by_epoque[commit] = epoque

for fichier in historique.keys():
    ancien = None
    while(ancien == None or historique[fichier] != ancien):
        ancien = historique[fichier][:]
        for i in range(len(historique[fichier])-1):
            if(commit_by_epoque[historique[fichier][i]] > commit_by_epoque[historique[fichier][i+1]]):
                print('Commits da invertire :',historique[fichier][i],historique[fichier][i+1])
                z = historique[fichier][i]
                historique[fichier][i] = historique[fichier][i+1]
                historique[fichier][i+1] = z

with open("historique_fichiers2.json",'w') as json_data2 :
    json.dump(historique, json_data2)
