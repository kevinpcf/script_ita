var fs = require('fs');
var exec = require('child_process').exec;
var spawn = require('child_process').spawn;
var stream = require('stream');
var readline = require('readline')

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

var output = [];
var medians = {};

var d = fs.readFileSync('./report.txt').toString().split('\n');
var issues = JSON.parse(fs.readFileSync('./issues.json'));

var nombre_commit = 0;
d.forEach(function (line) {
	//console.error(line);
	if(line.startsWith("COMMIT")) {
		nombre_commit+=1;
	}
});

console.error("Numero di COMMIT : "+nombre_commit);

var issuesMap = {};
issues.forEach(function (i) {
	i.created_at = new Date(i.created_at);
	i.closed_at = new Date(i.closed_at);
	issuesMap[~~i.number] = i;
});
var fileHistory = {};
//var names_of_file = []
var commits = {};
//d.pop();
//d.shift();
var current = null;
var filemap = {};
var skipped = 0;
var currentfile = null;
var I = 0;

d.forEach(function (line) {
	if(line.startsWith('Nombre_de_commits')) {
		nombre_commit = line.split('\t')[1];
		console.error('Numero di commit : '+nombre_commit);
	}
	if (line.startsWith("COMMIT")) {
		console.error((I++));
		filemap = {};
		var cm = line.substr("COMMIT ".length).split('\t')[0];
		var r = JSON.parse(fs.readFileSync('commits-clean/'+cm+'.json').toString());
		current = {
			commit: r.commit,
			date: new Date(r.date),
			fix: r.fix,
			buggy: [],
			changes: []
		}
		commits[r.commit] = current;
		r.changes.forEach(function (ch) {
			var filename = ch.f;
			fileHistory[filename] = fileHistory[filename] || [];
			if (ch.type == "renamed") {
				fileHistory[ch.to] = fileHistory[filename] || [];
				delete fileHistory[filename];
				filename = ch.to;
			}
			fileHistory[filename].push(r.commit);
			var newitem = {
				f: filename,
				type: ch.type,
				smells: {}
			}
			if (ch.type == 'renamed') {
				newitem.old = ch.f;
			}
			filemap[filename] = newitem;
			current.changes.push(newitem);
		});

		if(I == nombre_commit) {
			//console.error('Storico di tutti i file : '+JSON.stringify(fileHistory));
			fs.writeFileSync('./historique_fichiers.json', JSON.stringify(fileHistory));
		}

		if (current.fix.length > 0) {
			current.fix.forEach(function (bug) {
				
				var issue = issuesMap[~~bug];
				if (!issue) return;
				current.changes.forEach(function (ch) {
					var file = ch.f;
					candidat = null;
					for (var i=1;i<fileHistory[file].length;i++) {
						//console.log("Data del commit : "+commits[fileHistory[file][i]].date);
						if (commits[fileHistory[file][i]].date >= issue.created_at) {

							//console.log("Numero del bug : "+~~bug);
							commits[fileHistory[file][i-1]].buggy.push(~~bug+" @@ "+file);

							// Conserviamo nella memoria l'epoca del candidato al bug nella storia delle modifiche del file
							candidat = i-1;

							//console.log('Bug : '+bug);
							commits[fileHistory[file][i-1]].introduce = true;
							break;
						}
					}

					if(fileHistory[file].length > 1 && candidat != null) {
						commits_a_tracer = fileHistory[file].slice(candidat);
						candidat_bug = fileHistory[file][candidat];
						commit_fix = fileHistory[file][fileHistory[file].length-1];
						console.log('File '+file);
						console.log('Numero_bug '+~~bug);
						console.log('Candidato_bug '+candidat_bug);
						console.log('Commit_fix '+commit_fix);
						console.log('Commits_da_tracciare '+commits_a_tracer);
						console.log('');

					}
				})
			})
		}
		output.push(current);
	}
	if (line.startsWith(">>>")) {
		var file = line.substr(">>> uut/".length).split('\t');

		if (!filemap[file[0]]) {
			currentfile = "### SKIPPATO";
			return;
		};
		filemap[file[0]].churn = [~~file[1], ~~file[2], ~~file[3]];
		currentfile = file[0];
	}
	if (line.startsWith('%%')) {
		if (currentfile=="### SKIPPATO") return;
		var smell = line.substr('%% '.length).split("\t");
		filemap[currentfile].smells[smell[0]] = filemap[currentfile].smells[smell[0]] || [];

		//filemap[currentfile].smells[smell[0]].push(~~smell[3]);
		filemap[currentfile].smells[smell[0]].push([~~smell[3],[~~smell[1],~~smell[5]],smell[4]]);
		//console.error('Codice del smell : '+smell[4]);

		medians[smell[0]] = medians[smell[0]] || [];
		medians[smell[0]].push(~~smell[3]);
		//console.log(medians);
	};
});

fs.writeFileSync('./data.json',JSON.stringify(output));

var an = {};
var smells = Object.keys(medians);
smells.forEach(function (sm) {
	if (sm == 'max-len') {
		var data = medians[sm].filter(function (o) {
			return o != 0;
		}).sort(function (a, b) {
			return a<b?-1:
				   a>b?+1:
				   0;
		});
		var mx = data[data.length-1];
		data = data[Math.round(data.length/2)];
		an[sm] = {
			med: data,
			max: mx
		}
	}else if (sm == 'complex-chaining'){
		var data = medians[sm].filter(function (o) {
			return o != 0;
		}).sort(function (a, b) {
			return a<b?-1:
				   a>b?+1:
				   0;
		});
		var mx = data[data.length-1];
		data = data[Math.round(data.length/2)];
		an[sm] = {
			med: data,
			max: mx
		}
	}else if (sm == 'max-params') {
		var data = medians[sm].sort(function (a, b) {
			return a<b?-1:
				   a>b?+1:
				   0;
		});
		var mx = data[data.length-1];
		data = data[Math.round(data.length/2)];
		an[sm] = {
			med: data,
			max: mx
		}
	}else if (sm == 'max-nested-callbacks') {
		var data = medians[sm].filter(function (o) {
			return o != 0;
		}).sort(function (a, b) {
			return a<b?-1:
				   a>b?+1:
				   0;
		});
		var mx = data[data.length-1];
		data = data[Math.round(data.length/2)];
		an[sm] = {
			med: data,
			max: mx
		}
	}else if (sm == 'max-statements') {
		var data = medians[sm].filter(function (o) {
			return o != 0;
		}).sort(function (a, b) {
			return a<b?-1:
				   a>b?+1:
				   0;
		});
		var mx = data[data.length-1];
		data = data[Math.round(data.length/2)];
		an[sm] = {
			med: data,
			max: mx
		}
	}else if (sm == 'complexity') {
		var data = medians[sm].filter(function (o) {
			return o != 0;
		}).sort(function (a, b) {
			return a<b?-1:
				   a>b?+1:
				   0;
		});
		var mx = data[data.length-1];
		data = data[Math.round(data.length/2)];
		an[sm] = {
			med: data,
			max: mx
		}
	}else if (sm == 'max-depth') {
		var data = medians[sm].filter(function (o) {
			return o != 0;
		}).sort(function (a, b) {
			return a<b?-1:
				   a>b?+1:
				   0;
		});
		var mx = data[data.length-1];
		data = data[Math.round(data.length/2)];
		an[sm] = {
			med: data,
			max: mx
		}
	}else if (sm == 'complex-switch-case') {
		var data = medians[sm].filter(function (o) {
			return o != 0;
		}).sort(function (a, b) {
			return a<b?-1:
				   a>b?+1:
				   0;
		});
		var mx = data[data.length-1];
		data = data[Math.round(data.length/2)];
		an[sm] = {
			med: data,
			max: mx
		}
	}else if (sm == 'this-assign' || sm == 'no-reassign' || sm == 'extra-bind' || sm == 'cond-assign') {
		
		an[sm] = {
			med: 0,
			max: 1
		}
	}

});
Object.keys(an).sort().forEach(function (i) {
	console.error([i,an[i].med,an[i].max].join("\t"));
});
//fs.writeFileSync('./med.json', JSON.stringify(medians));
