var fs = require('fs');
var LC = require('./cloc.js');
var exec = require('child_process').exec;
Array.prototype.forEachAsync = function (cb, end) {
    var _this = this;
    setTimeout(function () {
        var index = 0;
        var next = function () {
            if (this.burned) return;
            this.burned = true;
            index++;
            if (index >= _this.length) {
                if (end) end();
                return;
            }
            cb(_this[index], next.bind({}));
        }
        if (_this.length == 0) {
            if (end) end();
        }else {
            cb(_this[0], next.bind({}));
        }
    }, 0);
}
var DIFF_CHANGES = {
    'A': 'added',
    'C': 'copied',
    'D': 'deleted',
    'M': 'modified',
    'R': 'renamed',
    'T': 'changed',
    'U': 'unmerged',
    'X': 'unknown',
    'B': 'broken'
};
// var binfo = JSON.parse(fs.readFileSync('./buginfo.json').toString());
var CLIEngine = require("eslint").CLIEngine;
var cnf = {
    "env": {
        "node": 1
    },
    "useEslintrc": false,
    "rules": {
        "max-statements": [2, 15],
        "max-depth": [1, 5],
        "complexity": [2, 5],
        "max-len": [2, 65],
        "max-params": [2, 3],
        "max-nested-callbacks": [2, 2],
        "smells/no-complex-switch-case": 1,
        "smells/no-this-assign": 1,
        //"smells/no-complex-string-concat": 1,
        "smells/no-complex-chaining": 1,
        "no-reassign/no-reassign": 1,
        "no-extra-bind": 1,
        "no-cond-assign": 2
    },
    "plugins": [
        "smells",
        "no-reassign"
    ]
}
function getCommits(cb) {
    exec('git log | cat - > ../c-ommits', {
        cwd: 'uut/'
    }, function(error, stdout, stderr) {
        //console.log(stderr);
        var commits = [];
        stdout = fs.readFileSync('./commits').toString();
        stdout.split(/\n/).forEach(function (line) {
            var cmrex = /^commit ([0-9a-f]{40})$/g;
            var match = cmrex.exec(line);
            if (match == null && line.toLowerCase().indexOf("fix") != -1) {
                commits[commits.length-1].fix = true;
                return;
            }
            if (match == null) return;
            commits.push({id: match[1]});
        });
        cb(commits.reverse());
    });
}

var cli = new CLIEngine(cnf);
var output = {};
var fmap = {};
var contenu = null;
var commit_epoque = JSON.parse(fs.readFileSync('./commit_epoque.json'));

getCommits(function (commits) {
    var N = commits.length;
    var I = 0;
    //console.error(commits);
    exec('git reset --hard && git checkout ' + commits[0].id, {
        cwd: 'uut/'
    }, function (err, stdout, stderr) {

        commits.forEachAsync(function (c, next) {
            // if (c.id != 'a58e3deac27fca9ddbb7e389fdfe7be3aebea639') return next();
            //console.error('!>> git diff-tree --no-commit-id --numstat -M -r ' + c.id + ' -z');
            exec('git diff-tree --no-commit-id --numstat --ignore-submodules -M -r -z ' + c.id, {
                cwd: 'uut/'
            }, function (error, stdout, stderr) {
                //console.error(JSON.stringify(stdout));
                // L'output contiene il nome e percorso dei file del COMMIT, insieme al numero di righe aggiunte e rimosse.
                var files = stdout.split('\u0000').map(function (e) {return e.split(/\t/);});
                files.pop();
                fmap = {};
                for (var i=0;i<files.length;i++) {
                    var e = files[i];
                    //console.error(JSON.stringify(e));
                    if (e[2] == '') {
                        e[2] = files[i+2][0];
                        i+=2;
                    }
                    fmap[e[2]]= [~~e[0], ~~e[1]];
                    //console.error(JSON.stringify(fmap[e[2]][0]));
                }
                //console.error('>>> git diff-tree --no-commit-id --name-status -M -r ' + c.id);
                exec('git diff-tree --no-commit-id --name-status --ignore-submodules -M -r -z ' + c.id, {
                    cwd: 'uut/'
                }, function (error, stdout, stderr) {
                    // Si visualizza l'id del COMMIT, insieme alla sua epoca (rispetto agli altri COMMIT).
                    console.log('COMMIT ' + c.id + '\t' + commit_epoque[c.id]);
                    if (error) throw error;
                    // var files = stdout.split("\n").map(function (e) {return e.split(/\t/);});
                    var _files = stdout.split('\u0000').map(function (e) {return e.split(/\t/);});
                    _files.pop();
                    var files = [];
                    for (var i=0;i<_files.length;i++) {
                        if (_files[i][0][0] == 'R') {
                            files.push([_files[i][0], _files[i+1][0], _files[i+2][0]]);  
                            i+=2;  
                        }else {
                            files.push([_files[i][0], _files[i+1][0]]);
                            i+=1;
                        }
                            
                    }
                    exec('git reset --hard && git checkout ' + c.id, {
                        cwd: 'uut/'
                    }, function (error, stdout, stderr) {
                        var target = [];
                        var changes = [];
                        files.forEach(function (e) {
                            var f = e[1];
                            
                            // console.log("files : ", f, DIFF_CHANGES[e[0][0]]);
                            var push = null;
                            if (DIFF_CHANGES[e[0][0]] == 'deleted') {
                                changes.push({f: f, type: 'deleted'});
                                console.log(">>> uut/" + f + '\t' + fmap[f][0] + '\t' + fmap[f][1] + '\t' + fmap[f][1]);
                            }
                            if (DIFF_CHANGES[e[0][0]] == 'modified') {
                                changes.push({f: f, type: 'modified'});
                                push = f;
                            }
                            if (DIFF_CHANGES[e[0][0]] == 'renamed') {
                                var  fnew = e[2];
                                changes.push({f: f, type: 'renamed', to: fnew});
                                push = fnew;
                            }
                            if (DIFF_CHANGES[e[0][0]] == 'added') {
                                changes.push({f: f, type: 'added'});
                                push = f;
                            }
                            if (push !== null && !fs.existsSync('uut/'+push)) push = null;
                            if (push != null && !fmap[push]) {
                                throw push;
                            }
                            if (push !== null) {
                                target.push("uut/"+push);
                            }
                        });
                        LC(target, function (lines) {
                            target.forEach(function (f) {
                                var abs = f.substr(4);
                                // Si visualizza il nome del file, il numero di righe aggiunte, il numero di righe rimosse e il numero totale di righe.
                                console.log(">>> " + f + '\t' + fmap[abs][0] + '\t' + fmap[abs][1] + '\t' + lines[f]);
                                // Si applica la rilevazione dei "code smells" sui file
                                var report = cli.executeOnFiles([f]);
                                // Visualizzazione dei "code smells"
                                //console.error(JSON.stringify(report));

                                if (report['results'].length != 0) {
                                    //fs.writeFileSync('./test.js', JSON.stringify(f, null, 4));
                                    // Si memorizza il file modificato
                                    //g = fs.readFileSync(f).toString().split('\n');
                                    // Si memorizzano le informazioni delle modifiche del file
                                    var report2 = report['results'][0]['messages'];
                                    var source = report['results'][0]['source'];
                                    // Per ogni modifica
                                    for(i=0 ; i<report2.length ; i++) {
                                        // Metricas del "code smell" ("peso")
                                        metric = 0;
                                        endLine = 0;
                                        // Se appare un "code smell"
                                        if(report2[i]["ruleId"] != null) {
                                            // Si memorizza il nome del "code smell"
                                            t = report2[i]["ruleId"].split('/')[report2[i]["ruleId"].split('/').length-1];

                                            // Se il "code smell" è max-statements
                                            if(t=='max-statements') {
                                                // Si memorizza il peso del "code smell"
                                                metric = report2[i]["message"].split(/\((\d+)\)/)[1];
                                                endLine = report2[i]["endLine"];
                                                //console.error('Peso del "smell" max-statements : '+metric);
                                            }

                                            // Se il "code smell" è max-depth
                                            if(t=='max-depth') {
                                                // Si memorizza il peso del "code smell"
                                                metric = report2[i]["message"].split(/\((\d+)\)/)[1];
                                                endLine = report2[i]["endLine"];
                                                //console.error('Peso del "smell" max-depth : '+metric);
                                            }

                                            // Se il "code smell" è complexity
                                            if(t=='complexity') {
                                                // Si memorizza il peso del "code smell"
                                                metric = report2[i]["message"].split(/(\d+)/)[1];
                                                endLine = report2[i]["endLine"];
                                                //console.error('Peso del "smell" complexity : '+metric);
                                            }

                                            // Se il "code smell" è max-len
                                            if(report2[i]["ruleId"]=='max-len') {
                                                //source = report2[i]["source"]
                                                //console.error("Numero di caratteri sulla riga : "+source.length)

                                                metric = report2[i]["message"].split(/\((\d+)\)/)[1];
                                                endLine = report2[i]["line"];
                                                //console.error('Peso del "smell" max-len : '+metric);
                                            }

                                            // Se il "code smell" è max-params
                                            if(report2[i]["ruleId"]=='max-params') {
                                                metric = report2[i]["message"].split(/\((\d+)\)/)[1];
                                                endLine = report2[i]["endLine"];
                                                //console.error('Peso del "smell" max-params : '+metric);
                                            }

                                            // Se il "code smell" è max-nested-callbacks
                                            if(report2[i]["ruleId"]=='max-nested-callbacks') {
                                                metric = report2[i]["message"].split(/\((\d+)\)/)[1];
                                                endLine = report2[i]["endLine"];
                                                //console.error('Peso del "smell" max-nested-callbacks : '+metric);
                                            }

                                            // Se il "code smell" è complex-switch-case
                                            if(t=='no-complex-switch-case') {
                                                t = 'complex-switch-case';
                                                // Si memorizza il peso del "code smell"
                                                metric = report2[i]["message"].split(/\((\d+)\)/)[1];
                                                endLine = report2[i]["endLine"];
                                                //console.error('Peso del "smell" complex-switch-case : '+metric);
                                            }

                                            // Se il "code smell" è this-assign
                                            if(t=='no-this-assign') {
                                                t = 'this-assign';
                                                metric = 1;
                                                endLine = report2[i]["line"];
                                                //console.error('Peso del "smell" this-assign : '+metric)
                                            }

                                            // Se il "code smell" è complex-chaining
                                            if(t=='no-complex-chaining') {
                                                t = 'complex-chaining';
                                                // Si memorizza il peso del "code smell"
                                                metric = report2[i]["message"].split(/\((\d+)\)/)[1];
                                                endLine = report2[i]["endLine"];
                                                //console.error('Peso del "smell" complex-chaining : '+metric);
                                            }

                                            // Se il "code smell" è no-reassign
                                            if(t=='no-reassign') {
                                                metric = 1;
                                                endLine = report2[i]["line"];
                                                //console.error('Peso del "smell" no-reassign : '+metric);
                                            }

                                            // Se il "code smell" è no-extra-bind
                                            if(t=='no-extra-bind') {
                                                metric = 1;
                                                endLine = report2[i]["line"];
                                                //console.error('Peso del "smell" no-extra-bind : '+metric);
                                            }

                                            // Se il "code smell" è cond-assign
                                            if(t=='no-cond-assign') {
                                                t = 'cond-assign';
                                                metric = 1;
                                                endLine = report2[i]["line"];
                                                //console.error('Peso del "smell" cond-assign : '+metric)
                                            }

                                            //if(count[t]==null){
                                            //    count[t] = 0;
                                            //}
                                            //count[t] += 1;
                                            //count[t]+=report2[i]["severity"];
                                            //console.log('%% '+report2[i]["ruleId"].split('/')[report2[i]["ruleId"].split('/').length-1]);
                                            var split_source = source.split(/\r|\n/);
                                            contenu = split_source[report2[i]["line"]-1].substr(report2[i]["column"]-1);
                                            if (endLine - report2[i]["line"] > 0) {
                                                for (var line_number = report2[i]["line"]; line_number < endLine - 1; line_number++) {
                                                    contenu += split_source[line_number]
                                                }
                                            }
                                            contenu = contenu.trim();
                                            if(contenu.length > 100) {
                                                contenu = contenu.substr(0,100)
                                            }
                                            // Si visualizza il tipo di "code smell", insieme alla sua linea, colonna nel file, peso e linea di fine
                                            console.log('%% ' + t + '\t'+report2[i]["line"] + '\t'+report2[i]["column"]+ '\t'+metric+'\t'+contenu+'\t'+endLine);
                                        }
                                        //else {
                                        //    console.log('%% '+report2[i]["ruleId"]+' '+'1');
                                        //}
                                    }
                                    //console.error(JSON.stringify(count));
                                    //for (var element in count){
                                    //    console.log('%% '+element+' '+count[element]);
                                    //}
                                }
                            })
                            console.error(N + " -- " + (++I));
                            next();
                        })
                    });
                });
            });
        }, function () {
            // fs.writeFileSync('./data.json', JSON.stringify(output));
        });
    });
});
