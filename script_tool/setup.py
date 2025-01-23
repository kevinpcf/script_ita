import subprocess
import os

# Progetti da trattare
projects = ['mihaiblaga89/bmw-connecteddrive-api']

# Per ciascun progetto
for project in projects:

    # Ci si posiziona nella directory del progetto
    print('Il progetto',project,'è in elaborazione!')
    os.chdir(project.split('/')[0])

    # Si copia il progetto da GitHub
    subprocess.run(['rm','-rf','uut'])
    subprocess.run(['git','clone','https://github.com/'+project+'.git','uut'])

    # Si recuperano tutti i commit del progetto
    subprocess.run(['rm','-rf','commits-data'])
    subprocess.run(['mkdir','commits-data'])
    os.system('node commits.js > /dev/null')

    # Si puliscono le informazioni sui commit del progetto
    subprocess.run(['rm','-rf','commits-clean'])
    subprocess.run(['mkdir','commits-clean'])
    subprocess.run(['node','clean.js'])

    # Si raccolgono le informazioni sui "smell" che appaiono durante l'intero progetto
    subprocess.run(['rm','-f','report.txt'])
    os.system('node report.js > report.txt')

    # Si raccolgono le informazioni sulle issue
    subprocess.run(['rm','-f','issues.json'])
    os.system('node issues.js '+project+' > issues.json')

    # Si combinano le informazioni di tracciamento degli smell e dei bug, e si registra un primo tracciamento degli smell
    subprocess.run(['rm','-f','tracing_bugs_with_false_positive.txt'])
    os.system('node combine.js > tracing_bugs_with_false_positive.txt')

    # Si rimuovono i bug che corrispondono a falsi positivi introdotti dall'algoritmo SZZ
    subprocess.run(['rm','-f','tracing_bugs.txt'])
    os.system('python3 remove_buggy_false_positive.py > tracing_bugs.txt')

    # Si tracciano le posizioni dei bug potenziali
    subprocess.run(['rm','-f','emplacements_bugs.txt'])
    os.system('python3 tracing_bugs_simple.py > emplacements_bugs.txt')

    # Si tracciano le posizioni dei bug potenziali, ma in senso lato, considerando le dipendenze
    subprocess.run(['rm','-f','emplacements_bugs_large.txt'])
    os.system('python3 tracing_bugs_large.py > emplacements_bugs_large.txt')

    # Si identificano i file "smelly"
    subprocess.run(['rm','-f','smells_count.txt'])
    os.system('python3 set_smelly.py > smells_count.txt')

    # Si mostrano i boxplot per ogni tipo di smell non booleano, quando possibile, per giustificare la soglia di peso
    subprocess.run(['Rscript','boxplot_smells_values.r'])

    # Si riordinano i commit
    subprocess.run(['python3','commit_by_date.py'])

    # Si ritorna alla directory padre
    os.chdir('..')
    print()

    # Si attende (per evitare errori di limitazione del rate API)
    subprocess.run(['sleep','0'])
    
print("Fine esecuzione")
