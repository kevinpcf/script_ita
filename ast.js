// Codice per estrarre dall'AST (generato da uglifyjs) le informazioni riguardanti gli utilizzi di funzioni e variabili

// UglifyJS permette di costruire l'AST
var UglifyJS = require('uglify-js')
  , fs = require('fs')
// Il terzo argomento della riga di comando corrisponde al file JavaScript da analizzare
  , filename = process.argv[2];
//console.log(filename);
// Si estrae il codice da questo file
code = String(fs.readFileSync(filename));
// Si costruisce l'AST di questo file
var Ast = UglifyJS.minify(code,{output : { ast : true, code : false},compress : {sequences : false}});

// data conterrà le nostre informazioni utili (per le variabili e le funzioni)
data = {};
data["variables"] = {}
data["functions"] = {}

// L'AST non è vuoto
if ('ast' in Ast) {
  // Si memorizzano i nomi delle variabili
  variables = Object.keys(Ast.ast.variables._values)
  //console.log("Ecco le variabili:", variables)

  // Per ogni variabile
  for (i = 0; i < variables.length; i++) {
    // Si inizializza "Orig" che conterrà le righe di inizializzazione, e "References" che conterrà le righe di utilizzo
    data["variables"][variables[i]] = {"Orig":[],"References":[]}
    // Si memorizza la riga di inizio dell'inizializzazione
    data["variables"][variables[i]]["Orig"].push(Ast.ast.variables._values[variables[i]].orig[0].start.line)
    // Fin conterrà la riga di fine dell'inizializzazione
    fin = null
    // Si analizza il corpo dell'AST
    for (j=0; j<Ast.ast.body.length; j++) {
      // Se un nodo AST contiene la chiave "definitions"
      if('definitions' in Ast.ast.body[j]) {
        // Si analizzano le definizioni presenti
        for (k=0; k<Ast.ast.body[j].definitions.length; k++) {
          // Se una delle definizioni corrisponde a una variabile con lo stesso nome di quella in analisi
          if(Ast.ast.body[j].definitions[k].name.name == Ast.ast.variables._values[variables[i]].name) {
            // Si memorizza la riga di fine dell'inizializzazione della variabile
            fin = Ast.ast.body[j].definitions[k].end.endline
          }
        }
      }
    }
    // Si memorizza questa riga di fine
    data["variables"][variables[i]]["Orig"].push(fin)

    // Si analizzano tutti i riferimenti successivi alla variabile
    for (j=0; j<Ast.ast.variables._values[variables[i]].references.length; j++) {
      // Si memorizzano le righe di inizio e fine di ogni riferimento a questa variabile
      data["variables"][variables[i]]["References"].push([Ast.ast.variables._values[variables[i]].references[j].start.line,Ast.ast.variables._values[variables[i]].re
