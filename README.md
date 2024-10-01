Push and Pull Kommand genom visual studio för att uppdatera databasen genom github.

git fil säkerställer att genom att bara uppdatera changes så ändrar allting till senaste ändring om det har ändrars i någon fil.

OBS installera först Git till dator/laptop

logga in i github först (genom visual studio code)

Kommando: 

git init

git add . # upload alla filer eller specifika genom att lägga in filens namn.

git commit -am "vad du vill det ska heta ex database ändring"

git remote add origin https://github.com/Kalle-NTI/APPDAGBOK.git

git push origin main

################################################################

om man vill uppdatera bara skriv in git commit -am ""
seda push för att uppdatera
eller om man vill ta in seda git pull origin main.
ex från en helt annan dator eller liknade.


###############################################################


