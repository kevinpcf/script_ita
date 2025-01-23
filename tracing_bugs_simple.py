import re
import os
import subprocess
from subprocess import Popen, PIPE


if __name__ == '__main__' :
    # Apriamo il nostro file che ci permetterà di tracciare i bug
    with open("tracing_bugs.txt") as file:
        data = file.readlines()
        file.close()

    # Ci spostiamo nella directory di lavoro
    os.chdir('uut')

    # Per ogni file da tracciare
    for i in range(len(data)):
        if(data[i].split(' ')[0]=='Fichier'):
            bug_candidat_file = {}
            # Se abbiamo un commit candidato per il bug in questione
            if('undefined' not in data[i+2].split(' ')[1]):
                # Memorizziamo i commit da visitare e tracciare
                commit_a_tracer = data[i+4].split(' ')[1].split(',')
                commit_a_tracer[len(commit_a_tracer)-1]=re.sub('\n','',commit_a_tracer[len(commit_a_tracer)-1])
                # Memorizziamo il nome del file
                fichier = re.sub('\n','',data[i].split(' ')[1])

                #print(commit_a_tracer)
                #try:

                # Eseguiamo il nostro comando git diff che mostrerà le modifiche del file tra il commit che fissa il bug (vecchio) e il commit candidato al bug (quello in cui il bug sarebbe apparso per la prima volta)
                result = subprocess.check_output(['git','diff',commit_a_tracer[len(commit_a_tracer)-1],commit_a_tracer[0],'--',fichier],stderr=subprocess.STDOUT)
                
                #except subprocess.CalledProcessError as exc:
                #    print("Status : FAIL", exc.returncode, exc.output)
                #else:
                #    print("Output: \n{}\n".format(result))
                
                # Formattazione del risultato del comando precedente
                result = result.decode('utf-8').split('\n')
                # Ogni differenza viene memorizzata
                difference = [line.split('@@')[1].strip() for line in result if len(re.findall('@@ .+ @@',line)) > 0]
                
                #print(difference)

                # Se ci sono differenze
                if(len(difference) > 0) :
                    # Conserviamo solo le informazioni riguardanti ciò che è stato aggiunto
                    difference2 = [e.split(' ')[1] for e in difference]

                    #print(difference2)

                    # Formattiamo ciò che è stato aggiunto. Abbiamo quindi una lista di liste con 2 elementi [inizio aggiunta, fine aggiunta]
                    difference3 = [[int(e.split(',')[0]),int(e.split(',')[0])+int(e.split(',')[1])-1] for e in difference2 if len(e.split(',')) > 1]

                    #print(difference3)
                    #print('Commit iniziale : '+commit_a_tracer[0])
                    #print('Commit attuale : '+commit_a_tracer[len(commit_a_tracer)-1])

                    # Queste differenze sono i nostri bug candidati (i potenziali bug)
                    bug_candidat_file[fichier] = [bug for bug in difference3 if bug != [0,-1]]

                    #print(bug_candidat_file)

                    # Se ci sono differenze
                    if(len(bug_candidat_file[fichier]) != 0) :
                        # Visualizziamo le posizioni dei bug nel commit iniziale (quello in cui i bug sarebbero apparsi per la prima volta)
                        print('Fichier '+fichier)
                        print('Commit_responsable '+commit_a_tracer[0])
                        print('Emplacements_des_bugs',bug_candidat_file[fichier])
                        print()
