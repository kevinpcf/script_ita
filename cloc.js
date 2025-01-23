var exec = require('child_process').exec;
function f(names, cb) {
	var total = names.length;
	var result = {};
	if (total == 0) cb({});
	names.forEach(n => {
		exec('cat ' + n + ' | wc -l', {
			cwd: './'
		}, function (err, stdout, stderr) {
			result[n] = parseInt(stdout);
			total--;
			if (total == 0) {
				cb(result);
			}
		})
	})
}
module.exports = f;
// // f(['uut/lib/middleware.js', 'uut/lib/response.js'], function (d) {
// // 	console.log(d);
// })