import subprocess
import os

# Progetti da trattare
projects = ['mihaiblaga89/bmw-connecteddrive-api']

# Per ciascun progetto
for project in projects:

    # Ci si posiziona nella directory del progetto
    print('Il progetto', project, 'è in elaborazione!')
    os.chdir(project.split('/')[0])

    # Si generano i dati di sopravvivenza per ciascun tipo di smell
    subprocess.run(['python3', 'survival_code_smells.py', '0.7'])

    # Si generano le curve di sopravvivenza per ogni tipo di smell, utilizzando un modello di Cox
    subprocess.run(['Rscript', 'analyze.r'])

    # Si ripete lo stesso con un'altra scala (il numero di commit invece del numero di giorni)
    subprocess.run(['python3', 'survival_code_smells_commit_scale.py', '0.7'])
    subprocess.run(['Rscript', 'analyze_commit_scale.r'])

    # Si ritorna alla directory padre
    os.chdir('..')
    print()
    
print("Fine esecuzione")
