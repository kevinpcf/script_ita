var fs = require('fs');
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

var CLIEngine = require("eslint").CLIEngine;
var cnf = {
    "env": {
        "node": 1
    },
    "useEslintrc": false,
    "rules": {
        //"max-statements": [2, 15],
        //"max-depth": [1, 5],
        //"complexity": [2, 5],
        //"max-len": [2, 65],
        //"max-params": [2, 3],
        //"max-nested-callbacks": [2, 2],
        //"smells/no-complex-switch-case": 1,
        //"smells/no-this-assign": 1,
        //"smells/no-complex-string-concat": 1,
        //"smells/no-complex-chaining": 1,
        //"no-reassign/no-reassign": 1,
        //"no-extra-bind": 1,
        "no-cond-assign": 2
    },
    "plugins": [
        "smells",
        "no-reassign"
    ]
}
function getCommits(cb) {
    exec('git log | cat - > ../commits', {
        cwd: 'uut/'
    }, function(error, stdout, stderr) {
        console.log(stderr);
        var commits = [];
        stdout = fs.readFileSync('./commits').toString();
        stdout.split(/\n/).forEach(function (line) {
            var cmrex = /^commit ([0-9a-f]{40})$/g;
            var match = cmrex.exec(line);
            // Gli ID dei bug sono preceduti da # o da gh-
            var bugs = line.match(/#\d+/g, line);
            if (bugs != null) {bugs = bugs.map(b => b.substr(1));}
            var bugs2 = line.toLowerCase().match(/gh-\d+/g, line.toLowerCase());
            if (bugs2 != null) {bugs2 = bugs2.map(b => b.substr(3));}
            var bugs3 = null;
            if (bugs != null) {
                if (bugs2 != null) {
                    bugs3 = bugs.concat(bugs2);
                }
                else {
                    bugs3 = bugs;
                }
            }
            else if (bugs2 != null) {
                bugs3 = bugs2;
            }
            // Rimuovi gli ID dei bug duplicati
            var bugs4 = [];
            if (bugs3 != null) {
                for (var i = 0; i < bugs3.length; i++) {
                    if (bugs4.indexOf(bugs3[i]) < 0) {
                        bugs4.push(bugs3[i]);
                    }
                }
            }
            if (match == null && bugs3 != null) {
                commits[commits.length-1].fix = bugs4;
                //console.error(bugs4);
                return;
            }
            if (match == null && line.startsWith('Date:   ')) {
                commits[commits.length-1].date = line.substr('Date:   '.length);
                return;
            }
            if (match == null) return;
            commits.push({id: match[1], date: -1});
        });
        cb(commits.reverse());
    });
}

var cli = new CLIEngine(cnf);
var output = {};
commit_date = [];

getCommits(function (commits) {
    var N = commits.length;
    var I = 0;
    exec('git reset --hard && git checkout ' + commits[0].id, {
        cwd: 'uut/'
    }, function (err, stdout, stderr) {

        commits.forEachAsync(function (c, next) {

            exec('git diff-tree --no-commit-id --name-status --ignore-submodules -M -r ' + c.id, {
                cwd: 'uut/'
            }, function (error, stdout, stderr) {
                //console.log(c.id);
                var files = stdout.split("\n").map(function (e) {return e.split(/\t/);});
                files.pop();
                exec('git reset --hard && git checkout ' + c.id, {
                    cwd: 'uut/'
                }, function (error, stdout, stderr) {
                    var target = [];
                    var changes = [];
                    files.forEach(function (e) {
                        var f = e[1];
                        //console.log("files : ", f, DIFF_CHANGES[e[0][0]]);
                        var push = null;
                        if (DIFF_CHANGES[e[0][0]] == 'deleted') {
                            changes.push({f: f, type: 'deleted'});
                        }
                        if (DIFF_CHANGES[e[0][0]] == 'modified') {
                            changes.push({f: f, type: 'modified'});
                            push = f;
                        }
                        if (DIFF_CHANGES[e[0][0]] == 'renamed') {
                            var  fnew = e.slice(2);
                            changes.push({f: f, type: 'renamed', to: fnew});
                            push = fnew;
                        }
                        if (DIFF_CHANGES[e[0][0]] == 'added') {
                            changes.push({f: f, type: 'added'});
                            push = f;
                        }
                        if (push !== null && !fs.existsSync('uut/'+push)) push = null;
                        if (push !== null) {
                            target.push("uut/"+push);
                        }
                    });
                    
                    var report = cli.executeOnFiles(target);
                    output[c.id] = report;
                    output[c.id].fix = c.fix?c.fix:[];
                    output[c.id].changes = changes;
                    output[c.id].date = new Date(c.date);
                    commit_date.push({id: c.id, date: output[c.id].date});
                    //console.error(commit_date.length);
                    commit_date.sort(function(a,b){
                        return a.date - b.date;
                    },
                    fs.writeFileSync('./commit_date.json', JSON.stringify(commit_date, null, 4))),
                    console.error(N + " -- " + (++I));
                    fs.writeFileSync('./commits-data/'+c.id+'.json', JSON.stringify(output[c.id], null, 4));
                    next();
                });
                //console.error(commit_date.length),
            });
        }, function () {
            //fs.writeFileSync('./data.json', JSON.stringify(output));
        });
    });
});
