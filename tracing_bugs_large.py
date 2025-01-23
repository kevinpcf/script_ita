import re
import os
import subprocess
import json


if __name__ == '__main__' :
    # Apriamo il nostro file che contiene le posizioni dei bug
    with open("emplacements_bugs.txt") as file:
        data = file.readlines()
        file.close()

    # Ci spostiamo nella directory di lavoro
    os.chdir('uut')

    # Per ogni file
    for i in range(len(data)):
        if(data[i].split(' ')[0]=='Fichier'):
            # Memorizziamo il nome del file
            file = data[i].split(' ')[1].split('\n')[0]
            #print(file)
            # Memorizziamo il commit "con bug"
            commit = data[i+1].split(' ')[1].split('\n')[0]
            # Memorizziamo le posizioni dei bug nel file nel commit
            bugs = eval(re.sub('\n','',re.sub('Emplacements_des_bugs ','',data[i+2])))
            
            # Passiamo al commit "con bug"
            os.system('git reset -q --hard && git checkout -q '+commit)

            # Applichiamo il parsing sul file "con bug" per ampliare le posizioni potenziali dei bug
            subprocess.run(['node','../ast.js',file])

            # Apriamo il file di parsing generato precedentemente
            with open("ast.json") as json_data:
                ast = json.load(json_data)
                json_data.close()

            # Visualizziamo le variabili e le funzioni create, con la loro inizializzazione e i loro riferimenti
            # print(ast)

            new_bugs = []

            # Trattiamo le intersezioni tra i bug attuali che conosciamo e le inizializzazioni/riferimenti di variabili e funzioni
            # Per ciascuno dei bug attuali noti
            for bug in bugs:
                # Per ogni variabile e funzione conosciuta
                for elements in ast.keys():
                    if(ast[elements] != {}):
                        for element in ast[elements].keys():
                            # Se l'intersezione tra il bug e l'inizializzazione della variabile/funzione non è vuota
                            inter = [max(bug[0], ast[elements][element]['Orig'][0]),min(bug[-1], ast[elements][element]['Orig'][-1])] if max(bug[0], ast[elements][element]['Orig'][0]) <= min(bug[-1], ast[elements][element]['Orig'][-1]) else []
                            if inter != []:
                                # Consideriamo il blocco di inizializzazione della variabile/funzione nei bug
                                new_bugs.append([ast[elements][element]['Orig'][0],ast[elements][element]['Orig'][1]])
                                # Consideriamo tutti i punti di riferimento per la funzione/variabile nei bug
                                for ref in ast[elements][element]['References']:
                                    new_bugs.append(ref)
                            # Per ogni punto in cui la funzione/variabile viene chiamata
                            for ref in ast[elements][element]['References']:
                                # Se l'intersezione tra il bug e la chiamata della funzione/variabile non è vuota
                                inter = [max(bug[0], ref[0]),min(bug[-1], ref[-1])] if max(bug[0], ref[0]) <= min(bug[-1], ref[-1]) else []
                                if inter != []:
                                    # Consideriamo il blocco di inizializzazione della variabile/funzione nei bug
                                    new_bugs.append([ast[elements][element]['Orig'][0],ast[elements][element]['Orig'][1]])
                                    # Consideriamo tutti i punti di riferimento per la funzione/variabile nei bug
                                    for ref2 in ast[elements][element]['References']:
                                        new_bugs.append(ref2)
            
            # Aggiungiamo i nostri nuovi bug a quelli già noti
            bugs = bugs + new_bugs

            # Visualizziamo il nome del file, il commit "con bug" e i potenziali luoghi dei bug
            print('Fichier '+file)
            print('Commit_responsable '+commit)
            print('Emplacements_des_bugs',bugs)
            print()

            # Eliminiamo il file ast.json
            subprocess.run(['rm','-f','ast.json'])
            print()
