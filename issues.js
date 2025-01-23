var request = require('request');
var github = require("github-request");

var getIssues = function (repo, cb) {
	github.requestAll({
		path: '/repos/' + repo + '/issues?state=all'
	}, function(error, issues) {
		if (error) throw error;
		console.log(JSON.stringify(issues.map( issue => {
			// console.log(issue);
				return ({
					url: issue.url,
					title: issue.title,
					number: issue.number,
					state: issue.state,
					created_at: issue.created_at,
					updated_at: issue.updated_at,
					closed_at: issue.closed_at,
					is_pull_request: issue.pull_request !== undefined
				});
			}), null, 4));
		// console.log(issues.length)
	});
	
}

getIssues(process.argv[2]);
